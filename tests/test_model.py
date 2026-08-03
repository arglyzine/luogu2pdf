"""model.py（Problem/Contest 数据模型）测试。"""

from model import Contest, Problem


def test_problem_defaults():
    p = Problem(pid="P17169", title="过去")
    assert p.english == ""
    assert p.type == "传统型"
    assert p.index == 0
    assert p.sections == {}
    assert p.limits == {}


def test_problem_english_name():
    p = Problem(pid="P17169", title="过去", english="past")
    assert p.english_name == "past"
    assert p.exec_name == "past"


def test_problem_exec_name_fallback():
    p = Problem(pid="P17169", title="过去", index=3)
    assert p.english_name == ""
    assert p.exec_name == "t3"


def test_contest_defaults():
    c = Contest()
    assert c.name == "模拟赛"
    assert c.notes == []


def test_contest_fields():
    c = Contest(name="测试赛", date="2026-08-03", time="9:00-13:00",
                duration="4 小时", notes=["注意一"])
    assert c.name == "测试赛"
    assert c.notes == ["注意一"]
