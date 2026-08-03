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
    assert fmt_time_range("9:00-13:00") == "09:00 $\\sim$ 13:00"


def test_fmt_time_range_full_width():
    assert fmt_time_range("8:30～12:00") == "08:30 $\\sim$ 12:00"


def test_fmt_time_range_no_range():
    assert fmt_time_range("9:00") == "9:00"


def test_dashfix_dates():
    assert dashfix("2026-08-03 模拟赛") == "2026.08.03 模拟赛"


def test_dashfix_keeps_other_hyphens():
    assert dashfix("NOIP-模拟赛 n-1") == "NOIP-模拟赛 n-1"


def test_display_wrap():
    assert "gather*" in _display_wrap("$$a\\\\b$$")
    assert "gather" not in _display_wrap("$$a$$")
