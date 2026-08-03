"""合集 PDF 后处理：按题目分段叠加页眉（左侧比赛名、右侧题名）与全局页码。

HTML 单文档无法实现「每页页眉右侧显示当前题名」（headerTemplate/fixed 均
按整份文档重复），故合集生成时不带页眉，生成后用 reportlab 按段叠加：
- 第 1 页封面：无页眉、无页码（与官方一致）
- 每题正文页：页眉（比赛名 | 题名）+ 页脚「第 N 页 共 M 页」
"""

import re
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from utils import dashfix

PAGE_W = 595.28  # A4 宽 (pt)
PAGE_H = 841.89  # A4 高 (pt)
MARGIN = 27 * 72 / 25.4  # 27mm ≈ 76.5pt
HEADER_Y = PAGE_H - 25 * 72 / 25.4  # 顶部 25mm 处
FOOTER_Y = 20 * 72 / 25.4 - 12  # 底部 20mm 区域内


def _font():
    """注册中文字体（TrueType，reportlab 不支持 OTF PostScript outlines）。"""
    name = "CJKFallback"
    if name not in pdfmetrics.getRegisteredFontNames():
        candidates = [
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
        ]
        for path in candidates:
            if __import__("os").path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return name
        raise RuntimeError("未找到 TrueType 中文字体（DroidSansFallback）")
    return name


def _draw_mixed(c, x, y, text, size):
    """混合绘制：ASCII 用 Helvetica，CJK 用中文字体（CJK 字体无拉丁字符）。"""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    for seg in re.findall(r"[\x00-\x7f]+|[^\x00-\x7f]+", text):
        font = "Helvetica" if seg.isascii() else _font()
        c.setFont(font, size)
        c.drawString(x, y, seg)
        x += stringWidth(seg, font, size)


def _header_packet(contest_name, title, page_w, page_h):
    """生成一页的页眉+页码 overlay。"""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))
    c.setFillColorRGB(0, 0, 0)
    _draw_mixed(c, MARGIN, HEADER_Y, dashfix(contest_name), 10)
    if title:
        # 题名右对齐：先量总宽（按混合字体分段）再左移
        width = sum(stringWidth(seg, "Helvetica" if seg.isascii() else _font(), 10)
                    for seg in re.findall(r"[\x00-\x7f]+|[^\x00-\x7f]+", title))
        _draw_mixed(c, page_w - MARGIN - width, HEADER_Y, title, 10)
    c.setLineWidth(0.8)
    c.line(MARGIN, HEADER_Y - 5, page_w - MARGIN, HEADER_Y - 5)
    c.save()
    return BytesIO(packet.getvalue())


def _page_number_packet(page_no, total, page_w, page_h):
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))
    c.setFillColorRGB(0, 0, 0)
    _draw_mixed(c, page_w / 2, FOOTER_Y, f"第 {page_no} 页　共 {total} 页", 9)
    c.save()
    return BytesIO(packet.getvalue())


def apply_overlay(pdf_in, pdf_out, contest_name, segments, total_pages):
    """segments: [(起始页(0-based), 结束页(0-based), 题名)]，封面段题名为 None。"""
    reader = PdfReader(str(pdf_in))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        w, h = page.mediabox.width, page.mediabox.height
        if i > 0:
            title = next((t for s, e, t in segments if s <= i <= e and t), "")
            header = _header_packet(contest_name, title, w, h)
            page.merge_page(PdfReader(header).pages[0])
            footer = _page_number_packet(i + 1, total_pages, w, h)
            page.merge_page(PdfReader(footer).pages[0])
        writer.add_page(page)
    with open(pdf_out, "wb") as f:
        writer.write(f)
