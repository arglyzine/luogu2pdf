"""NOIP 官方风格题面 HTML 模板生成。

版式参考 CCF NOIP 2024 官方题面 PDF：
- 每页页眉：左侧比赛名，右侧「题名（英文名）」，下横线
- 标题居中加粗：「题名（英文名）」
- 节标题左对齐加粗：【题目描述】【输入格式】【输出格式】【样例 1 输入】...
- 正文宋体、首行缩进，样例代码框，页脚「第 X 页 共 Y 页」
- 封面页：比赛信息表格 + 注意事项
"""

import re
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from utils import fmt_date, fmt_time_range, fmt_time_limit, fmt_memory, dashfix

ROOT = Path(__file__).resolve().parent
KATEX_CSS = ROOT / "assets" / "katex" / "katex.min.css"
KATEX_FONTS = ROOT / "assets" / "katex" / "fonts"
SERIF_FONT = ROOT / "assets" / "fonts" / "NotoSerifCJKsc-Regular.otf"

_env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
BASE_CSS = _env.get_template("style.css.j2")

BASE_CSS_TEMPLATE = None  # 延迟加载

KATEX_ESCAPE = None


def _katex_css():
    """读取本地 KaTeX 样式，字体路径转 file:// 绝对路径。"""
    global KATEX_ESCAPE
    css = KATEX_CSS.read_text(encoding="utf-8")
    fonts_uri = KATEX_FONTS.resolve().as_uri()
    return css.replace("url(fonts/", f"url({fonts_uri}/")


def _base_style(with_header=True):
    css = BASE_CSS.render(serif_font=SERIF_FONT.resolve().as_uri())
    return "<style>" + css + _katex_css() + "</style>"


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
    """题目各节 HTML：节标题【】格式 + 内容原样保留（模板循环渲染）。"""
    parts = []
    sections = problem.sections
    samples = problem.samples

    # 主体节：背景/描述/输入/输出
    for name, title in SECTION_MAP:
        content = sections.get(name)
        if not content or name == "说明/提示":
            continue
        if title is None:
            title = hint_title(content)
        prefix = {"输入格式": "从标准输入中读入数据。",
                  "输出格式": "输出到标准输出中。"}.get(name)
        # prefix 段需在 .lfe-marked 内（正文缩进选择器）才能首行缩进
        body = f'<div class="lfe-marked"><p>{prefix}</p></div>' + content if prefix else content
        parts.append({
            "title": title,
            "content": body,
            "cls": "marked datarange" if title == "数据范围" else "marked",
        })

    # 样例输入/输出
    if samples:
        groups = {}
        for s in samples:
            groups.setdefault(s["n"], {})[s["kind"]] = s["text"]
        for n in sorted(groups):
            g = groups[n]
            if "输入" in g:
                parts.append({"title": f"样例 {n} 输入", "sample": _numbered_sample(g["输入"])})
            if "输出" in g:
                parts.append({"title": f"样例 {n} 输出", "sample": _numbered_sample(g["输出"])})

    # 说明/提示：按 ### 小标题拆分（样例解释在样例之后独立成节）
    hint_html = sections.get("说明/提示")
    if hint_html:
        for htitle, hbody in _split_hint_html(hint_html):
            if not hbody.strip():
                continue
            m = re.search(r"样例\s*(\d+)\s*解释", htitle)
            # hint 拆分出的片段无 .lfe-marked 包装，补一层以应用正文缩进等样式
            hbody = f'<div class="lfe-marked">{hbody}</div>'
            if "解释" in htitle and "样例" in htitle:
                n = m.group(1) if m else (1 if samples else 1)
                parts.append({"title": f"样例 {n} 解释", "content": hbody, "cls": "marked"})
            else:
                t = htitle or hint_title(hbody)
                parts.append({
                    "title": t,
                    "content": hbody,
                    "cls": "marked datarange" if t == "数据范围" else "marked",
                })

    return _env.get_template("sections.html.j2").render(sections=parts)


# ---------------- 页面组装 ----------------

def build_problem_html(problem, contest, index, total):
    """单题完整 HTML（页眉 fixed，每页重复）。"""
    title = problem.title
    en = problem.english_name
    title_html = f"{escape(title)}（{escape(en)}）" if en else escape(title)
    body = _sections_html(problem)
    return _env.get_template("problem.html.j2").render(
        doc_title=f"第{index}题 {escape(title)}",
        style=_base_style(with_header=True),
        contest_name=escape(contest.name),
        title_html=title_html,
        body=body,
    )


def build_problem_section(problem, contest):
    """合集中的题面片段（流式页眉，仅本题首页显示）。"""
    title = problem.title
    en = problem.english_name
    title_html = f"{escape(title)}（{escape(en)}）" if en else escape(title)
    return ('<div style="page-break-before: always;"></div>\n'
            f'<h1 class="title">{title_html}</h1>\n') + _sections_html(problem)
# (build_problem_section 保留 Python 拼接：页眉/标题组合，模板化收益低)


def build_cover_html(contest, problems):
    """封面 HTML：比赛信息表格 + 提交文件名/编译选项 + 注意事项（对齐 LaTeX 版）。

    数据准备与模板分离：模板用 Jinja2 循环渲染表格，Python 只组装数据。
    """
    n = len(problems)
    # 时限取各测试点最大值（与 LaTeX 封面一致）
    limits = []
    for p in problems:
        t = p.limits.get("time", [0])
        limits.append(f"{max(t) / 1000:.1f} 秒" if t else "")
    info_rows = [
        ("题目名称", [p.title for p in problems]),
        ("题目类型", [p.type for p in problems]),
        ("目录", [p.exec_name for p in problems]),
        ("可执行文件名", [p.exec_name for p in problems]),
        ("输入文件名", ["标准输入"] * n),
        ("输出文件名", ["标准输出"] * n),
        ("每个测试点时限", limits),
        ("内存限制", [fmt_memory(p.memory_limit) for p in problems]),
        ("测试点数目", [str(len(p.limits.get("time", []))) for p in problems]),
    ]
    src_files = [f"{p.exec_name}.cpp" for p in problems]

    time_line = ""
    if contest.date or contest.time:
        parts = []
        if contest.date:
            parts.append(fmt_date(contest.date))
        if contest.time:
            parts.append(f"{fmt_time_range(contest.time)}（{contest.duration}）")
        time_line = f'<p class="cover-time">时间：{"　".join(parts)}</p>'

    notes = contest.notes or [
        "文件名（程序名和输入输出文件名）必须使用英文小写。",
        "main 函数的返回值类型必须是 int，程序正常结束时的返回值必须是 0。",
        "提交的程序代码文件的放置位置请参考各省的具体要求。",
        "因违反以上三点而出现的错误或问题，申诉时一律不予受理。",
        "若无特殊说明，结果的比较方式为全文比较（过滤行末空格及文本回车）。",
        "选手提交的程序源文件必须不大于 100KB。",
        "程序可使用的栈空间内存限制与题目的内存限制一致。",
    ]

    return _env.get_template("cover.html.j2").render(
        contest_name=dashfix(contest.name),
        time_line=time_line,
        info_rows=info_rows,
        src_files=src_files,
        compile_opts="-O2 -std=c++14 -static",
        notes=notes,
        n=n,
    )


def build_combined_html(contest, problems, cover_html, sections_html):
    """合集 HTML：封面 + 各题片段，页码连续。"""
    return _env.get_template("combined.html.j2").render(
        doc_title=escape(contest.name),
        style=_base_style(with_header=False),
        cover_html=cover_html,
        sections_html=sections_html,
    )
