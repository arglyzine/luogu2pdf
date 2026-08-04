"""LaTeX 编译：xelatex -shell-escape 两遍编译。"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def compile_latex(tex_path, venv_bin, progress_cb=None):
    """用 xelatex -shell-escape 编译两遍：

    1. -no-pdf（引擎级不写 PDF，但 aux/write 正常执行，TotPages 等
       label 完整写入——draftmode 做不到这点，会导致需三遍）
    2. 正式输出（解析引用收敛）

    progress_cb(step)：可选回调，step=1（第一遍完成）、step=2
    （第二遍完成）后调用。
    返回 (True, PDF路径) 或 (False, 错误信息)。"""
    env = dict(os.environ)
    if venv_bin:
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    # 让 xelatex 能找到 assets/latex/statement.cls（末尾冒号保留默认路径）
    env["TEXINPUTS"] = str((ROOT / "assets" / "latex").resolve()) + os.pathsep + env.get("TEXINPUTS", "")
    # 第一遍：-no-pdf（不写 PDF，省时；aux 正常写入）
    subprocess.run(
        ["xelatex", "-no-pdf", "-shell-escape", "-interaction=nonstopmode",
         "-halt-on-error", tex_path.name],
        cwd=tex_path.parent, env=env,
        capture_output=True, text=True, timeout=600,
    )
    if progress_cb:
        progress_cb(1)
    # 第二遍：正式输出 PDF（解析引用）
    r = subprocess.run(
        ["xelatex", "-shell-escape", "-interaction=nonstopmode",
         "-halt-on-error", tex_path.name],
        cwd=tex_path.parent, env=env,
        capture_output=True, text=True, timeout=600,
    )
    if progress_cb:
        progress_cb(2)
    pdf = tex_path.with_suffix(".pdf")
    if pdf.exists():
        return True, pdf
    log = (tex_path.with_suffix(".log")).read_text(encoding="utf-8", errors="ignore")
    errs = [l for l in log.splitlines() if l.startswith("!")][:5]
    return False, "\n".join(errs) if errs else "PDF 未生成"
