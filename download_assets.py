#!/usr/bin/env python3
"""下载渲染所需资源到 assets/（KaTeX 样式与字体、思源宋体）。

幂等：已存在的文件会跳过。首次使用前运行一次即可，之后离线可用。
"""

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KATEX_VERSION = "0.16.11"
MIRROR = f"https://registry.npmmirror.com/katex/{KATEX_VERSION}/files/dist"
SERIF_URLS = [
    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-Regular.otf",
    "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-Regular.otf",
]


def fetch(url, timeout=120, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=timeout).read()
    if binary:
        return data
    return data.decode("utf-8", "ignore")


def ensure_katex():
    css_dir = ROOT / "assets" / "katex"
    fonts_dir = css_dir / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    css_path = css_dir / "katex.min.css"
    if not css_path.exists():
        css_path.write_text(fetch(MIRROR + "/katex.min.css"), encoding="utf-8")
        print("katex.min.css 已下载")
    css = css_path.read_text(encoding="utf-8")
    refs = sorted(set(re.findall(r"url\(fonts/([^)]+)\)", css)))
    missing = [f for f in refs if not (fonts_dir / f).exists()]
    for i, name in enumerate(missing):
        (fonts_dir / name).write_bytes(fetch(MIRROR + "/fonts/" + name, binary=True))
        print(f"字体 {i + 1}/{len(missing)}: {name}")
    print(f"KaTeX 就绪（{len(refs)} 个字体文件）")


def ensure_serif():
    out = ROOT / "assets" / "fonts" / "NotoSerifCJKsc-Regular.otf"
    if out.exists() and out.stat().st_size > 1000:
        print("思源宋体已存在")
        return
    for url in SERIF_URLS:
        try:
            data = fetch(url, binary=True)
            if len(data) < 1000:
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            print(f"思源宋体已下载（{len(data) // 1024 // 1024} MB）")
            return
        except Exception as e:
            print(f"下载失败: {url} ({e})")
    sys.exit("错误：思源宋体下载失败，请手动放置到 assets/fonts/NotoSerifCJKsc-Regular.otf")


if __name__ == "__main__":
    ensure_katex()
    ensure_serif()
    print("全部就绪。")
