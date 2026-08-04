"""latex.py 转换器纯函数测试：锁定 Markdown→LaTeX 行为。"""

import pytest

from markdown_latex import (md_to_latex, _table_to_latex,
                           _escape_special, _display_wrap)
from latex_doc import _split_hint
from utils import dashfix, fmt_time_range


# ---------------- 防作弊与警告块 ----------------

def test_anti_ai_removed():
    out = md_to_latex("::anti-ai[**不要看**] 正文内容", None)
    assert "不要看" not in out
    assert "正文内容" in out


def test_warning_block_removed_markers():
    out = md_to_latex(":::warning{open}\n**本题输入输出量较大**。\n:::\n\n正文", None)
    assert ":::" not in out
    assert "输入输出量较大" in out


def test_warning_bold_becomes_stress():
    out = md_to_latex(":::warning{open}\n**强调文字**。\n:::", None)
    assert "\\stress{" in out


# ---------------- 公式处理 ----------------

def test_inline_math_preserved():
    out = md_to_latex("给定 $n$ 个节点（$1\\le n \\le 10^5$）", None)
    assert "\\le n" in out
    assert "textbackslash" not in out


def test_display_math_gather_wrap():
    out = md_to_latex("$$\na=b\\\\\nc=d\n$$", None)
    assert "gather*" in out


def test_display_math_single_line_no_gather():
    out = md_to_latex("$$x=1$$", None)
    assert "gather" not in out


def test_unclosed_math_fixed():
    # _fix_math 会把奇数个 $ 补全为公式（洛谷表头常见写法）
    out = md_to_latex("表头 $n", None)
    assert "$n$" in out


# ---------------- 特殊字符转义 ----------------

def test_escape_special():
    assert _escape_special("a_b%c") == r"a\_b\%c"
    assert _escape_special("a\\b") == r"a\textbackslash{}b"


def test_math_not_escaped():
    out = md_to_latex("$a_i$ 与 $x^2$", None)
    assert "$a_i$" in out


# ---------------- 表格 ----------------

def test_table_basic_three_line():
    rows = ["| a | b |", "|:-:|:-:|", "| 1 | 2 |"]
    out = _table_to_latex(rows)
    assert "toprule" not in out  # 用 Xhline 风格
    assert "Xhline" not in out  # tabularray 无 Xhline
    assert "tblr" in out


def test_table_column_count():
    rows = ["| a | b | c |", "| 1 | 2 | 3 |", "| 4 | 5 | 6 |"]
    out = _table_to_latex(rows)
    assert "colspec = {c|c|c}" in out


def test_table_caret_merge():
    rows = [
        "| 子任务 | N | 性质 |",
        "|:-:|:-:|:-:|",
        "| 1 | $\\le 9$ | 无 |",
        "| 2 | ^ | 无 |",
        "| 3 | $\\le 10$ | A |",
    ]
    out = _table_to_latex(rows)
    assert "SetCell[r=2]" in out
    assert "^" not in out.replace("textasciicircum", "")


def test_table_same_value_without_caret_not_merged():
    # 性质列两行都是「无」但没有 ^ 标记 → 不合并；N 列 ^ 仍合并
    rows = [
        "| 子任务 | N | 性质 |",
        "| 1 | $\\le 9$ | 无 |",
        "| 2 | ^ | 无 |",
    ]
    out = _table_to_latex(rows)
    # 只有 1 处 SetCell（N 列的 ^ 合并）
    assert out.count("SetCell") == 1
    # 性质列两行都保留值
    assert out.count("无") == 2


def test_table_caret_chain_merge():
    # 连续多个 ^ 与来源行合并为 r=3
    rows = [
        "| a | b |",
        "| x | y |",
        "| ^ | y |",
        "| ^ | z |",
    ]
    out = _table_to_latex(rows)
    assert "SetCell[r=3]" in out


def test_table_merge_skip_covered():
    # 无 ^ 的连续相同值不合并
    rows = [
        "| a | b |",
        "| x | y |",
        "| x | z |",
        "| w | z |",
    ]
    out = _table_to_latex(rows)
    assert "SetCell" not in out


# ---------------- hint 拆分 ----------------

def test_split_hint_sections():
    hint = "### 样例解释\n解释文本\n\n### 数据范围\n范围文本"
    parts = _split_hint(hint)
    titles = [t for t, _ in parts]
    assert titles == ["样例解释", "数据范围"]


def test_split_hint_no_header_content():
    hint = "前置内容\n\n### 数据范围\n范围文本"
    parts = _split_hint(hint)
    assert parts[0][0] == ""
    assert "前置内容" in parts[0][1]


def test_split_hint_empty_body_skipped_later():
    hint = "### 样例解释\n\n### 数据范围\n范围"
    parts = _split_hint(hint)
    assert len(parts) == 2


# ---------------- 格式化工具 ----------------

def test_fmt_time_range_pad_and_tilde():
    assert fmt_time_range("9:00-13:00") == "09:00 ～ 13:00"


def test_fmt_time_range_full_width():
    assert fmt_time_range("8:30～12:00") == "08:30 ～ 12:00"


def test_fmt_time_range_no_range():
    assert fmt_time_range("9:00") == "9:00"


def test_dashfix_dates():
    assert dashfix("2026-08-03 模拟赛") == "2026.08.03 模拟赛"


def test_dashfix_keeps_other_hyphens():
    assert dashfix("NOIP-模拟赛 n-1") == "NOIP-模拟赛 n-1"


def test_display_wrap():
    assert "gather*" in _display_wrap("$$a\\\\b$$")
    assert "gather" not in _display_wrap("$$a$$")


# ---------------- 嵌套列表 ----------------

def test_nested_itemize():
    md = """- 外层项
  - 子项一
  - 子项二
- 第二外层项"""
    out = md_to_latex(md, None)
    assert out.count("begin{itemize}") == 2
    assert out.count("end{itemize}") == 2


def test_nested_item_inline_rendered():
    # 嵌套子项内的粗体/公式必须转换（占位符恢复机制）
    md = """- 外层
  - 新边**可以**共端点。公式 $x^2$
  - 子项二"""
    out = md_to_latex(md, None)
    assert "\\stress{可以}" in out
    assert "$x^2$" in out
    assert "**" not in out


def test_nested_three_levels():
    md = """- 一级
  - 二级
    - 三级"""
    out = md_to_latex(md, None)
    assert out.count("begin{itemize}") == 3


def test_mixed_list_types_split():
    # - 与 1. 混用时按类型拆开
    md = """- 圆点项
1. 数字项
- 另一个圆点项"""
    out = md_to_latex(md, None)
    assert "begin{itemize}" in out and "begin{enumerate}" in out


def test_enumerate_continuation_formula():
    # P17170 样例解释：编号项后接缩进公式块（续行）
    md = """1. 对第 $1$ 行异或 $3$，得到

   $$
   n=3,\\quad m=3\\\\
   A=\\begin{pmatrix}1\\2\\3\\end{pmatrix}
   $$

2. 第 2 项"""
    out = md_to_latex(md, None)
    assert out.count("begin{enumerate}") == 1
    assert "gather*" in out
    assert "pmatrix" in out


def test_nested_in_enumerate():
    md = """1. 外层编号项
   - 子圆点项
2. 第二编号项"""
    out = md_to_latex(md, None)
    assert "begin{enumerate}" in out and "begin{itemize}" in out


# ---------------- 分割线与引用 ----------------

def test_hr_rule():
    out = md_to_latex("上文\n\n---\n\n下文", None)
    assert "\\rule{\\textwidth}{0.4pt}" in out
    assert "---" not in out


def test_quote_tcolorbox():
    out = md_to_latex("> 她说：**毕业晚会**后。\n> 少年傍着少女。\n\n正文", None)
    assert "\\begin{callout}" in out
    assert "\\stress{毕业晚会}" in out


def test_quote_empty_lines_merged():
    # 引用内 > 空行是段分隔，不是新块；> 空行不产生字面输出
    md = "> 第一段\n>\n> 第二段\n>\n> 第三段"
    out = md_to_latex(md, None)
    assert out.count("\\begin{callout}") == 1
    assert not any(l.strip() == ">" for l in out.split("\n"))


def test_quote_not_swallowed_by_para():
    # 段落中途出现引用行不应被并入段落
    out = md_to_latex("段落前\n> 引用行\n段落后", None)
    assert "\\begin{callout}" in out


def test_hr_not_swallowed_by_para():
    out = md_to_latex("段落前\n---\n段落后", None)
    assert "\\rule" in out


# ---------------- #### 级标题与公式标题 ----------------

def test_split_hint_four_hash():
    hint = "#### 样例 1 解释\n解释\n\n#### 数据范围\n范围"
    parts = _split_hint(hint)
    assert parts[0][0] == "样例 1 解释"
    assert parts[1][0] == "数据范围"


def test_split_hint_formula_title():
    # 标题含 $1$（公式标记）
    hint = "#### 样例 $1$ 解释\n解释内容"
    parts = _split_hint(hint)
    assert parts[0][0] == "样例 $1$ 解释"


# ---------------- 编译脚本 ----------------

def test_build_build_script_parallel(tmp_path):
    from latex_doc import build_build_script
    script = build_build_script(tmp_path)
    assert "xargs -P" in script          # 并行
    assert "-draftmode" in script        # 第一遍不写 PDF
    assert "venv" in script
