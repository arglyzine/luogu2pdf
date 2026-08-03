"""LaTeX 编译：xelatex -shell-escape 两遍编译。"""

import os
import subprocess
from pathlib import Path

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def compile_latex(tex_path, venv_bin):
    """用 xelatex -shell-escape 编译（两遍，处理 LastPage 引用）。
    返回 (True, PDF路径) 或 (False, 错误信息)。"""
    env = dict(os.environ)
    if venv_bin:
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    # 让 xelatex 能找到 assets/latex/statement.cls（末尾冒号保留默认路径）
    env["TEXINPUTS"] = str((ROOT / "assets" / "latex").resolve()) + os.pathsep + env.get("TEXINPUTS", "")
    for _ in range(2):
        r = subprocess.run(
            ["xelatex", "-shell-escape", "-interaction=nonstopmode",
             "-halt-on-error", tex_path.name],
            cwd=tex_path.parent, env=env,
            capture_output=True, text=True, timeout=600,
        )
    pdf = tex_path.with_suffix(".pdf")
    if pdf.exists():
        return True, pdf
    log = (tex_path.with_suffix(".log")).read_text(encoding="utf-8", errors="ignore")
    errs = [l for l in log.splitlines() if l.startswith("!")][:5]
    return False, "\n".join(errs) if errs else "PDF 未生成"
