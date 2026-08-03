"""NOIP 官方风格题面 HTML 模板生成。

版式参考 CCF NOIP 2024 官方题面 PDF：
- 每页页眉：左侧比赛名，右侧「题名（英文名）」，下横线
- 标题居中加粗：「题名（英文名）」
- 节标题左对齐加粗：【题目描述】【输入格式】【输出格式】【样例 1 输入】...
- 正文宋体、首行缩进，样例代码框，页脚「第 X 页 共 Y 页」
- 封面页：比赛信息表格 + 注意事项
"""

import re
import string
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KATEX_CSS = ROOT / "assets" / "katex" / "katex.min.css"
KATEX_FONTS = ROOT / "assets" / "katex" / "fonts"
SERIF_FONT = ROOT / "assets" / "fonts" / "NotoSerifCJKsc-Regular.otf"

BASE_CSS = string.Template("""
@font-face {
  font-family: 'Noto Serif CJK SC';
  src: url('$serif_font');
  font-weight: normal; font-style: normal;
}
@page { size: A4; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Noto Serif CJK SC', 'Noto Sans CJK SC', 'Source Han Serif SC', serif;
  font-size: 12pt; line-height: 1.6; color: #000;
}
/* ---- 页眉（fixed 元素在 Chromium 打印时每页重复） ---- */
.page-header {
  position: fixed; top: 0; left: 0; right: 0;
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 10pt; padding: 0 0 1.5mm;
  border-bottom: 1pt solid #000; background: #fff; z-index: 10;
}
body.with-header { padding-top: 12mm; }
.page-header .right { font-weight: bold; }
/* 合集中的流式页眉（仅每节首页显示） */
.flow-header {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 10pt; padding: 2mm 0 1.5mm; margin: 0 0 4mm;
  border-bottom: 1pt solid #000;
}
.flow-header .right { font-weight: bold; }
/* ---- 标题（黑体，参考 OI-statement-LaTeX 的 \Large\sf） ---- */
h1.title {
  text-align: center; font-size: 17pt; font-weight: bold;
  margin: 10mm 0 12mm;
  font-family: 'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
/* ---- 节标题（黑体不加粗，字号比正文大一号，参考官方题面） ---- */
h2.sec {
  font-size: 14pt; font-weight: normal; text-align: left;
  margin: 7mm 0 3mm; text-indent: 1em;
  font-family: 'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
/* ---- 正文内容（匹配洛谷提取的 .lfe-marked 容器） ---- */
.lfe-marked p { text-indent: 2em; margin: 1.5mm 0; }
.lfe-marked ul, .lfe-marked ol { margin: 1.5mm 0; padding-left: 8mm; }
.lfe-marked li { margin: 0.5mm 0; }
.lfe-marked table { border-collapse: collapse; margin: 2.5mm auto; border-top: 2pt solid #000; border-bottom: 2pt solid #000; }
/* 注意：Chromium 打印会丢弃 <1px 的 border，细线用 1px */
.lfe-marked th, .lfe-marked td { padding: 1mm 4mm; border-left: 1px solid #000; border-right: 1px solid #000; }
.lfe-marked th { border-bottom: 1.5pt solid #000; font-weight: normal; }
.lfe-marked td { border-bottom: 1px solid #000; }
.lfe-marked tr:last-child td { border-bottom: none; }
/* 去掉左右边界竖线（列间线保留） */
.lfe-marked tr > :first-child { border-left: none; }
.lfe-marked tr > :last-child { border-right: none; }
/* 数据范围表无特殊处理（样式已统一） */
.lfe-marked code {
  font-family: 'DejaVu Sans Mono', 'Noto Sans Mono CJK SC', monospace;
  font-size: 10.5pt;
}
.lfe-marked img { max-width: 88%; display: block; margin: 2.5mm auto; }
.lfe-marked blockquote { margin: 2mm 0; padding: 0 4mm; border-left: 2pt solid #999; }
.lfe-marked .katex-display { margin: 3mm 0; }
/* 强调文字：加粗 + 着重号（官方 \stress 风格） */
.lfe-marked strong {
  font-weight: bold;
  text-emphasis: filled dot;
  -webkit-text-emphasis: filled dot;
  text-emphasis-position: under;
  -webkit-text-emphasis-position: under;
}
/* ---- 样例框（蓝色细边框，参考 tcolorbox colframe=blue, boxrule=0.5pt） ---- */
pre.sample {
  border: 0.5pt solid #2E74B5; padding: 2mm 3.5mm; margin: 1.5mm 0 4mm;
  white-space: pre-wrap; word-break: break-all;
  font-family: 'DejaVu Sans Mono', 'Noto Sans Mono CJK SC', monospace;
  font-size: 10.5pt; line-height: 1.6;
}
.ln { color: #808080; user-select: none; }
/* ---- 封面 ---- */
.cover-title { text-align: center; font-size: 20pt; font-weight: bold; margin: 14mm 0 4mm; }
.cover-subtitle { text-align: center; font-size: 14pt; font-weight: bold; margin: 0 0 3mm; }
.cover-time { text-align: center; font-size: 12pt; margin: 0 0 8mm; }
table.cover { border-collapse: collapse; margin: 0 auto 8mm; }
table.cover th, table.cover td { border: 0.75pt solid #000; padding: 1.5mm 4mm; font-size: 11pt; }
table.cover th { font-weight: bold; white-space: nowrap; }
table.cover td { text-align: center; }
.cover-section { text-align: center; font-size: 12pt; font-weight: bold; margin: 4mm 0 1.5mm; }
.cover-line { text-align: center; font-size: 11pt; margin: 0 0 2mm; }
ol.cover-notes { font-size: 10.5pt; margin: 1mm auto 0; max-width: 165mm; }
ol.cover-notes li { margin: 0.5mm 0; }
""")

KATEX_ESCAPE = None


def _katex_css():
    """读取本地 KaTeX 样式，字体路径转 file:// 绝对路径。"""
    global KATEX_ESCAPE
    css = KATEX_CSS.read_text(encoding="utf-8")
    fonts_uri = KATEX_FONTS.resolve().as_uri()
    return css.replace("url(fonts/", f"url({fonts_uri}/")


def _base_style(with_header):
    css = BASE_CSS.substitute(serif_font=SERIF_FONT.resolve().as_uri())
    if not with_header:
        css += "\n.page-header { display: none; }\n"
    return "<style>" + css + _katex_css() + "</style>"


# ---------------- 格式化辅助 ----------------

def fmt_date(date_str):
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(date_str))
    if m:
        return f"{m.group(1)} 年 {int(m.group(2))} 月 {int(m.group(3))} 日"
    return str(date_str)


def fmt_time_range(raw):
    """'9:00-13:00' -> '09:00 ～ 13:00'；'8:30~12:00' 同样处理。"""
    s = str(raw).strip().replace("~", "-").replace("～", "-")
    parts = re.split(r"\s*-\s*", s)
    if len(parts) == 2:
        def f(t):
            m = re.match(r"(\d{1,2}):(\d{2})", t.strip())
            return f"{int(m.group(1)):02d}:{m.group(2)}" if m else t.strip()
        return f"{f(parts[0])} ～ {f(parts[1])}"
    return s


def fmt_time_limit(raw):
    """'500ms'->'0.5 秒'；'1.00s'->'1.0 秒'；'1.00s ~ 1.20s'->'1.0 秒 ～ 1.2 秒'。"""
    s = raw.strip().lower()
    def one(x):
        m = re.match(r"([\d.]+)\s*ms$", x)
        if m:
            return f"{float(m.group(1))/1000:.1f} 秒"
        m = re.match(r"([\d.]+)\s*s$", x)
        if m:
            return f"{float(m.group(1)):.1f} 秒"
        return x
    if "~" in s or "～" in s:
        a, b = re.split(r"\s*[~～]\s*", s)
        return f"{one(a)} ～ {one(b)}"
    return one(s)


def fmt_memory(raw):
    """'16.00MB'->'16 MiB'；'512.00MB'->'512 MiB'；'1GB'->'1024 MiB'。"""
    s = raw.strip().upper()
    m = re.match(r"([\d.]+)\s*(KB|MB|GB)$", s)
    if m:
        v, u = float(m.group(1)), m.group(2)
        v = v * 1024 if u == "GB" else v / 1024 if u == "KB" else v
        return f"{v:g} MiB"
    return s


def safe_filename(name, fallback="题目"):
    return re.sub(r'[\\/:*?"<>|\s]+', "-", name).strip("-") or fallback


# ---------------- 内容组装 ----------------

def _numbered_sample(text):
    """给样例代码添加行号（灰色行号，参考 \theFancyVerbLine 的灰色样式）。"""
    lines = text.rstrip("\n").split("\n")
    width = len(str(len(lines)))
    numbered = []
    for i, line in enumerate(lines, 1):
        numbered.append(f'<span class="ln">{i:>{width}}</span>  {escape(line)}')
    return '<pre class="sample">' + "\n".join(numbered) + "</pre>"


SECTION_MAP = [
    ("题目背景", "题目背景"),
    ("题目描述", "题目描述"),
    ("输入格式", "输入格式"),
    ("输出格式", "输出格式"),
    ("说明/提示", None),  # 动态标题，见 hint_title()
]

HINT_KEYWORDS = re.compile(r"数据范围|对于\s*100\s*%\s*的数据|测试点")


def hint_title(content):
    """根据内容判断节标题：含数据范围关键词时用【数据范围】，否则【提示】。"""
    # 去掉 HTML 标签再检测关键词（KaTeX span 会打断正则）
    text = re.sub(r"<[^>]+>", " ", content)
    if HINT_KEYWORDS.search(text):
        return "数据范围"
    return "提示"


def _split_hint_html(hint_html):
    """把说明/提示的 HTML 按 <h3> 小标题拆分成 [(标题, 内容HTML), ...]。"""
    parts = re.split(r"(<h3[^>]*>.*?</h3>)", hint_html, flags=re.S)
    out = []
    cur_title, cur_body = "", []
    for part in parts:
        m = re.match(r"<h3[^>]*>(.*?)</h3>", part, flags=re.S)
        if m:
            if cur_title or cur_body:
                out.append((cur_title, "".join(cur_body)))
            cur_title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            cur_body = []
        else:
            cur_body.append(part)
    if cur_title or cur_body:
        out.append((cur_title, "".join(cur_body)))
    # 丢弃无标题且无实际内容（纯标签）的条目，如 h3 前的 lfe-marked wrap 开标签
    return [(t, b) for t, b in out if t or re.search(r"\S", re.sub(r"<[^>]+>", "", b))]


def _sections_html(problem):
    """题目各节 HTML：节标题【】格式 + 内容原样保留。"""
    html = []
    sections = problem.get("sections", {})
    samples = problem.get("samples", [])

    # 主体节：背景/描述/输入/输出
    for name, title in SECTION_MAP:
        content = sections.get(name)
        if not content or name == "说明/提示":
            continue
        if title is None:
            title = hint_title(content)
        html.append(f'<h2 class="sec">【{escape(title)}】</h2>')
        prefix = {"输入格式": "从标准输入中读入数据。",
                  "输出格式": "输出到标准输出中。"}.get(name)
        if prefix:
            html.append(f'<div class="marked"><p>{prefix}</p></div>')
        cls = "marked datarange" if title == "数据范围" else "marked"
        html.append(f'<div class="{cls}">{content}</div>')

    # 样例输入/输出
    if samples:
        groups = {}
        for s in samples:
            groups.setdefault(s["n"], {})[s["kind"]] = s["text"]
        for n in sorted(groups):
            g = groups[n]
            if "输入" in g:
                html.append(f'<h2 class="sec">【样例 {n} 输入】</h2>')
                html.append(_numbered_sample(g["输入"]))
            if "输出" in g:
                html.append(f'<h2 class="sec">【样例 {n} 输出】</h2>')
                html.append(_numbered_sample(g["输出"]))

    # 说明/提示：按 ### 小标题拆分（样例解释在样例之后独立成节）
    hint_html = sections.get("说明/提示")
    if hint_html:
        for htitle, hbody in _split_hint_html(hint_html):
            if not hbody.strip():
                continue
            m = re.search(r"样例\s*(\d+)\s*解释", htitle)
            if "解释" in htitle and "样例" in htitle:
                n = m.group(1) if m else (1 if samples else 1)
                html.append(f'<h2 class="sec">【样例 {n} 解释】</h2>')
                html.append(f'<div class="marked">{hbody}</div>')
            else:
                t = htitle or hint_title(hbody)
                cls = "marked datarange" if t == "数据范围" else "marked"
                html.append(f'<h2 class="sec">【{escape(t)}】</h2>')
                html.append(f'<div class="{cls}">{hbody}</div>')

    return "\n".join(html)


# ---------------- 页面组装 ----------------

def _english_name(problem):
    """模拟赛显示名：english 或空（不暴露洛谷题号）。"""
    return (problem.get("english") or "").strip()


def _exec_name(problem, index):
    """可执行文件名：english 或 t{编号}。"""
    return _english_name(problem) or f"t{index}"


def _header_html(problem, flow):
    name = problem["contest_name"]
    title = problem.get("title", "")
    en = _english_name(problem)
    right = f"{escape(title)}（{escape(en)}）" if en else escape(title)
    if flow:
        return f'<div class="flow-header"><span>{escape(name)}</span><span class="right">{right}</span></div>'
    return f'<div class="page-header"><span>{escape(name)}</span><span class="right">{right}</span></div>'


def build_problem_html(problem, contest, index, total):
    """单题完整 HTML（页眉 fixed，每页重复）。"""
    problem = dict(problem)
    problem["contest_name"] = contest["name"]
    title = problem.get("title", "")
    en = _english_name(problem)
    title_html = f"{escape(title)}（{escape(en)}）" if en else escape(title)
    head = f"""
<div class="page-header"><span>{escape(contest['name'])}</span><span class="right">{title_html}</span></div>
<h1 class="title">{title_html}</h1>
"""
    body = _sections_html(problem)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>第{index}题 {escape(title)}</title>
{_base_style(with_header=True)}
</head>
<body class="with-header">
{head}
{body}
</body>
</html>
"""


def build_problem_section(problem, contest):
    """合集中的题面片段（流式页眉，仅本题首页显示）。"""
    problem = dict(problem)
    problem["contest_name"] = contest["name"]
    title = problem.get("title", "")
    en = _english_name(problem)
    title_html = f"{escape(title)}（{escape(en)}）" if en else escape(title)
    head = f"""
<div style="page-break-before: always;"></div>
{_header_html(problem, flow=True)}
<h1 class="title">{title_html}</h1>
"""
    return head + _sections_html(problem)


def build_cover_html(contest, problems):
    """封面 HTML：比赛信息表格 + 注意事项。"""
    rows = []
    names = [escape(p.get("title", p.get("pid", ""))) for p in problems]
    enames = [_exec_name(p, i) for i, p in enumerate(problems, 1)]
    types = [escape(p.get("type", "传统型")) for p in problems]
    limits = [f"{fmt_time_limit(p.get('timeLimit', ''))}" for p in problems]
    mems = [f"{fmt_memory(p.get('memoryLimit', ''))}" for p in problems]
    ios = ["标准输入" for _ in problems]
    oos = ["标准输出" for _ in problems]

    def row(label, cells):
        tds = "".join(f"<td>{c}</td>" for c in cells)
        return f"<tr><th>{label}</th>{tds}</tr>"

    table = (
        "<table class=\"cover\">"
        + row("题目名称", names)
        + row("题目类型", types)
        + row("可执行文件名", enames)
        + row("输入文件名", ios)
        + row("输出文件名", oos)
        + row("每个测试点时限", limits)
        + row("内存限制", mems)
        + "</table>"
    )

    time_line = ""
    if contest.get("date") or contest.get("time"):
        parts = []
        if contest.get("date"):
            parts.append(fmt_date(contest["date"]))
        if contest.get("time"):
            parts.append(f"{fmt_time_range(contest['time'])}（{contest.get('duration', '')}）")
        time_line = f'<p class="cover-time">时间：{"　".join(parts)}</p>'

    notes = contest.get("notes") or [
        "文件名（程序名和输入输出文件名）必须使用英文小写。",
        "main 函数的返回值类型必须是 int，程序正常结束时的返回值必须是 0。",
        "提交的程序代码文件的放置位置请参考各省的具体要求。",
        "因违反以上三点而出现的错误或问题，申诉时一律不予受理。",
        "若无特殊说明，结果的比较方式为全文比较（过滤行末空格及文本回车）。",
        "选手提交的程序源文件必须不大于 100KB。",
        "程序可使用的栈空间内存限制与题目的内存限制一致。",
    ]
    notes_html = "".join(f"<li>{escape(n)}</li>" for n in notes)

    body = f"""
<div class="cover-title">{escape(contest['name'])}</div>
{time_line}
{table}
<div class="cover-section">注意事项（请仔细阅读）</div>
<ol class="cover-notes">
{notes_html}
</ol>
"""
    return body


def build_combined_html(contest, problems, cover_html, sections_html):
    """合集 HTML：封面 + 各题片段，页码连续。"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{escape(contest['name'])}</title>
{_base_style(with_header=False)}
</head>
<body>
{cover_html}
{sections_html}
</body>
</html>
"""
