"""样例数据导出测试。"""

from main import export_samples
from model import Problem
from pathlib import Path


def _problem(pid, title, index, samples):
    return Problem(pid=pid, title=title, index=index,
                   md_samples=samples)


def test_export_samples(tmp_path):
    datas = [
        _problem("P1", "题一", 1, [["1 2\n", "3\n"], ["4\n", "5\n"]]),
        _problem("P2", "题二", 2, [["0\n", "1\n"]]),
        _problem("P3", "题三", 3, []),  # 无样例
    ]
    n = export_samples(datas, tmp_path)
    assert n == 3
    d1 = tmp_path / "data" / "t1"
    assert (d1 / "1.in").read_text() == "1 2\n"
    assert (d1 / "1.out").read_text() == "3\n"
    assert (d1 / "2.in").read_text() == "4\n"
    d2 = tmp_path / "data" / "t2"
    assert (d2 / "1.out").read_text() == "1\n"
    assert not (tmp_path / "data" / "t3").exists()


def test_export_samples_newline_appended(tmp_path):
    # 洛谷样例无结尾换行，导出时应补齐（数据文件惯例）
    d = _problem("P1", "题一", 1, [["2", "2"]])
    export_samples([d], tmp_path)
    assert (tmp_path / "data" / "t1" / "1.in").read_text() == "2\n"
    assert (tmp_path / "data" / "t1" / "1.out").read_text() == "2\n"


def test_export_samples_english_name(tmp_path):
    d = Problem(pid="P1", title="题一", english="past", index=1,
                md_samples=[["a\n", "b\n"]])
    export_samples([d], tmp_path)
    assert (tmp_path / "data" / "past" / "1.in").exists()


def test_export_samples_missing_output(tmp_path):
    # 只有输入没有输出的样例：只写 .in
    d = Problem(pid="P1", title="题一", index=1, md_samples=[["x\n"]])
    export_samples([d], tmp_path)
    assert (tmp_path / "data" / "t1" / "1.in").exists()
    assert not (tmp_path / "data" / "t1" / "1.out").exists()
