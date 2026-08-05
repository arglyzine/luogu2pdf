#!/usr/bin/env python3
"""示例 PDF 生成：读 example.json，走工具真实渲染路径，生成
自包含 example.tex（可直接 xelatex 编译的样例）并编译为 PDF，
附带渲染 README 截图。

用法：python3 example/build_example.py
产物：example/example.tex（入库）、example/example.pdf、example/*.png
"""

import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from compile import compile_latex
from latex_doc import build_cover_tex, build_statement_tex
from model import Contest, Problem
from utils import dashfix

VENV_BIN = ROOT / ".venv" / "bin"
PDF_NAME = "example.pdf"


def main():
    cfg = json.loads((HERE / "example.json").read_text(encoding="utf-8"))
    contest = Contest(
        name=cfg["contest"],
        date=cfg.get("date", ""),
        time=cfg.get("time", ""),
        duration=cfg.get("duration", ""),
        notes=cfg.get("notes") or [],
    )
    datas = []
    for i, p in enumerate(cfg["problems"], 1):
        datas.append(Problem(
            pid=p["pid"],
            title=p["title"],
            english=p.get("english", ""),
            type=p.get("type", "传统型"),
            index=i,
            file_io=p.get("io") == "file",
            content=p.get("content", {}),
            limits=p.get("limits", {}),
            md_samples=p.get("samples", []),
        ))

    # 自包含 tex：封面 + 题面全部内联（无 \input），可直接 xelatex 编译
    images = HERE / "img"
    images.mkdir(exist_ok=True)
    cover = build_cover_tex(contest, datas, images)
    bodies = "\n\n\\newpage\n\n".join(
        build_statement_tex(d, contest, d.index, len(datas), images)
        for d in datas)
    body = cover + "\n\n\\setcounter{page}{2}\n\n\\newpage\n\n" + bodies

    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      autoescape=False)
    example_tex = HERE / "example.tex"
    example_tex.write_text(
        env.get_template("problem_doc.tex.j2").render(
            title=dashfix(contest.name), body=body),
        encoding="utf-8")
    print(f"已生成 {example_tex}")

    # 编译（compile_latex 自带页数漂移校验，必要时第三遍）
    ok, pdf = compile_latex(example_tex, VENV_BIN)
    if not ok:
        print(f"编译失败: {pdf}")
        sys.exit(1)
    if pdf.resolve() != (HERE / PDF_NAME).resolve():
        shutil.copy(pdf, HERE / PDF_NAME)
    print(f"已生成 {HERE / PDF_NAME}")

    # 渲染 README 截图
    try:
        import fitz
    except ImportError:
        print("跳过截图（缺少 PyMuPDF）")
        return
    doc = fitz.open(HERE / PDF_NAME)
    doc[0].get_pixmap(dpi=100).save(HERE / "cover.png")
    doc[1].get_pixmap(dpi=100).save(HERE / "page-statement.png")
    # 第一题末页：含「样例 1 解释」的页（数据范围表格/提示，第一题独有）
    for pi in range(1, len(doc)):
        t = doc[pi].get_text().replace(" ", "").replace("\n", "")
        if "样例1解释" in t:
            doc[pi].get_pixmap(dpi=100).save(HERE / "page-tail.png")
            break
    print("截图已更新")


if __name__ == "__main__":
    main()
