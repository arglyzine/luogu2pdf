"""基于真实抓取数据的集成测试：转换器对真实题面不崩溃且关键内容保留。

依赖 .work/raw_*.json（运行过 main.py 抓取后存在）；缺失时跳过。
"""

import json
import re
from pathlib import Path

import pytest

from latex import md_to_latex, _split_hint, _table_to_latex

WORK = Path(__file__).resolve().parent.parent / ".work"


def _raw_files():
    return sorted(WORK.glob("raw_P*.json")) if WORK.exists() else []


@pytest.mark.skipif(not _raw_files(), reason="需要先运行 main.py 抓取数据")
@pytest.mark.parametrize("raw", _raw_files(), ids=lambda p: p.stem)
def test_md_to_latex_on_real_problems(raw):
    data = json.loads(raw.read_text(encoding="utf-8"))
    md = data.get("md", {})
    content = md.get("content", {})
    for sec, text in content.items():
        if text.strip():
            out = md_to_latex(text, None)
            assert isinstance(out, str)
            assert ":::" not in out
            assert "::anti-ai" not in out
            # 中文字符不被转义破坏
            chinese = re.findall(r"[\u4e00-\u9fff]", text)
            if chinese:
                assert chinese[0] in out


@pytest.mark.skipif(not _raw_files(), reason="需要先运行 main.py 抓取数据")
def test_table_latex_on_real_hints():
    for raw in _raw_files():
        data = json.loads(raw.read_text(encoding="utf-8"))
        hint = data.get("md", {}).get("content", {}).get("hint", "")
        for line in hint.split("\n"):
            if line.strip().startswith("|"):
                out = _table_to_latex([line, "|-|", "|x|"])
                assert "tblr" in out
