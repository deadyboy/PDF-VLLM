from __future__ import annotations

from io import BytesIO

import fitz
import pytest
from PIL import Image

from icu_vllm.pdf_render_quality_probe import (
    audit_pdf_page,
    dpi_to_zoom,
    parse_rect_points,
    render_pdf_region,
    write_comparison_contact_sheet,
)


def _sample_png_bytes(color: tuple[int, int, int] = (230, 230, 230)) -> bytes:
    image = Image.new("RGB", (24, 16), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _write_sample_pdf(path, *, image_count: int = 1) -> None:
    doc = fitz.open()
    page = doc.new_page(width=240, height=180)
    page.insert_text((20, 30), "APTT 43.6 CPOT0", fontsize=10)
    png = _sample_png_bytes()
    for idx in range(image_count):
        x0 = 20 + idx * 35
        page.insert_image(fitz.Rect(x0, 60, x0 + 24, 76), stream=png)
    doc.save(path)
    doc.close()


def test_audit_pdf_page_reports_text_images_and_tiled_flag(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path, image_count=3)

    audit = audit_pdf_page(pdf_path, page_index=0, tiled_image_threshold=3)

    assert audit["page_index"] == 0
    assert audit["page_rect_points"] == [0.0, 0.0, 240.0, 180.0]
    assert audit["has_text_layer"] is True
    assert "CPOT0" in audit["text_preview"]
    assert audit["image_count"] == 3
    assert audit["possible_tiled_pdf"] is True
    assert {"xref", "width", "height", "bpc", "colorspace"}.issubset(audit["images"][0])


def test_render_pdf_region_writes_clip_png_and_manifest(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path)
    out_path = tmp_path / "page0_obs_clip_300dpi.png"

    manifest = render_pdf_region(
        pdf_path=pdf_path,
        page_index=0,
        clip_rect_points=[10, 10, 120, 90],
        dpi=300,
        output_path=out_path,
    )

    assert out_path.exists()
    assert (tmp_path / "page0_obs_clip_300dpi.manifest.json").exists()
    assert manifest["dpi"] == 300
    assert manifest["zoom"] == pytest.approx(dpi_to_zoom(300), rel=1e-3)
    assert manifest["clip_rect_points"] == [10.0, 10.0, 120.0, 90.0]
    assert manifest["used_clip"] is True
    assert manifest["output_size"][0] > 0
    assert manifest["estimated_rgb_mb"] > 0


def test_render_pdf_region_refuses_high_dpi_full_page(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path)

    with pytest.raises(ValueError, match="900/1200 DPI"):
        render_pdf_region(
            pdf_path=pdf_path,
            page_index=0,
            clip_rect_points=None,
            dpi=1200,
            output_path=tmp_path / "full_page_1200dpi.png",
        )


def test_contact_sheet_scales_variants_to_same_display_size(tmp_path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (80, 40), (255, 255, 255)).save(first)
    Image.new("RGB", (160, 80), (245, 245, 245)).save(second)

    sheet_path = write_comparison_contact_sheet(
        image_paths=[first, second],
        labels=["300 DPI", "600 DPI"],
        output_path=tmp_path / "comparison_contact_sheet.png",
        cell_width=120,
    )

    assert sheet_path.exists()
    sheet = Image.open(sheet_path)
    assert sheet.width == 240
    assert sheet.height > 40


def test_parse_rect_points_accepts_comma_separated_points():
    assert parse_rect_points("1, 2.5, 30, 40") == [1.0, 2.5, 30.0, 40.0]
