"""LaTeX 题面生成：Markdown（洛谷 content 字段）→ LaTeX 源码 → PDF。

使用 OI-statement-LaTeX 风格模板（minted 样例框 + 行号），
公式为洛谷 markdown 中的 LaTeX 源，直接保留。
"""

import os
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLS = ROOT / "assets" / "latex" / "statement.cls"

# ---------------- Markdown → LaTeX 转换 ----------------

_MATH_DISPLAY_RE = re.compile(r"\$\$[\s\S]*?\$\$")
_MATH_RE = re.compile(r"\$[^$\n]+\$")


def _protect(text, regex, tokens):
    """把匹配内容替换为占位符，返回 (处理后的文本, 列表)。"""
    def repl(m):
        tokens.append(m.group(0))
        return f"\x00M{len(tokens) - 1}\x00"
    return regex.sub(repl, text), tokens


def _protect_math(text, tokens):
    """先保护 $$..$$ 多行公式，再保护 $..$ 行内公式。"""
    text, tokens = _protect(text, _MATH_DISPLAY_RE, tokens)
    text, tokens = _protect(text, _MATH_RE, tokens)
    return text, tokens


def _display_wrap(text):
    """$$...$$ 含 \\\\ 时转 gather* 环境（display math 的 \\ 不换行）。"""
    def repl(m):
        body = m.group(1)
        if "\\\\" in body:
            return "\\begin{gather*}" + body + "\\end{gather*}"
        return m.group(0)
    return re.sub(r"\$\$([\s\S]*?)\$\$", repl, text)


def _restore(text, tokens):
    return re.sub(r"\x00M(\d+)\x00", lambda m: tokens[int(m.group(1))], text)


def _escape_special(text):
    """转义 LaTeX 特殊字符（公式已被占位保护）。"""
    out = []
    for ch in text:
        if ch == "\\":
            out.append(r"\textbackslash{}")
        elif ch in "#%&_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append(r"\textasciitilde ")
        elif ch == "^":
            out.append(r"\textasciicircum ")
        else:
            out.append(ch)
    return "".join(out)


def _fix_math(text):
    """洛谷 markdown 表头常写未闭合的 $n，$ 数为奇数时自动补全。"""
    if "$" in text and text.count("$") % 2 == 1:
        return text + "$"
    return text


def _inline(text, images):
    """行内标记转换：公式保护 → 图片/链接/代码 → 转义 → 粗斜体。"""
    tokens = []
    text, tokens = _protect_math(text, tokens)
    text = _fix_math(text)
    text, tokens = _protect_math(text, tokens)
    # 图片先占位（生成的 LaTeX 命令需在转义之后展开）
    img_tokens = []
    def img_repl(m):
        url = m.group(2)
        alt = m.group(1)
        local = _download_image(url, images)
        if local:
            img_tokens.append(
                r"\begin{center}\includegraphics[width=0.8\textwidth]{" + local + r"}\end{center}")
            return f"\x00I{len(img_tokens) - 1}\x00"
        return alt or ""
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", img_repl, text)
    # 链接 [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 行内代码 `x`：先占位（生成的 \texttt 需在转义后展开）
    code_tokens = []
    def code_repl(m):
        code_tokens.append(m.group(1))
        return f"\x00C{len(code_tokens) - 1}\x00"
    text = re.sub(r"`([^`]+)`", code_repl, text)
    # 转义非公式部分（反斜杠、特殊字符）；未配对的 $ 转义为文本
    text = _escape_special(text)
    text = text.replace("$", r"\textdollar{}")
    # 恢复公式、图片与代码
    text = _restore(text, tokens)
    text = re.sub(r"\x00I(\d+)\x00", lambda m: img_tokens[int(m.group(1))], text)
    text = re.sub(r"\x00C(\d+)\x00",
                  lambda m: r"\texttt{" + _escape_special(code_tokens[int(m.group(1))]) + "}",
                  text)
    # 粗体 **x** → \stress（加粗 + 着重号，官方强调风格）；含公式/命令时退回 \textbf
    def bold_repl(m):
        t = m.group(1)
        if "$" in t or "\\" in t:
            return r"\textbf{" + t + "}"
        return r"\stress{" + t + "}"
    text = re.sub(r"\*\*([^*]+)\*\*", bold_repl, text)
    # 斜体 *x*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\textit{\1}", text)
    # $$..$$ 多行公式转 gather*（须在粗斜体处理后，避免 * 被误判）
    text = _display_wrap(text)
    return text


def _download_image(url, images):
    """下载题面图片到 .work/img/，返回相对文件名；失败返回 None。"""
    try:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/")[-1])
        img_dir = images or (ROOT / ".work" / "latex" / "img")
        img_dir.mkdir(parents=True, exist_ok=True)
        dest = img_dir / name
        if not dest.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        return dest.resolve().as_posix()
    except Exception:
        return None


def _split_blocks(md):
    """按行把 markdown 分成块：(类型, 内容)。"""
    blocks = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.lstrip().startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", "\n".join(code)))
        elif re.match(r"^\s*\|", line):
            tbl = []
            while i < len(lines) and re.match(r"^\s*\|", lines[i]):
                tbl.append(lines[i].strip())
                i += 1
            blocks.append(("table", tbl))
        elif re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            blocks.append(("itemize", items))
        elif re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < len(lines):
                if re.match(r"^\s*\d+\.\s+", lines[i]):
                    items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]))
                    i += 1
                elif not lines[i].strip():
                    i += 1
                elif re.match(r"^\s+\S", lines[i]):
                    items[-1] += "\n" + lines[i]
                    i += 1
                else:
                    break
            blocks.append(("enumerate", items))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^\s*\|", lines[i]) \
                    and not re.match(r"^\s*[-*]\s+", lines[i]) and not re.match(r"^\s*\d+\.\s+", lines[i]) \
                    and not lines[i].lstrip().startswith("```"):
                para.append(lines[i].strip())
                i += 1
            blocks.append(("para", "\n".join(para)))
    return blocks


def md_to_latex(md, images):
    """Markdown 文本 → LaTeX 源码（段落级）。"""
    md = re.sub(r"::anti-ai\[[^\]]*\]", "", md)
    # 删除 :::warning{...} 块标记行与结尾 ::: 行（含其他 ::: 块）
    md = re.sub(r"^:::[a-z-]*(\{[^}]*\})?\s*$", "", md, flags=re.M)
    md = re.sub(r"::[a-z-]+(\{[^}]*\})?", "", md)
    out = []
    for kind, content in _split_blocks(md):
        if kind == "para":
            text = _inline(content, images)
            out.append(text)
        elif kind == "itemize":
            items = "\n".join(r"  \item " + _inline(x, images) for x in content)
            out.append(r"\begin{itemize}" + "\n" + items + "\n\\end{itemize}")
        elif kind == "enumerate":
            items = "\n".join(r"  \item " + _inline(x, images) for x in content)
            out.append(r"\begin{enumerate}" + "\n" + items + "\n\\end{enumerate}")
        elif kind == "code":
            code = _escape_special(content)
            out.append(r"\begin{verbatim}" + code + r"\end{verbatim}")
        elif kind == "table":
            out.append(_table_to_latex(content))
    return "\n\n".join(out)



def _table_to_latex(rows):
    """markdown 表格 → 官方风格表格（tabularray）。

    - 列间竖线（vlines），左右边界无竖线
    - 顶/底/表头下粗线（hline{1}/{2}/{Z}），行间细线（hlines）
    - ^ 标记（与上一行同列相同）→ 纵向合并单元格（\SetCell[r=N]）
    - tabularray 自动跳过合并区域内的线（无 \cline/\multirow 兼容问题）
    """
    cells = [re.split(r"(?<!\\)\|", r[1:-1] if r.startswith("|") else r) for r in rows]
    cells = [[c.strip() for c in row] for row in cells]
    # 去掉分隔行 |:--:|:--:|
    cells = [row for row in cells if not all(re.fullmatch(r":?-+:?", c or "-") for c in row)]
    if not cells:
        return ""
    nrows, ncols = len(cells), max(len(r) for r in cells)
    for row in cells:
        row += [""] * (ncols - len(row))

    # 1) 展开 ^ 标记（与上方最近非 ^ 值相同）
    for r in range(1, nrows):
        for c in range(ncols):
            if cells[r][c] == "^":
                for rr in range(r - 1, -1, -1):
                    if cells[rr][c] != "^":
                        cells[r][c] = cells[rr][c]
                        break

    # 2) 每列连续相同值 → 纵向合并（表头行不参与）
    span = [[1] * ncols for _ in range(nrows)]
    covered = [[False] * ncols for _ in range(nrows)]
    for c in range(ncols):
        r = 1
        while r < nrows:
            val = cells[r][c]
            if not val:
                r += 1
                continue
            end = r
            while end + 1 < nrows and cells[end + 1][c] == val:
                end += 1
            if end > r:
                span[r][c] = end - r + 1
                for k in range(r + 1, end + 1):
                    covered[k][c] = True
            r = end + 1

    # 3) tabularray 输出：colspec 的 | 只画列间竖线（首尾不加 = 无边界竖线）
    #    \begin{center}：居中并保留上下间距（超宽表格的特殊处理由使用者自行调整）
    out = [r"\begin{center}\begin{tblr}{",
           "  colspec = {" + "c|" * (ncols - 1) + "c},",
           "  hlines,",
           "  hline{1} = {2pt},",
           "  hline{2} = {1.5pt},",
           "  hline{Z} = {2pt},",
           "}"]
    for r in range(nrows):
        parts = []
        for c in range(ncols):
            if covered[r][c]:
                parts.append("")
            elif span[r][c] > 1:
                parts.append(f"\\SetCell[r={span[r][c]}]{{c}}{_inline(cells[r][c], images=None)}")
            else:
                parts.append(_inline(cells[r][c], images=None))
        out.append("  " + " & ".join(parts) + r" \\")
    out.append(r"\end{tblr}\end{center}")
    return "\n".join(out)


# ---------------- 题面生成 ----------------

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


def fmt_time_range(raw):
    """'9:00-13:00' -> '09:00 $\\sim$ 13:00'（官方封面时间格式：补零 + 数学波浪号，
    两侧数学间距对称）。"""
    s = str(raw).strip().replace("~", "-").replace("～", "-")
    parts = re.split(r"\s*-\s*", s)
    if len(parts) == 2:
        def f(t):
            m = re.match(r"(\d{1,2}):(\d{2})", t.strip())
            return f"{int(m.group(1)):02d}:{m.group(2)}" if m else t.strip()
        return f"{f(parts[0])} $\\sim$ {f(parts[1])}"
    return s


def _dashfix(s):
    """日期数字之间的连字符改点号（YYYY.MM.DD 格式）。"""
    return re.sub(r"(?<=\d)-(?=\d)", ".", s)


def _english_name(problem):
    """模拟赛显示名：english 或空（不暴露洛谷题号）。"""
    return (problem.get("english") or "").strip()


def _ename(problem, index):
    """可执行文件名：english 或 t{编号}。"""
    return _english_name(problem) or f"t{index}"


def build_statement_tex(problem, contest, index, total, images):
    """生成单个题目的 .tex 文件内容（\section 形式，合集或单题共用）。"""
    sections = []
    md = problem["md"]
    content = md["content"]
    name = content.get("name", problem.get("pid", ""))
    samples = md.get("samples", [])

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

    samples = md.get("samples", [])
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

    en = _english_name(problem)
    head = (f"\\section{{{name}（\\englishname{{{en}}}）}}\n" if en
            else f"\\section{{{name}}}\n")
    return head + "\n".join(sections)


def _sample_block(text):
    """样例 → minted（行号 + tcolorbox 蓝框）。"""
    escaped = text.rstrip("\n").replace("\\", r"\textbackslash{}")
    return (r"\begin{minted}[linenos]{text}" + "\n" + escaped + "\n" + "\\end{minted}")


def build_cover_tex(contest, problems, images):
    """封面 .tex：比赛信息表格 + 提交文件名/编译选项 + 注意事项。

    版式对照 NOIP 官方封面：标题 22pt 黑体、时间行 15pt、
    信息表格（目录/可执行文件名/测试点数目等）、数据列居中。
    """
    names = [p["md"]["content"].get("name", p.get("pid", "")) for p in problems]
    enames = [_ename(p, i) for i, p in enumerate(problems, 1)]
    limits = []
    mems = []
    testcnt = []
    for p in problems:
        lim = p["md"].get("limits", {})
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
    if contest.get("date") or contest.get("time"):
        m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(contest.get("date", "")))
        date = (f"{m.group(1)} 年 {int(m.group(2))} 月 {int(m.group(3))} 日") if m else contest.get("date", "")
        # 官方时间格式：08:30 ∼ 13:00（补零 + 波浪线）
        t = fmt_time_range(contest.get("time", ""))
        duration = contest.get("duration", "")
        time_line = f"\\fontsize{{15}}{{22}}\\selectfont \\rmfamily 时间：{date} {t}（{duration}）\n\\vskip 0.5em"

    notes = contest.get("notes") or [
        "文件名（程序名和输入输出文件名）必须使用英文小写。",
        "main 函数的返回值类型必须是 int，程序正常结束时的返回值必须是 0。",
        "提交的程序代码文件的放置位置请参考各省的具体要求。",
        "因违反以上三点而出现的错误或问题，申诉时一律不予受理。",
        "若无特殊说明，结果的比较方式为全文比较（过滤行末空格及文本回车）。",
        "选手提交的程序源文件必须不大于 100KB。",
        "程序可使用的栈空间内存限制与题目的内存限制一致。",
    ]
    notes_tex = "\n".join(r"    \item " + _escape_special(n) for n in notes)

    return f"""\\begin{{titlepage}}
\\vspace*{{-20mm}}
\\begin{{center}}
{{\\fontsize{{22}}{{32}}\\selectfont \\heiti {_dashfix(contest['name'])}}}\\\\
\\vskip 0.6em
{time_line}
\\vskip 0.8em
\\end{{center}}

{table}

{{\\noindent\\hspace*{{1.5em}}\\rmfamily 提交源程序文件名}}\\par
{src_table}

{{\\noindent\\hspace*{{1.5em}}\\rmfamily 编译选项}}\\par
{compile_table}

{{\\noindent\\hspace*{{1.5em}}\\stress{{注意事项（请仔细阅读）}}}}\\par
\\begin{{enumerate}}
{notes_tex}
\\end{{enumerate}}
\\end{{titlepage}}
"""


_PREAMBLE = """\\documentclass{statement}
\\usepackage{tikz}
\\usepackage{ulem}
\\usepackage{tabularx}
\\usepackage{makecell}
\\usepackage{tabularray}
\\usepackage{color}
\\usepackage{xcolor}
\\usepackage{hyperref}
\\usepackage{minted}

\\title{__TITLE__}
\\date{}

\\begin{document}
__BODY__
\\end{document}
"""


def build_problem_doc(contest, index, total, body_rel):
    """单题完整文档：preamble + \input 引用题面 body（可独立编译）。"""
    title = _dashfix(contest["name"])
    return _PREAMBLE.replace("__TITLE__", title).replace("__BODY__", f"\\input{{{body_rel}}}")


def build_combined_doc(contest, problems, images, body_rels):
    """合集完整文档：封面 + \input 各题面 body（修改题面后合集同步更新）。"""
    cover = build_cover_tex(contest, problems, images)
    # 封面占第 1 页（无页码），正文从第 2 页开始（与官方一致）
    sections = "\n\n\\newpage\n\n".join(f"\\input{{{r}}}" for r in body_rels)
    body = cover + "\n\n\\setcounter{page}{2}\n\n\\newpage\n\n" + sections
    title = _dashfix(contest["name"])
    return _PREAMBLE.replace("__TITLE__", title).replace("__BODY__", body)


def build_build_script(tex_out):
    """生成 tex/ 目录的一键编译脚本：重新生成全部（题数 + 1 个 PDF）。"""
    # 相对路径找到项目 .venv（tex -> 比赛名 -> output -> 项目根）
    venv = os.path.relpath(ROOT / ".venv" / "bin", tex_out).replace("\\", "/")
    return f"""#!/usr/bin/env bash
# 一键重新编译全部题面：每道题 + 合集，共 {{$(ls *.tex | wc -l)}} 个 PDF
set -euo pipefail
cd "$(dirname "$0")"

# minted 需要 pygmentize，优先使用项目 .venv 的版本
export PATH="$(pwd)/{venv}:$PATH"

for f in *.tex; do
  xelatex -shell-escape -interaction=nonstopmode -halt-on-error "$f" >/dev/null 2>&1 || true
done
for f in *.tex; do
  xelatex -shell-escape -interaction=nonstopmode -halt-on-error "$f"
done
# 把生成的 PDF 复制到上级目录（output/<比赛名>/）
cp *.pdf ..
echo "完成：生成 $(ls *.pdf | wc -l) 个 PDF（已复制到上级目录）"
"""


# ---------------- 编译 ----------------

def compile_latex(tex_path, venv_bin):
    """用 xelatex -shell-escape 编译（两遍，处理 LastPage 引用）。
    返回 (True, PDF路径) 或 (False, 错误信息)。"""
    env = dict(os.environ)
    if venv_bin:
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    # 让 xelatex 能找到 assets/latex/statement.cls（末尾冒号保留默认路径）
    env["TEXINPUTS"] = str((ROOT / "assets" / "latex").resolve()) + os.pathsep + env.get("TEXINPUTS", "")
    for _ in range(2):
        r = subprocess.run(
            ["xelatex", "-shell-escape", "-interaction=nonstopmode",
             "-halt-on-error", tex_path.name],
            cwd=tex_path.parent, env=env,
            capture_output=True, text=True, timeout=600,
        )
    pdf = tex_path.with_suffix(".pdf")
    if pdf.exists():
        return True, pdf
    log = (tex_path.with_suffix(".log")).read_text(encoding="utf-8", errors="ignore")
    errs = [l for l in log.splitlines() if l.startswith("!")][:5]
    return False, "\n".join(errs) if errs else "PDF 未生成"
