"""Markdown→LaTeX 转换器：markdown-it-py 解析（AST→LaTeX 渲染器）。

解析归标准库（blockquote/嵌套列表/围栏代码/强调/链接/图片），
洛谷方言保留两层：预处理（::anti-ai、折叠块标记行清理、公式保护）
与渲染层（$ 公式直通、^ 表格合并、callout、tblr 表格、minted 代码块）。
"""

import re
import urllib.request
from pathlib import Path

from markdown_it import MarkdownIt
from jinja2 import Environment, FileSystemLoader

from rules import CARET

ROOT = Path(__file__).resolve().parent

_env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)

# js-default preset 含表格规则（GFM 风格）
_md = MarkdownIt("js-default")

_MATH_DISPLAY_RE = re.compile(r"\$\$[\s\S]*?\$\$")
_MATH_RE = re.compile(r"\$[^$\n]+\$")


def _protect(text, regex, tokens):
    """把匹配内容替换为占位符，返回 (处理后的文本, 列表)。

    占位符用私用区 U+E000 包裹：NUL（\\x00）会被 markdown-it 的
    normalize 替换成 U+FFFD，导致解析后无法恢复（踩坑）。
    """
    def repl(m):
        tokens.append(m.group(0))
        return f"\ue000M{len(tokens) - 1}\ue000"
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
    return re.sub(r"\ue000M(\d+)\ue000", lambda m: tokens[int(m.group(1))], text)


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


def _list_to_tex(kind, items):
    env = "itemize" if kind == "itemize" else "enumerate"
    body = "\n".join("  \\item " + it for it in items)
    return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"


def _preprocess(md):
    """洛谷方言预处理：防作弊标记、折叠块标记行、行内 :: 标记。"""
    md = re.sub(r"::anti-ai\[[^\]]*\]", "", md)
    # 删除 :::warning{...} / ::::info[标题] 等折叠块标记行与结尾 ::: 行
    # （3+ 冒号，可选 [标题]/{参数}；内容保留，折叠语义丢弃）
    md = re.sub(r"^:{3,}[a-z-]*(\[[^\]]*\])?(\{[^}]*\})?\s*$", "", md, flags=re.M)
    md = re.sub(r"::[a-z-]+(\{[^}]*\})?", "", md)
    # 独立 --- 行在段落后会被 markdown-it 解析为 setext 标题（标准行为），
    # 洛谷题面中 --- 的意图是分隔线：换成 ___（同为 hr，且不触发 setext）
    md = re.sub(r"^---+$", "___", md, flags=re.M)
    return md


def _collect_until(children, start, close_type):
    """收集 children[start:j] 直到 close_type（不含）；返回 (j, 子列表)。

    j 指向 close token 本身，调用处赋给循环变量后由主循环 i += 1
    自然越过 close（若返回 j+1 会再跳过 close 后的第一个 token）。
    """
    j = start
    while j < len(children) and children[j].type != close_type:
        j += 1
    return j, children[start:j]


def _render_inline_children(children, images, math_tokens):
    """inline children → LaTeX（公式占位在 text token 中，最后统一恢复）。"""
    out = []
    i = 0
    n = len(children)
    while i < n:
        c = children[i]
        if c.type == "text":
            out.append(_escape_special(c.content))
        elif c.type == "softbreak":
            out.append("\n")
        elif c.type == "hardbreak":
            out.append(r"\\")
        elif c.type == "code_inline":
            out.append(r"\texttt{" + _escape_special(c.content) + "}")
        elif c.type == "strong_open":
            j, inner = _collect_until(children, i + 1, "strong_close")
            content = _render_inline_children(inner, images, math_tokens)
            # 含公式/命令时退回 \textbf（\stress 的着重号只适合纯文本）
            if "$" in content or "\\" in content:
                out.append(r"\textbf{" + content + "}")
            else:
                out.append(r"\stress{" + content + "}")
            i = j
        elif c.type == "em_open":
            j, inner = _collect_until(children, i + 1, "em_close")
            out.append(r"\textit{"
                       + _render_inline_children(inner, images, math_tokens) + "}")
            i = j
        elif c.type in ("link_open", "link_close"):
            pass  # 剥链接，保留文本
        elif c.type == "image":
            out.append(_render_image(c, images))
        elif c.type == "html_inline":
            out.append(_escape_special(c.content))
        i += 1
    text = "".join(out)
    text = _restore(text, math_tokens)
    text = _display_wrap(text)
    return text


def _render_image(c, images):
    url = c.attrs.get("src", "")
    alt = "".join(ch.content for ch in (c.children or []) if ch.type == "text")
    local = _download_image(url, images)
    if local:
        return (r"\begin{center}\includegraphics[width=0.8\textwidth]{"
                + local + r"}\end{center}")
    return alt or ""


def _render_cell_text(text, images, math_tokens):
    """表格单元格文本 → LaTeX。

    math_tokens 为主流程的公式占位列表：单元格文本可能已含主流程
    占位（M{n}\ue000，表格公式在解析前被整体保护），恢复时
    必须用同一列表；未保护的公式（直接调用 _table_to_latex 的测试
    场景）在此追加保护。
    """
    text, math_tokens = _protect_math(text, math_tokens)
    text = _fix_math(text)
    text, math_tokens = _protect_math(text, math_tokens)
    for t in _md.parse(text):
        if t.type == "inline" and t.children:
            return _render_inline_children(t.children, images, math_tokens)
    return ""


def _render_heading(tag, tokens, i, images, math_tokens):
    inline = tokens[i + 1]
    body = _render_inline_children(inline.children, images, math_tokens)
    level = int(tag[1])
    if level >= 3:
        # ### 及以上 → 小节标题（hint 的 ### 由 latex_doc._split_hint 处理，
        # 这里处理正文中残留的小标题）
        return r"\subsection[ " + body + " ]{【 " + body + " 】}"
    return body


def _collect_until_close(tokens, start, close_type):
    """收集 tokens[start:j] 直到 close_type（不含），返回 (j+1, 子列表)。"""
    j = start
    depth = 0
    while j < len(tokens):
        t = tokens[j]
        if t.type == close_type and depth == 0:
            break
        if t.type in ("bullet_list_open", "ordered_list_open", "blockquote_open"):
            depth += 1
        elif t.type in ("bullet_list_close", "ordered_list_close", "blockquote_close"):
            depth -= 1
        j += 1
    return j + 1, tokens[start:j]


def _render_tokens(tokens, images, math_tokens):
    """块级 token 流 → LaTeX（段落间 \n\n 分隔）。"""
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t.type == "paragraph_open":
            inline = tokens[i + 1]
            out.append(_render_inline_children(inline.children, images, math_tokens))
            i += 3
        elif t.type == "blockquote_open":
            j, body = _collect_until_close(tokens, i + 1, "blockquote_close")
            out.append("\\begin{callout}\n"
                       + _render_tokens(body, images, math_tokens)
                       + "\n\\end{callout}")
            i = j
        elif t.type in ("bullet_list_open", "ordered_list_open"):
            kind = "itemize" if t.type == "bullet_list_open" else "enumerate"
            j, body = _collect_until_close(
                tokens, i + 1,
                "bullet_list_close" if kind == "itemize" else "ordered_list_close")
            out.append(_render_list(kind, body, images, math_tokens))
            i = j
        elif t.type == "fence":
            info = (t.info or "").strip()
            lang = info.split()[0] if info else ""
            content = t.content.replace("\\", r"\textbackslash{}")
            # 代码块需要长行折行（breaklines；样例框不折行保持紧凑）
            out.append(_env.get_template("sample.tex.j2").render(
                content=content, lang=lang or "text", wrap=True))
            i += 1
        elif t.type == "table_open":
            j, rows = _collect_table(tokens, i + 1)
            out.append(_table_to_latex(rows, images, math_tokens))
            i = j
        elif t.type == "hr":
            out.append(r"\noindent\rule{\textwidth}{0.4pt}")
            i += 1
        elif t.type == "heading_open":
            out.append(_render_heading(t.tag, tokens, i, images, math_tokens))
            i += 3
        elif t.type == "code_block":
            content = t.content.replace("\\", r"\textbackslash{}")
            out.append(_env.get_template("sample.tex.j2").render(
                content=content, lang="text", wrap=True))
            i += 1
        elif t.type == "html_block":
            i += 1
        else:
            i += 1
    return "\n\n".join(out)


def _render_list(kind, body, images, math_tokens):
    """列表 token 体（list_item_open..list_item_close 为一项）→ itemize/enumerate。"""
    items = []
    i = 0
    n = len(body)
    while i < n:
        if body[i].type == "list_item_open":
            j, item_tokens = _collect_until_close(body, i + 1, "list_item_close")
            # 项内容：段落 + 嵌套列表（_render_tokens 输出 \n\n 分隔）
            rendered = _render_tokens(item_tokens, images, math_tokens)
            items.append(rendered)
            i = j
        else:
            i += 1
    return _list_to_tex(kind, items)


def _collect_table(tokens, start):
    """从 table_open 后收集表格行，返回 (结束索引, rows)。

    rows 为 | 分隔的文本行（首行表头；含分隔行由 _table_to_latex 过滤）。
    """
    rows = []
    i = start
    while i < len(tokens) and tokens[i].type != "table_close":
        if tokens[i].type == "tr_open":
            cells = []
            i += 1
            while i < len(tokens) and tokens[i].type != "tr_close":
                if tokens[i].type == "inline":
                    raw = "".join(ch.content for ch in (tokens[i].children or [])
                                  if ch.type == "text")
                    cells.append(raw)
                i += 1
            rows.append("|" + "|".join(cells) + "|")
        i += 1
    return i + 1, rows


def md_to_latex(md, images):
    """Markdown 文本 → LaTeX 源码（段落级）。"""
    math_tokens = []
    md = _preprocess(md)
    # 公式保护：先闭合的（$$/$），补全未闭合 $ 后再保护一次
    md, math_tokens = _protect_math(md, math_tokens)
    md = _fix_math(md)
    md, math_tokens = _protect_math(md, math_tokens)
    tokens = _md.parse(md)
    return _render_tokens(tokens, images, math_tokens)


def _table_to_latex(rows, images=None, math_tokens=None):
    """markdown 表格（| 文本行）转官方风格表格（tabularray）。

    - 列间竖线（vlines），左右边界无竖线
    - 顶/底/表头下粗线（hline 1/2/Z），行间细线（hlines）
    - 仅 ^ 标记处合并：^ 表示「与上一行同列相同」，其所在行与来源行
      纵向合并（SetCell[r=N]）；普通相同值不合并
    - tabularray 自动跳过合并区域内的线（无 cline/multirow 兼容问题）
    """
    if math_tokens is None:
        math_tokens = []
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
                parts.append(f"\\SetCell[r={span[r][c]}]{{c}}"
                             + _render_cell_text(cells[r][c], images, math_tokens))
            else:
                parts.append(_render_cell_text(cells[r][c], images, math_tokens))
        rows.append("  " + " & ".join(parts) + r" \\")
    return _env.get_template("tblr.tex.j2").render(
        colspec="c|" * (ncols - 1) + "c",
        rows="\n".join(rows),
    )


# ---------------- 题面生成 ----------------
