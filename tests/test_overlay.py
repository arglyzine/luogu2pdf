"""overlay.py（合集页眉/页码叠加）测试。"""

from io import BytesIO

import fitz
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from overlay import _draw_mixed, _header_packet, _page_number_packet, apply_overlay


def _make_pdf(pages):
    """用 reportlab 生成 pages 页的测试 PDF（每页一句文本）。"""
    buf = BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.setFont("Helvetica", 12)
        c.drawString(100, 500, f"content {i}")
        c.showPage()
    c.save()
    buf.seek(0)
    return buf


def test_draw_mixed_segments():
    c = canvas.Canvas(BytesIO())
    _draw_mixed(c, 0, 0, "第 2 页 共 15 页", 9)
    assert c._fontname in ("Helvetica", "CJKFallback")


def test_header_packet_has_text():
    packet = _header_packet("2026.08.03 模拟赛", "过去", 595.28, 841.89)
    doc = fitz.open(stream=packet.getvalue(), filetype="pdf")
    t = doc[0].get_text().replace(" ", "").replace("\n", "")
    assert "2026.08.03" in t and "模拟赛" in t and "过去" in t


def test_page_number_packet_text():
    packet = _page_number_packet(3, 15, 595.28, 841.89)
    doc = fitz.open(stream=packet.getvalue(), filetype="pdf")
    t = doc[0].get_text().replace(" ", "").replace("\n", "")
    assert "第3页" in t and "共15页" in t


def test_apply_overlay_cover_skipped(tmp_path):
    """第 1 页（封面）无页眉无页码；后续页有页眉和全局页码。"""
    src = _make_pdf(4)
    out = tmp_path / "overlay.pdf"
    apply_overlay(src, out, "2026.08.03 模拟赛",
                  [(1, 2, "过去"), (3, 3, "未来")], 4)
    doc = fitz.open(out)
    assert len(doc) == 4
    t0 = doc[0].get_text()
    assert "模拟赛" not in t0 and "页" not in t0  # 封面干净
    t1 = doc[1].get_text().replace(" ", "").replace("\n", "")
    assert "模拟赛" in t1 and "过去" in t1
    assert "第2页" in t1 and "共4页" in t1
    t3 = doc[3].get_text().replace(" ", "").replace("\n", "")
    assert "未来" in t3  # 第 4 页属于未来段
