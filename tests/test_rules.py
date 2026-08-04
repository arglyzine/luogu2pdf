"""rules.py（双后端共享语义规则）测试。"""

from rules import (HINT_HEADING_RE, SAMPLE_EXPLAIN_RE, DATARANGE_RE,
                   CARET, classify_hint, sample_explain_number)


def test_classify_hint_html():
    assert classify_hint("<p>对于 100% 的数据满足：</p>") == "数据范围"
    assert classify_hint("<p>本题开启捆绑测试</p>") == "提示"


def test_classify_hint_markdown():
    # LaTeX 端传入 markdown 源也应判断一致
    assert classify_hint("对于 100% 的数据，保证：") == "数据范围"
    assert classify_hint("注意常数因子") == "提示"


def test_classify_hint_keeps_together_with_latex():
    # 两端语义一致：LaTeX 原用「数据范围|测试点|对于 100%」判断
    for text in ["测试点编号如下", "对于 100% 的数据", "数据范围"]:
        assert classify_hint(text) == "数据范围"


def test_sample_explain_number():
    assert sample_explain_number("样例 1 解释") == "1"
    assert sample_explain_number("样例 $1$ 解释") == "1"
    assert sample_explain_number("样例 12 解释") == "12"
    assert sample_explain_number("数据范围") is None


def test_heading_re():
    assert HINT_HEADING_RE.match("### 样例解释")
    assert HINT_HEADING_RE.match("  #### 数据范围")
    assert not HINT_HEADING_RE.match("正文段落")
    assert not HINT_HEADING_RE.match("####### 太多级")


def test_caret_semantics():
    assert CARET == "^"


def test_datarange_re():
    assert DATARANGE_RE.search("对于 100% 的数据")
    assert DATARANGE_RE.search("测试点")
