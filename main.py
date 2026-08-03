#!/usr/bin/env python3
"""洛谷题面转 NOIP 格式 PDF 工具（HTML / LaTeX 双后端）。

用法：
    python main.py                              # 使用 contest.json 配置，HTML 后端
    python main.py --latex                      # 用 LaTeX 生成（xelatex + minted）
    python main.py --problems P1000 P1001       # 命令行直接指定题号

输出：
    output/<比赛名>/
        第1题-<题号>-<题名>.pdf   每道题单独一个 PDF
        <比赛名>-题面合集.pdf      封面 + 全部题目合并的一个 PDF
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright

from luogu import fetch_problem
from model import Contest, Problem
from template import (build_cover_html, build_problem_html,
                      build_problem_section, build_combined_html)
from utils import safe_filename
from latex import (build_statement_tex, build_problem_doc,
                      build_combined_doc, build_build_script, compile_latex)

DEFAULT_CONFIG = ROOT / "contest.json"
WORK_DIR = ROOT / ".work"
DEFAULT_OUTPUT = ROOT / "output"
VENV_BIN = ROOT / ".venv" / "bin"

FOOTER_HTML = """
<div style="width:100%; text-align:center; font-size:10px; color:#000;
            font-family:'Noto Serif CJK SC','Noto Sans CJK SC',serif;">
  第 <span class="pageNumber"></span> 页　共 <span class="totalPages" style="color:#2E74B5;"></span> 页
</div>
"""

EMPTY_HEADER_HTML = "<div></div>"


def parse_args():
    ap = argparse.ArgumentParser(description="洛谷题面转 NOIP 格式 PDF")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                    help="比赛配置文件（JSON），默认 contest.json")
    ap.add_argument("--contest", help="比赛名称，覆盖配置")
    ap.add_argument("--date", help="比赛日期，如 2026-08-03")
    ap.add_argument("--time", help="比赛时间，如 9:00-13:00")
    ap.add_argument("--duration", help="比赛时长，如 4 小时")
    ap.add_argument("--problems", help="题号列表，逗号分隔，如 P17169,P17170")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT,
                    help="输出目录，默认 output/")
    ap.add_argument("--latex", action="store_true",
                    help="用 LaTeX 生成（需要 xelatex + minted + pygments）")
    ap.add_argument("--no-merge", action="store_true", help="不生成合集 PDF")
    ap.add_argument("--keep-html", action="store_true", help="保留中间 HTML/TeX")
    return ap.parse_args()


def load_config(path):
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
    else:
        cfg = {}
    problems = cfg.get("problems", [])
    if isinstance(problems, list):
        cfg["problems"] = [p if isinstance(p, dict) else {"pid": p} for p in problems]
    return cfg


def merge_config(args, cfg):
    contest = Contest(
        name=args.contest or cfg.get("contest", "模拟赛"),
        date=args.date or cfg.get("date", ""),
        time=args.time or cfg.get("time", ""),
        duration=args.duration or cfg.get("duration", ""),
        notes=cfg.get("notes") or [],
    )
    problems = cfg["problems"]
    if args.problems:
        problems = [{"pid": p.strip()} for p in args.problems.split(",") if p.strip()]
    if not problems:
        sys.exit("错误：没有指定题目（请在 contest.json 中填写 problems，或用 --problems 指定）")
    return contest, problems


async def fetch_all(browser, problems, work_dir):
    """抓取所有题目，返回数据列表。"""
    datas = []
    for i, prob in enumerate(problems, 1):
        pid = prob["pid"]
        print(f"\n[{i}/{len(problems)}] 抓取 {pid} ...", flush=True)
        try:
            data = await fetch_problem(browser, pid, work_dir)
            data.index = i
            data.english = prob.get("english", "")
            data.type = prob.get("type", "传统型")
            datas.append(data)
            print(f"  完成: {data.title} | {data.time_limit} / "
                  f"{data.memory_limit} | {len(data.samples)} 组样例")
        except Exception as e:
            print(f"  失败: {e}")
    if not datas:
        sys.exit("\n错误：所有题目都抓取失败")
    return datas


def pdf_name(data, out_dir):
    """输出文件名：第X题-题名.pdf（不暴露洛谷题号）。"""
    en = data.english_name
    title = safe_filename(data.title)
    if en:
        return out_dir / f"第{data['index']}题-{safe_filename(en)}-{title}.pdf"
    return out_dir / f"第{data['index']}题-{title}.pdf"


async def run_html(browser, datas, contest, out_dir, args):
    """HTML 后端：Chromium 打印 PDF。"""
    pdf_paths = []
    ctx = await browser.new_context(locale="zh-CN")
    try:
        for data in datas:
            pid = data.pid
            html = build_problem_html(data, contest, data.index, len(datas))
            html_path = WORK_DIR / f"problem_{pid}.html"
            html_path.write_text(html, encoding="utf-8")
            if args.keep_html:
                print(f"\nHTML 已保存: {html_path}")

            print(f"\n生成 PDF: {pid} ...", flush=True)
            page = await ctx.new_page()
            try:
                await page.goto(html_path.as_uri(), wait_until="networkidle", timeout=60000)
                await page.evaluate("document.fonts.ready.then(() => true)")
                pdf_path = pdf_name(data, out_dir)
                await page.pdf(
                    path=str(pdf_path), format="A4", print_background=True,
                    margin={"top": "25mm", "bottom": "20mm",
                            "left": "27mm", "right": "27mm"},
                    footer_template=FOOTER_HTML,
                    header_template=EMPTY_HEADER_HTML,
                    display_header_footer=True,
                )
                pdf_paths.append(pdf_path)
                print(f"  完成: {pdf_path.name}")
            except Exception as e:
                print(f"  失败: {e}")
            finally:
                await page.close()

        if not args.no_merge:
            print("\n生成合集 PDF ...", flush=True)
            try:
                cover_body = build_cover_html(contest, datas)
                sections = "\n".join(build_problem_section(d, contest) for d in datas)
                html = build_combined_html(contest, datas, cover_body, sections)
                html_path = WORK_DIR / "combined.html"
                html_path.write_text(html, encoding="utf-8")
                page = await ctx.new_page()
                try:
                    await page.goto(html_path.as_uri(), wait_until="networkidle", timeout=60000)
                    await page.evaluate("document.fonts.ready.then(() => true)")
                    merge_path = out_dir / f"{safe_filename(contest.name)}-题面合集.pdf"
                    await page.pdf(
                        path=str(merge_path), format="A4", print_background=True,
                        margin={"top": "25mm", "bottom": "20mm",
                                "left": "27mm", "right": "27mm"},
                        footer_template=FOOTER_HTML,
                        header_template=EMPTY_HEADER_HTML,
                        display_header_footer=True,
                    )
                    print(f"  完成: {merge_path.name}")
                finally:
                    await page.close()
            except Exception as e:
                print(f"  合集失败: {e}")
    finally:
        await ctx.close()
    return pdf_paths


def run_latex(datas, contest, out_dir, args):
    """LaTeX 后端：输出可独立编译的 tex 源码（题面 body 分离 + 编译脚本），
    编译生成每题 + 合集 PDF。"""
    import shutil
    tex_out = out_dir / "tex"
    tex_out.mkdir(parents=True, exist_ok=True)
    body_dir = tex_out / "题面"
    body_dir.mkdir(exist_ok=True)
    images = tex_out / "img"
    images.mkdir(exist_ok=True)
    shutil.copy(ROOT / "assets" / "latex" / "statement.cls", tex_out / "statement.cls")

    # 1) 题面 body（只含 \section 内容，单题与合集共用 \input）
    body_rels = []
    for data in datas:
        bname = f"第{data.index}题-{safe_filename(data.title)}.tex"
        data.statement_tex = build_statement_tex(
            data, contest, data.index, len(datas), images)
        (body_dir / bname).write_text(data.statement_tex, encoding="utf-8")
        body_rels.append(f"题面/{bname}")

    # 2) 单题文档 + 合集文档（引用 body）
    tex_names = []
    for data in datas:
        tname = f"第{data.index}题-{safe_filename(data.title)}.tex"
        (tex_out / tname).write_text(
            build_problem_doc(contest, data.index, len(datas),
                              f"题面/{tname}"),
            encoding="utf-8")
        tex_names.append(tname)
    comb_name = f"{safe_filename(contest.name)}-题面合集.tex"
    if not args.no_merge:
        (tex_out / comb_name).write_text(
            build_combined_doc(contest, datas, images, body_rels),
            encoding="utf-8")
        tex_names.append(comb_name)

    # 3) 一键编译脚本（修改题面后重新生成全部 PDF）
    (tex_out / "build.sh").write_text(build_build_script(tex_out), encoding="utf-8")
    (tex_out / "build.sh").chmod(0o755)

    # 4) 编译全部（两遍处理 TotPages 引用），PDF 复制到 out_dir
    pdf_paths = []
    for tname in tex_names:
        tex_path = tex_out / tname
        print(f"\n编译 LaTeX: {tname} ...", flush=True)
        ok, pdf = compile_latex(tex_path, VENV_BIN)
        if ok:
            dest = out_dir / pdf.name
            shutil.copy(pdf, dest)
            pdf_paths.append(dest)
            print(f"  完成: {dest.name}")
        else:
            print(f"  失败: {pdf}")
    return pdf_paths


async def run(args):
    cfg = load_config(args.config)
    contest, problems = merge_config(args, cfg)

    WORK_DIR.mkdir(exist_ok=True)
    out_dir = args.output_dir / safe_filename(contest.name)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"比赛: {contest.name} | {contest.date} | {contest.time}（{contest.duration}）")
    print(f"题目: {', '.join(p['pid'] for p in problems)}")
    print(f"输出: {out_dir}")
    print(f"后端: {'LaTeX' if args.latex else 'HTML'}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            datas = await fetch_all(browser, problems, WORK_DIR)
            if args.latex:
                for d in datas:
                    if not d.content:
                        sys.exit(f"\n错误: {d.pid} 缺少 Markdown 数据（LaTeX 后端需要），抓取可能失败")
                pdf_paths = run_latex(datas, contest, out_dir, args)
            else:
                pdf_paths = await run_html(browser, datas, contest, out_dir, args)
        finally:
            await browser.close()

    if not pdf_paths:
        sys.exit("\n错误：所有 PDF 生成失败")
    print("\n全部完成。")


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
