"""洛谷题面抓取模块：使用 Playwright 无头浏览器访问洛谷并提取题目数据。

提取的内容包括：题号、题名、时间/内存限制、各节题面 HTML（KaTeX 已渲染）、
输入输出样例，以及页面上 KaTeX 样式规则（含字体 @font-face）。

附件下载需要登录态：在项目根配置 .luogu_cookies.json（__client_id、_uid），
文件不入库（gitignore）；题面/样例抓取不需要登录。
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_URL = "https://www.luogu.com.cn/problem/"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)

# 在页面上下文中执行的提取脚本（独立文件，便于维护）
EXTRACT_JS = (Path(__file__).resolve().parent / "assets" / "extract.js").read_text(
    encoding="utf-8")


def _load_cookies():
    """读取 .luogu_cookies.json（附件下载登录态）；无配置返回 []。"""
    path = Path(__file__).resolve().parent / ".luogu_cookies.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [{"name": k, "value": str(v), "domain": ".luogu.com.cn", "path": "/"}
                for k, v in data.items() if v and not str(v).startswith("在此填入")]
    except Exception:
        return []


async def fetch_problem(browser, pid, work_dir):
    """抓取单个题目，返回 Problem 数据对象；失败抛 RuntimeError。"""
    from model import Problem

    ctx = await browser.new_context(locale="zh-CN", user_agent=UA)
    if cookies := _load_cookies():
        await ctx.add_cookies(cookies)
    page = await ctx.new_page()
    try:
        await page.goto(BASE_URL + pid, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_selector("h2.title", timeout=20000)
        except Exception:
            raise RuntimeError(f"{pid}: 页面未加载出题目（题目不存在或触发了风控）")
        await page.wait_for_timeout(1200)
        data = await page.evaluate(EXTRACT_JS)
        if not data.get("pid"):
            raise RuntimeError(f"{pid}: 未能提取到题目信息")
        raw = json.dumps(data, ensure_ascii=False, indent=1)
        (work_dir / f"raw_{pid}.json").write_text(raw, encoding="utf-8")
        md = data.get("md", {})
        # 附件下载：带登录态（downloadLink 为相对路径，拼站源）
        att_dir = work_dir / "attachments" / pid
        att_dir.mkdir(parents=True, exist_ok=True)
        attachments = []
        for att in md.get("attachments", []):
            fname = att.get("filename", "")
            if not fname:
                continue
            dest = att_dir / fname
            if not dest.exists():
                try:
                    resp = await ctx.request.get(
                        "https://www.luogu.com.cn" + att["downloadLink"])
                    if resp.status == 200:
                        dest.write_bytes(await resp.body())
                    else:
                        logger.warning(
                            "%s 附件 %s 下载失败（HTTP %s），附件需要登录："
                            "请在项目根配置 .luogu_cookies.json（__client_id、_uid）",
                            pid, fname, resp.status)
                except Exception:
                    pass
            if dest.exists():
                attachments.append({"filename": fname,
                                    "size": att.get("size", 0),
                                    "local": str(dest)})
        return Problem(
            pid=data.get("pid", pid),
            title=data.get("title", pid),
            time_limit=data.get("timeLimit", ""),
            memory_limit=data.get("memoryLimit", ""),
            sections=data.get("sections", {}),
            samples=data.get("samples", []),
            content=md.get("content", {}),
            limits=md.get("limits", {}),
            md_samples=md.get("samples", []),
            attachments=attachments,
        )
    finally:
        await ctx.close()
