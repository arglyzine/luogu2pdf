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
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright

from luogu import fetch_problem
from model import Contest
from template import (build_cover_html, build_problem_html,
                      build_problem_section, build_combined_html)
from utils import safe_filename, dashfix
from compile import compile_latex
from latex_doc import (build_statement_tex, build_problem_doc,
                       build_combined_doc, build_build_script)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("luogu2pdf")

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
    """读取并校验 contest.json；格式错误给出明确提示。"""
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
    else:
        cfg = {}
    problems = cfg.get("problems", [])
    if not isinstance(problems, list):
        sys.exit("错误：contest.json 的 problems 必须是列表")
    cfg["problems"] = [p if isinstance(p, dict) else {"pid": p} for p in problems]
    for p in cfg["problems"]:
        if not re.match(r"^P\d+$", str(p.get("pid", ""))):
            sys.exit(f"错误：题目号格式不正确：{p.get('pid')!r}（应为 P 开头，如 P17169）")
    date = str(cfg.get("date", ""))
    if date and not re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", date):
        log.warning("日期格式建议 YYYY-MM-DD：%s", date)
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
        for p in problems:
            if not re.match(r"^P\d+$", p["pid"]):
                sys.exit(f"错误：题目号格式不正确：{p['pid']!r}")
    if not problems:
        sys.exit("错误：没有指定题目（请在 contest.json 中填写 problems，或用 --problems 指定）")
    return contest, problems


async def fetch_all(browser, problems, work_dir):
    """抓取所有题目，返回数据列表。"""
    datas = []
    for i, prob in enumerate(problems, 1):
        pid = prob["pid"]
        log.info("[%d/%d] 抓取 %s ...", i, len(problems), pid)
        try:
            data = await fetch_problem(browser, pid, work_dir)
            data.index = i
            data.english = prob.get("english", "")
            data.type = prob.get("type", "传统型")
            datas.append(data)
            log.info("  完成: %s | %s / %s | %d 组样例",
              data.title, data.time_limit, data.memory_limit, len(data.samples))
        except Exception as e:
            log.error("  失败: %s", e)
    if not datas:
        sys.exit("\n错误：所有题目都抓取失败")
    return datas


def pdf_name(data, out_dir):
    """输出文件名：第X题-题名.pdf（不暴露洛谷题号）。"""
    en = data.english_name
    title = safe_filename(data.title)
    if en:
        return out_dir / f"第{data.index}题-{safe_filename(en)}-{title}.pdf"
    return out_dir / f"第{data.index}题-{title}.pdf"


def header_html(left, right):
    """Chromium headerTemplate：渲染在页边距区域，每页重复且不与正文重叠。

    内层 div 对齐版心（左右 27mm padding），横线不延伸到页面两端。
    """
    return f"""<div style="width:100%; padding:0 76.5pt; box-sizing:border-box;">
  <div style="display:flex; justify-content:space-between; border-bottom:1px solid #000;
              padding-bottom:2mm; font-size:10px; font-family:'Noto Serif CJK SC',serif; color:#000;">
    <span>{left}</span><span style="font-weight:bold;">{right}</span>
  </div>
</div>"""


def split_segments_by_problems(pdf_path, datas):
    """按题目名 h1 标题（17pt 大字号，正文/节标题不干扰）定位每题起始页。
    返回 [(起页, 止页, 题名)]（0-based）。"""
    import fitz
    doc = fitz.open(pdf_path)
    total = len(doc)
    # h1 标题实测 17.22pt，节标题 14.35pt：取 16.5 只匹配题名标题，
    # 给字体渲染留缓冲又不误匹配节标题/公式
    page_big_text = []
    for i in range(total):
        big = "".join(s["text"] for b in doc[i].get_text("dict")["blocks"]
                      for l in b.get("lines", []) for s in l["spans"]
                      if s["size"] >= 16.5)
        page_big_text.append(big)
    starts = []
    for d in datas:
        found = None
        for i in range(1, total):
            if d.title in page_big_text[i]:
                found = i
                break
        starts.append(found)
    segs = []
    for k, d in enumerate(datas):
        s = starts[k]
        if s is None:
            continue
        e = starts[k + 1] - 1 if k + 1 < len(starts) and starts[k + 1] is not None else total - 1
        en = d.english_name
        segs.append((s, e, f"{d.title}（{en}）" if en else d.title))
    return segs


async def run_html(browser, datas, contest, out_dir, args):
    """HTML 后端：Chromium 打印 PDF（页眉用 headerTemplate，每页重复）。"""
    pdf_paths = []
    ctx = await browser.new_context(locale="zh-CN")
    try:
        for data in datas:
            pid = data.pid
            html = build_problem_html(data, contest, data.index, len(datas))
            html_path = WORK_DIR / f"problem_{pid}.html"
            html_path.write_text(html, encoding="utf-8")
            if args.keep_html:
                log.info("HTML 已保存: %s", html_path)

            log.info("生成 PDF: %s ...", pid)
            page = await ctx.new_page()
            try:
                await page.goto(html_path.as_uri(), wait_until="networkidle", timeout=60000)
                await page.evaluate("document.fonts.ready.then(() => true)")
                pdf_path = pdf_name(data, out_dir)
                en = data.english_name
                right = f"{data.title}（{en}）" if en else data.title
                await page.pdf(
                    path=str(pdf_path), format="A4", print_background=True,
                    margin={"top": "25mm", "bottom": "20mm",
                            "left": "27mm", "right": "27mm"},
                    footer_template=FOOTER_HTML,
                    header_template=header_html(dashfix(contest.name), right),
                    display_header_footer=True,
                )
                pdf_paths.append(pdf_path)
                log.info("  完成: %s", pdf_path.name)
            except Exception as e:
                log.error("  失败: %s", e)
            finally:
                await page.close()

        if not args.no_merge:
            log.info("生成合集 PDF ...")
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
                        header_template="<div></div>", footer_template="<div></div>",
                        display_header_footer=True,
                    )
                    # 按题分段叠加页眉（右侧题名）与全局页码（第 1 页封面无页眉页码）
                    from overlay import apply_overlay
                    segs = split_segments_by_problems(merge_path, datas)
                    total = __import__("pypdf").PdfReader(str(merge_path)).get_num_pages()
                    apply_overlay(merge_path, merge_path, contest.name, segs, total)
                    log.info("  完成: %s", merge_path.name)
                finally:
                    await page.close()
            except Exception as e:
                log.error("  合集失败: %s", e)
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

    # 4) 并行编译全部（文件间独立，draftmode 第一遍已处理引用），PDF 复制到 out_dir
    from concurrent.futures import ThreadPoolExecutor
    pdf_paths = []

    def compile_one(tname):
        tex_path = tex_out / tname
        log.info("编译 LaTeX: %s ...", tname)
        return tname, compile_latex(tex_path, VENV_BIN)

    with ThreadPoolExecutor(max_workers=len(tex_names)) as ex:
        results = list(ex.map(compile_one, tex_names))
    for tname, (ok, pdf) in results:
        if ok:
            dest = out_dir / pdf.name
            shutil.copy(pdf, dest)
            pdf_paths.append(dest)
            log.info("  完成: %s", dest.name)
        else:
            log.error("  失败(%s): %s", tname, pdf)
    return pdf_paths


def export_samples(datas, out_dir):
    """把样例输入输出导出为 data/<可执行文件名>/{n}.in / {n}.out。

    洛谷样例文本无结尾换行；数据文件按惯例以换行结尾（评测/比对按行处理），
    统一补齐。"""
    data_dir = out_dir / "data"
    count = 0

    def write(path, text):
        if not text.endswith("\n"):
            text += "\n"
        path.write_text(text, encoding="utf-8")

    for d in datas:
        samples = d.md_samples
        if not samples:
            continue
        pdir = data_dir / d.exec_name
        pdir.mkdir(parents=True, exist_ok=True)
        for n, pair in enumerate(samples, 1):
            inp, outp = pair[0], pair[1] if len(pair) > 1 else ""
            write(pdir / f"{n}.in", inp)
            if outp:
                write(pdir / f"{n}.out", outp)
            count += 1
    if count:
        log.info("样例数据已导出: %s（%d 组）", data_dir, count)
    return count


def create_distribution_zip(out_dir, contest):
    """打包下发 zip：每题 PDF + 合集 PDF + data/ 样例数据。
    返回 zip 路径；与 package.sh 共用同一实现。"""
    import zipfile
    name = safe_filename(contest.name)
    zip_path = out_dir / f"{name}-下发.zip"
    files = sorted(out_dir.glob("第*.pdf")) + [out_dir / f"{name}-题面合集.pdf"]
    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if f.exists():
                z.write(f, f.name)
                n += 1
        data = out_dir / "data"
        if data.exists():
            for f in sorted(data.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(out_dir))
                    n += 1
    log.info("下发包已生成: %s（%d 个文件，%.1f MB）",
             zip_path, n, zip_path.stat().st_size / 1e6)
    return zip_path


def write_package_script(out_dir, contest):
    """在输出目录生成 package.sh：重新编译（若有 tex/）+ 打包下发 zip。"""
    import os
    venv = os.path.relpath(VENV_BIN, out_dir).replace("\\", "/")
    root = os.path.relpath(ROOT, out_dir).replace("\\", "/")
    script = f"""#!/usr/bin/env bash
# 重新编译（若 tex/ 存在）并打包下发 zip：题面 PDF + data/
set -euo pipefail
cd "$(dirname "$0")"

if [ -d tex ] && [ -x tex/build.sh ]; then
  echo "[package] 重新编译 tex/ ..."
  (cd tex && ./build.sh)
fi

export PATH="$(pwd)/{venv}:$PATH"
"$(pwd)/{venv}/python" -c "
import pathlib, sys
sys.path.insert(0, r'{root}')
from main import create_distribution_zip
from model import Contest
create_distribution_zip(pathlib.Path('.'), Contest(name='{contest.name}'))
"
echo "[package] 完成"
"""
    (out_dir / "package.sh").write_text(script, encoding="utf-8")
    (out_dir / "package.sh").chmod(0o755)
    log.info("打包脚本已生成: %s", out_dir / "package.sh")


async def run(args):
    cfg = load_config(args.config)
    contest, problems = merge_config(args, cfg)

    WORK_DIR.mkdir(exist_ok=True)
    out_dir = args.output_dir / safe_filename(contest.name)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("比赛: %s | %s | %s（%s）", contest.name, contest.date, contest.time, contest.duration)
    log.info("题目: %s", ", ".join(p["pid"] for p in problems))
    log.info("输出: %s", out_dir)
    log.info("后端: %s", "LaTeX" if args.latex else "HTML")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            datas = await fetch_all(browser, problems, WORK_DIR)
            export_samples(datas, out_dir)
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
    write_package_script(out_dir, contest)
    if not args.no_merge:
        create_distribution_zip(out_dir, contest)
    log.info("全部完成。")


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
