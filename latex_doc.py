"""LaTeX 文档组装：题面/封面/合集/单题文档与 build.sh。"""

from markdown_latex import md_to_latex, _escape_special
from utils import fmt_time_range, dashfix

import os
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from markdown_latex import md_to_latex, _escape_special
from utils import fmt_time_range, dashfix

ROOT = Path(__file__).resolve().parent

_env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)


def _split_hint(hint):
    """按 ### 小标题分段 hint，返回 [(标题, 内容), ...]；### 之前的内容标题为空。"""
    parts = re.split(r"^###\s+(.+?)\s*$", hint, flags=re.M)
    out = []
    if parts[0].strip():
        out.append(("", parts[0]))
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        out.append((title, body))
    return out


def build_statement_tex(problem, contest, index, total, images):
    """生成单个题目的 .tex 文件内容（\section 形式，合集或单题共用）。"""
    sections = []
    content = problem.content
    name = content.get("name", problem.pid)
    samples = problem.md_samples

    def sec(title, body, force=True):
        if body and body.strip():
            sections.append(f"\\subsection[{title}]{{【{title}】}}\n\n{body}\n")

    if content.get("background"):
        sec("题目背景", md_to_latex(content["background"], images))
    if content.get("description"):
        sec("题目描述", md_to_latex(content["description"], images))
    if content.get("formatI"):
        sec("输入格式", "从标准输入中读入数据。\n\n" + md_to_latex(content["formatI"], images))
    if content.get("formatO"):
        sec("输出格式", "输出到标准输出中。\n\n" + md_to_latex(content["formatO"], images))

    samples = problem.md_samples
    if samples:
        for n, pair in enumerate(samples, 1):
            inp, outp = pair[0], pair[1] if len(pair) > 1 else ""
            sections.append(f"\\subsection[样例 {n} 输入]{{【样例 {n} 输入】}}\n"
                            + _sample_block(inp))
            if outp:
                sections.append(f"\\subsection[样例 {n} 输出]{{【样例 {n} 输出】}}\n"
                                + _sample_block(outp))

    if content.get("hint"):
        for htitle, hbody in _split_hint(content["hint"]):
            if not hbody.strip():
                continue
            m = re.search(r"样例\s*(\d+)\s*解释", htitle)
            if "解释" in htitle and "样例" in htitle:
                n = m.group(1) if m else (1 if samples else 1)
                sections.append(f"\\subsection[样例 {n} 解释]{{【样例 {n} 解释】}}\n\n"
                                + md_to_latex(hbody, images) + "\n")
            else:
                title = htitle or ("数据范围" if re.search(
                    r"数据范围|测试点|对于\s*100\s*%", hbody) else "提示")
                sec(title, md_to_latex(hbody, images))

    en = problem.english_name
    head = (f"\\section{{{name}（\\englishname{{{en}}}）}}\n" if en
            else f"\\section{{{name}}}\n")
    return head + "\n".join(sections)


def _sample_block(text):
    """样例 → minted（行号 + tcolorbox 蓝框）。"""
    escaped = text.rstrip("\n").replace("\\", r"\textbackslash{}")
    return _env.get_template("sample.tex.j2").render(content=escaped)


def build_cover_tex(contest, problems, images):
    """封面 .tex：比赛信息表格 + 提交文件名/编译选项 + 注意事项。

    版式对照 NOIP 官方封面：标题 22pt 黑体、时间行 15pt、
    信息表格（目录/可执行文件名/测试点数目等）、数据列居中。
    """
    names = [p.content.get("name", p.pid) for p in problems]
    enames = [p.exec_name for p in problems]
    limits = []
    mems = []
    testcnt = []
    for p in problems:
        lim = p.limits
        t = lim.get("time", [0])
        m = lim.get("memory", [0])
        limits.append(f"{max(t) / 1000:.1f} 秒" if t else "")
        mems.append(f"{max(m) / 1024:.0f} MiB" if m else "")
        testcnt.append(str(len(t)) if t else "")
    n = len(problems)

    # 数据列居中（官方封面表格数据列居中）
    X = ">{\\centering\\arraybackslash}X"
    spec_c = "|l|" + "|".join([X] * n) + "|"

    def row(label, cells, mono=False):
        cells = [rf"\texttt{{{c}}}" if mono else c for c in cells]
        return f"    {label} & " + " & ".join(cells) + r" \\" + "\n\\hline"

    table = "\\begin{center}\n\\begin{tabularx}{\\textwidth}{" + spec_c + "}\n\\hline\n"
    table += row("题目名称", names) + "\n"
    table += row("题目类型", ["传统型"] * n) + "\n"
    table += row("目录", enames, mono=True) + "\n"
    table += row("可执行文件名", enames, mono=True) + "\n"
    table += row("输入文件名", ["标准输入"] * n) + "\n"
    table += row("输出文件名", ["标准输出"] * n) + "\n"
    table += row("每个测试点时限", limits) + "\n"
    table += row("内存限制", mems) + "\n"
    if any(testcnt):
        table += row("测试点数目", testcnt) + "\n"
    table += "\\end{tabularx}\n\\end{center}"

    # 提交源程序文件名 / 编译选项（官方封面结构）
    src_table = ("\\begin{center}\n\\begin{tabularx}{\\textwidth}{" + spec_c + "}\n\\hline\n"
                 + row("对于 C++ 语言", [rf"\texttt{{{e}.cpp}}" for e in enames], mono=True) + "\n"
                 + "\\end{tabularx}\n\\end{center}")
    compile_table = ("\\begin{center}\n\\begin{tabularx}{\\textwidth}{" + spec_c + "}\n\\hline\n"
                     + f"    对于 C++ 语言 & \\multicolumn{{{n}}}{{>{{\\centering\\arraybackslash}}X|}}"
                     + r"{\texttt{-O2 -std=c++14 -static}} \\" + "\n\\hline\n"
                     + "\\end{tabularx}\n\\end{center}")

    time_line = ""
    if contest.date or contest.time:
        m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(contest.date))
        date = (f"{m.group(1)} 年 {int(m.group(2))} 月 {int(m.group(3))} 日") if m else contest.date
        # 官方时间格式：08:30 ∼ 13:00（补零 + 波浪线）
        t = fmt_time_range(contest.time)
        duration = contest.duration
        time_line = f"\\fontsize{{15}}{{22}}\\selectfont \\rmfamily 时间：{date} {t}（{duration}）\n\\vskip 0.5em"

    notes = contest.notes or [
        "文件名（程序名和输入输出文件名）必须使用英文小写。",
        "main 函数的返回值类型必须是 int，程序正常结束时的返回值必须是 0。",
        "提交的程序代码文件的放置位置请参考各省的具体要求。",
        "因违反以上三点而出现的错误或问题，申诉时一律不予受理。",
        "若无特殊说明，结果的比较方式为全文比较（过滤行末空格及文本回车）。",
        "选手提交的程序源文件必须不大于 100KB。",
        "程序可使用的栈空间内存限制与题目的内存限制一致。",
    ]
    notes_tex = "\n".join(r"    \item " + _escape_special(n) for n in notes)

    return _env.get_template("cover.tex.j2").render(
        contest_name=dashfix(contest.name),
        time_line=time_line,
        table=table,
        src_table=src_table,
        compile_table=compile_table,
        notes_tex=notes_tex,
    )


def build_problem_doc(contest, index, total, body_rel):
    """单题完整文档：preamble + \input 引用题面 body（可独立编译）。"""
    return _env.get_template("problem_doc.tex.j2").render(
        title=dashfix(contest.name),
        body=f"\\input{{{body_rel}}}",
    )


def build_combined_doc(contest, problems, images, body_rels):
    """合集完整文档：封面 + \input 各题面 body（修改题面后合集同步更新）。"""
    cover = build_cover_tex(contest, problems, images)
    # 封面占第 1 页（无页码），正文从第 2 页开始（与官方一致）
    sections = "\n\n\\newpage\n\n".join(f"\\input{{{r}}}" for r in body_rels)
    body = cover + "\n\n\\setcounter{page}{2}\n\n\\newpage\n\n" + sections
    return _env.get_template("problem_doc.tex.j2").render(
        title=dashfix(contest.name),
        body=body,
    )


def build_build_script(tex_out):
    """生成 tex/ 目录的一键编译脚本：重新生成全部（题数 + 1 个 PDF）。"""
    # 相对路径找到项目 .venv（tex -> 比赛名 -> output -> 项目根）
    venv = os.path.relpath(ROOT / ".venv" / "bin", tex_out).replace("\\", "/")
    return _env.get_template("build.sh.j2").render(venv=venv)


# ---------------- 编译 ----------------
