"""LaTeX 编译：xelatex -shell-escape 两遍编译，页数漂移时补第三遍。"""

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run_xelatex(tex_path, env, no_pdf=False):
    args = ["xelatex", "-shell-escape", "-interaction=nonstopmode",
            "-halt-on-error"]
    if no_pdf:
        args.insert(1, "-no-pdf")
    return subprocess.run(
        args + [tex_path.name],
        cwd=tex_path.parent, env=env,
        capture_output=True, text=True, timeout=600,
    )


def _aux_totpages(aux_path):
    """读 aux 的 TotPages label 值（上一遍编译写下的页数）；无则 None。"""
    if not aux_path.exists():
        return None
    m = re.search(r"\\newlabel\{TotPages\}\{\{(\d+)\}", 
                  aux_path.read_text(encoding="utf-8", errors="ignore"))
    return int(m.group(1)) if m else None


def _log_pages(log_path):
    """读 log 的最终页数；无则 None。"""
    if not log_path.exists():
        return None
    m = re.search(r"Output written on .* \((\d+) pages?\)",
                  log_path.read_text(encoding="utf-8", errors="ignore"))
    return int(m.group(1)) if m else None


def compile_latex(tex_path, venv_bin, progress_cb=None):
    """用 xelatex -shell-escape 编译两遍（必要时三遍）：

    1. -no-pdf（引擎级不写 PDF，但 aux/write 正常执行，TotPages 等
       label 完整写入——draftmode 做不到这点，会导致需三遍）
    2. 正式输出（解析引用收敛）
    3. 若第 2 遍页数 ≠ 第 1 遍（minted 第一遍是 <MINTED> 占位、
       第二遍才渲染完整内容，页数可能漂移），补第三遍正式输出——
       否则页脚的「共 N 页」（\pageref{TotPages} 读上一遍 aux）
       会滞后

    progress_cb(step)：可选回调，step=1（第一遍完成）、step=2
    （第二遍完成）、step=3（第三遍完成）后调用。
    返回 (True, PDF路径) 或 (False, 错误信息)。"""
    env = dict(os.environ)
    if venv_bin:
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    # 让 xelatex 能找到 assets/latex/statement.cls（末尾冒号保留默认路径）
    env["TEXINPUTS"] = str((ROOT / "assets" / "latex").resolve()) + os.pathsep + env.get("TEXINPUTS", "")
    aux = tex_path.with_suffix(".aux")
    log = tex_path.with_suffix(".log")
    # 第一遍：-no-pdf（不写 PDF，省时；aux 正常写入）
    _run_xelatex(tex_path, env, no_pdf=True)
    if progress_cb:
        progress_cb(1)
    # 记录第一遍页数（第二遍会覆盖 aux，必须此时读取）
    pages1 = _aux_totpages(aux)
    # 第二遍：正式输出 PDF（解析引用）
    _run_xelatex(tex_path, env)
    if progress_cb:
        progress_cb(2)
    # 第三遍：minted 占位→完整渲染导致页数漂移时，TotPages 会滞后
    pages2 = _log_pages(log)
    if pages2 is not None and pages1 is not None and pages2 != pages1:
        _run_xelatex(tex_path, env)
        if progress_cb:
            progress_cb(3)
    pdf = tex_path.with_suffix(".pdf")
    if pdf.exists():
        return True, pdf
    errs = [l for l in log.read_text(encoding="utf-8", errors="ignore").splitlines()
            if l.startswith("!")][:5]
    return False, "\n".join(errs) if errs else "PDF 未生成"
