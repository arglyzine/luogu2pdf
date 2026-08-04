"""compile.py 测试（subprocess 打桩，不依赖 xelatex）。"""

import subprocess
from pathlib import Path

from compile import compile_latex


def test_compile_latex_progress_cb(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        # 模拟 xelatex：第一遍（draftmode）不产 PDF，第二遍产出
        if "-draftmode" not in args:
            (tmp_path / "main.pdf").write_bytes(b"%PDF-1.4")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("compile.subprocess.run", fake_run)
    tex = tmp_path / "main.tex"
    tex.write_text("% dummy", encoding="utf-8")
    ok, pdf = compile_latex(tex, None, progress_cb=calls.append)
    assert ok and pdf.name == "main.pdf"
    assert calls == [1, 2]  # draftmode 后、正式输出后各一次


def test_compile_latex_failure(monkeypatch, tmp_path):
    def fake_run(args, **kwargs):
        if "-draftmode" not in args:
            # 写一个带错误的 log，不产 PDF
            (tmp_path / "main.log").write_text(
                "! Undefined control sequence.\nl.6 \\bad\n", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("compile.subprocess.run", fake_run)
    tex = tmp_path / "main.tex"
    tex.write_text("% dummy", encoding="utf-8")
    ok, err = compile_latex(tex, None)
    assert not ok
    assert "Undefined control sequence" in err
