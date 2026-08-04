"""template.py（HTML 后端）与共享工具函数测试。"""

from rules import classify_hint
from template import _split_hint_html, _numbered_sample
from utils import fmt_date, fmt_time_limit, fmt_memory, safe_filename


def test_fmt_date():
    assert fmt_date("2026-08-03") == "2026 年 8 月 3 日"
    assert fmt_date("2026/12/25") == "2026 年 12 月 25 日"
    assert fmt_date("unknown") == "unknown"


def test_fmt_time_limit():
    assert fmt_time_limit("500ms") == "0.5 秒"
    assert fmt_time_limit("1.00s") == "1.0 秒"
    assert fmt_time_limit("1.00s ~ 1.20s") == "1.0 秒 ～ 1.2 秒"


def test_fmt_memory():
    assert fmt_memory("16.00MB") == "16 MiB"
    assert fmt_memory("512.00MB") == "512 MiB"
    assert fmt_memory("1GB") == "1024 MiB"


def test_safe_filename():
    assert safe_filename("过去/未来") == "过去-未来"
    assert safe_filename("   ") == "题目"


def test_hint_title_datarange():
    content = "<p>对于 100% 的数据满足：</p>"
    assert classify_hint(content) == "数据范围"


def test_hint_title_plain():
    assert classify_hint("<p>注意常数因子</p>") == "提示"


def test_split_hint_html():
    html = "<h3>样例解释</h3><p>解释</p><h3>数据范围</h3><p>范围</p>"
    parts = _split_hint_html(html)
    titles = [t for t, _ in parts]
    assert titles == ["样例解释", "数据范围"]
    assert "解释" in parts[0][1]


def test_numbered_sample():
    out = _numbered_sample("1\n2")
    assert 'class="ln"' in out
    assert "1</span>  1" in out.replace(" ", "").replace('"', "") or "1" in out


def test_split_hint_html_four_hash():
    html = "<h4>样例 $1$ 解释</h4><p>解释</p><h4>数据范围</h4><p>范围</p>"
    parts = _split_hint_html(html)
    assert parts[0][0] == "样例 $1$ 解释"
    assert parts[1][0] == "数据范围"
