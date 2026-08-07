"""Markdown→LaTeX 转换器：洛谷题面 Markdown 源转 LaTeX 源码。"""

import re
import urllib.request
from pathlib import Path

from rules import CARET
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent

_env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)


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
    # 下划线斜体 _x_（洛谷语法）：先占位，避免 _ 被转义（*x* 不受转义影响，原地处理）
    em_tokens = []
    def em_repl(m):
        em_tokens.append(m.group(1))
        return f"\x00E{len(em_tokens) - 1}\x00"
    text = re.sub(r"_([^_]+)_", em_repl, text)
    # 转义非公式部分（反斜杠、特殊字符）；未配对的 $ 转义为文本
    text = _escape_special(text)
    text = text.replace("$", r"\textdollar{}")
    # 恢复公式、图片与代码
    text = _restore(text, tokens)
    text = re.sub(r"\x00I(\d+)\x00", lambda m: img_tokens[int(m.group(1))], text)
    text = re.sub(r"\x00C(\d+)\x00",
                  lambda m: r"\texttt{" + _escape_special(code_tokens[int(m.group(1))]) + "}",
                  text)
    text = re.sub(r"\x00E(\d+)\x00",
                  lambda m: r"\textit{" + _restore(em_tokens[int(m.group(1))], tokens) + "}",
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
            # 围栏语言（```cpp 等）；洛谷未指定语言 fallback C++，但
            # 转换端保守处理为 text（避免误高亮，如样例数据块）
            rest = line.strip()[3:].strip()
            lang = rest.split()[0] if rest else ""
            code = []
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", (lang, "\n".join(code))))
        elif re.match(r"^\s*\|", line):
            tbl = []
            while i < len(lines) and re.match(r"^\s*\|", lines[i]):
                tbl.append(lines[i].strip())
                i += 1
            blocks.append(("table", tbl))
        elif re.match(r"^\s*---+\s*$", line):
            # 分割线（markdown ---）
            i += 1
            blocks.append(("hr", None))
        elif re.match(r"^\s*>\s*$", line) or re.match(r"^\s*>\s", line):
            # 引用块：连续 > 行；单独的 > 作为段分隔
            quote = []
            while i < len(lines):
                l = lines[i]
                if re.match(r"^\s*>\s*$", l):
                    quote.append("")
                    i += 1
                elif re.match(r"^\s*>\s", l):
                    quote.append(re.sub(r"^\s*>\s*", "", l))
                    i += 1
                else:
                    break
            blocks.append(("quote", "\n".join(quote)))
        elif re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            block, i = _collect_list(lines, i, len(line) - len(line.lstrip()))
            blocks.append(block)
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^\s*\|", lines[i]) \
                    and not re.match(r"^\s*[-*]\s+", lines[i]) and not re.match(r"^\s*\d+\.\s+", lines[i]) \
                    and not re.match(r"^\s*>\s*$", lines[i]) and not re.match(r"^\s*>\s", lines[i]) \
                    and not re.match(r"^\s*---+\s*$", lines[i]) \
                    and not lines[i].lstrip().startswith("```"):
                para.append(lines[i].strip())
                i += 1
            blocks.append(("para", "\n".join(para)))
    return blocks


_LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def _list_to_tex(kind, items):
    env = "itemize" if kind == "itemize" else "enumerate"
    body = "\n".join("  \\item " + it for it in items)
    return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"


def _collect_list(lines, i, base_indent):
    """收集缩进层级 >= base_indent 的列表（支持嵌套子列表与缩进续行）。

    返回 (("itemize"|"enumerate", [项文本...]), 下一行索引)；
    嵌套子列表以 LaTeX 片段形式附加到所属项文本中。
    """
    items = []
    kind = None
    while i < len(lines):
        m = _LIST_RE.match(lines[i])
        if not m or len(m.group(1)) < base_indent:
            break
        indent = len(m.group(1))
        cur_kind = "enumerate" if m.group(2)[0].isdigit() else "itemize"
        if kind is None:
            kind = cur_kind
        if cur_kind != kind:
            break
        text = m.group(3)
        i += 1
        # 收集项内内容：空行跳过、更深缩进的列表嵌套、缩进非列表行续行
        nested = []
        while i < len(lines):
            line = lines[i]
            m2 = _LIST_RE.match(line)
            if m2 and len(m2.group(1)) > indent:
                sub, i = _collect_list(lines, i, len(m2.group(1)))
                _NESTED_TOKENS.append(sub)
                text += "\n" + f"\x00NL{len(_NESTED_TOKENS) - 1}\x00"
            elif m2:
                break
            elif not line.strip():
                i += 1
            elif len(line) - len(line.lstrip()) > indent:
                text += "\n" + line
                i += 1
            else:
                break
        if nested:
            text += "\n" + "\n".join(nested)
        items.append(text)
    return (kind, items), i


_NESTED_TOKENS = []


def md_to_latex(md, images):
    """Markdown 文本 → LaTeX 源码（段落级）。"""
    _NESTED_TOKENS.clear()
    md = re.sub(r"::anti-ai\[[^\]]*\]", "", md)
    # 删除 :::warning{...} / ::::info[标题] 等折叠块标记行与结尾 ::: 行
    # （3+ 冒号，可选 [标题]/{参数}；内容保留，折叠语义丢弃）
    md = re.sub(r"^:{3,}[a-z-]*(\[[^\]]*\])?(\{[^}]*\})?\s*$", "", md, flags=re.M)
    md = re.sub(r"::[a-z-]+(\{[^}]*\})?", "", md)
    out = []
    for kind, content in _split_blocks(md):
        if kind == "para":
            text = _inline(content, images)
            out.append(text)
        elif kind in ("itemize", "enumerate"):
            def restore(m):
                sub_kind, sub_items = _NESTED_TOKENS[int(m.group(1))]
                rendered = [_inline(x, images) for x in sub_items]
                rendered = [re.sub(r"\x00NL(\d+)\x00", restore, x) for x in rendered]
                return _list_to_tex(sub_kind, rendered)
            items = [_inline(x, images) for x in content]
            items = [re.sub(r"\x00NL(\d+)\x00", restore, x) for x in items]
            out.append(_list_to_tex(kind, items))
        elif kind == "code":
            # 代码块 → minted 语法高亮（语言标记来自围栏，如 ```cpp）；
            # 无语言 → text。反斜杠转义与样例框一致（minted 的
            # commandchars 会消费 \）；样例框样式由 statement.cls 的
            # \BeforeBeginEnvironment{minted} 统一包裹
            lang = content[0] if isinstance(content, tuple) else ""
            body = content[1] if isinstance(content, tuple) else content
            body = body.replace("\\", r"\textbackslash{}")
            # 代码块需要长行折行（breaklines；样例框不折行保持紧凑）
            out.append(_env.get_template("sample.tex.j2").render(
                content=body, lang=lang or "text", wrap=True))
        elif kind == "table":
            out.append(_table_to_latex(content))
        elif kind == "hr":
            out.append(r"\noindent\rule{\textwidth}{0.4pt}")
        elif kind == "quote":
            # 引用块：admonition 风格 callout（statement.cls 定义）
            body = "\n\n".join(_inline(x, images) for x in content.split("\n\n"))
            out.append("\\begin{callout}\n" + body + "\n\\end{callout}")
    return "\n\n".join(out)



def _table_to_latex(rows):
    """markdown 表格转官方风格表格（tabularray）。

    - 列间竖线（vlines），左右边界无竖线
    - 顶/底/表头下粗线（hline 1/2/Z），行间细线（hlines）
    - 仅 ^ 标记处合并：^ 表示「与上一行同列相同」，其所在行与来源行
      纵向合并（SetCell[r=N]）；普通相同值不合并
    - tabularray 自动跳过合并区域内的线（无 cline/multirow 兼容问题）
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

    # 1) 记录 ^ 位置，再展开（与上方最近非 ^ 值相同）
    caret = [[cells[r][c] == CARET for c in range(ncols)] for r in range(nrows)]
    for r in range(1, nrows):
        for c in range(ncols):
            if cells[r][c] == CARET:
                for rr in range(r - 1, -1, -1):
                    if cells[rr][c] != "^":
                        cells[r][c] = cells[rr][c]
                        break

    # 2) 仅对 ^ 所在列合并：^ 连续段与其来源行合并（表头行不参与）
    span = [[1] * ncols for _ in range(nrows)]
    covered = [[False] * ncols for _ in range(nrows)]
    for c in range(ncols):
        r = 1
        while r < nrows:
            if caret[r][c]:
                end = r
                while end + 1 < nrows and caret[end + 1][c]:
                    end += 1
                span[r - 1][c] = end - (r - 1) + 1
                for k in range(r, end + 1):
                    covered[k][c] = True
                r = end + 1
            else:
                r += 1

    # 3) tabularray 输出：colspec 的 | 只画列间竖线（首尾不加 = 无边界竖线）
    #    \begin{center}：居中并保留上下间距（超宽表格的特殊处理由使用者自行调整）
    rows = []
    for r in range(nrows):
        parts = []
        for c in range(ncols):
            if covered[r][c]:
                parts.append("")
            elif span[r][c] > 1:
                parts.append(f"\\SetCell[r={span[r][c]}]{{c}}{_inline(cells[r][c], images=None)}")
            else:
                parts.append(_inline(cells[r][c], images=None))
        rows.append("  " + " & ".join(parts) + r" \\")
    return _env.get_template("tblr.tex.j2").render(
        colspec="c|" * (ncols - 1) + "c",
        rows="\n".join(rows),
    )


# ---------------- 题面生成 ----------------
