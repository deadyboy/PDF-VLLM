from __future__ import annotations

from io import BytesIO

import fitz
from PIL import Image

from icu_vllm.observation_pdf_dpi_recognition_probe import (
    DPI_VARIANTS,
    build_pdf_dpi_row,
    load_case_rects,
    render_case_variants,
    select_cases,
    summarize_pdf_dpi_rows,
    write_pdf_dpi_report,
)


def _sample_png_bytes() -> bytes:
    image = Image.new("RGB", (48, 32), (245, 245, 245))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _write_sample_pdf(path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=240, height=180)
    page.insert_text((20, 40), "CPOT0 APTT 43.6", fontsize=10)
    page.insert_image(fitz.Rect(20, 70, 68, 102), stream=_sample_png_bytes())
    doc.save(path)
    doc.close()


def test_select_cases_filters_by_page_and_rects():
    cases = [
        {"page": "gold_smoke_001", "block_id": "block_01"},
        {"page": "gold_dev_m_002", "block_id": "block_00"},
    ]
    rects = {"gold_smoke_001/block_01": [10, 20, 30, 40]}

    selected = select_cases(cases, page_label="gold_smoke_001", case_rects=rects)

    assert selected == [{"page": "gold_smoke_001", "block_id": "block_01", "clip_rect_points": [10, 20, 30, 40]}]


def test_load_case_rects_supports_default_and_case_specific(tmp_path):
    path = tmp_path / "rects.json"
    path.write_text(
        '{"default": [1, 2, 3, 4], "cases": {"gold_smoke_001/block_01": [5, 6, 7, 8]}}',
        encoding="utf-8",
    )

    rects = load_case_rects(path)

    assert rects["default"] == [1.0, 2.0, 3.0, 4.0]
    assert rects["gold_smoke_001/block_01"] == [5.0, 6.0, 7.0, 8.0]


def test_render_case_variants_writes_manifests_and_downsamples(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path)
    audit = {"image_count": 3, "possible_tiled_pdf": False}
    case = {"page": "gold_smoke_001", "block_id": "block_01", "clip_rect_points": [10, 10, 120, 80]}

    payload = render_case_variants(
        pdf_path=pdf_path,
        page_index=0,
        case=case,
        output_dir=tmp_path,
        source_pdf_audit=audit,
    )

    assert set(payload["variants"]) == set(DPI_VARIANTS)
    size_300 = payload["variants"]["pdf_clip_300dpi"]["output_size_after_downsample"]
    assert payload["variants"]["pdf_clip_1200dpi"]["used_clip"] is True
    assert payload["variants"]["pdf_clip_1200dpi_down_to_300dpi"]["downsampled"] is True
    assert payload["variants"]["pdf_clip_1200dpi_down_to_300dpi"]["output_size_after_downsample"] == size_300
    for variant in DPI_VARIANTS:
        assert (tmp_path / payload["variants"][variant]["image_path"]).exists()
        assert (tmp_path / payload["variants"][variant]["manifest_path"]).exists()


def test_build_row_and_summary_use_observation_eval_kinds():
    row = build_pdf_dpi_row(
        page="gold_smoke_001",
        block_id="block_01",
        gold="CPOT0分",
        main_value=None,
        old_col_value="CPOT0分",
        variant_values={
            "pdf_clip_300dpi": "CPO10分",
            "pdf_clip_600dpi": "CPOT0分",
        },
    )

    assert row["variant_results"]["pdf_clip_600dpi"]["eval_kind"] == "exact_equal"
    assert row["variant_results"]["pdf_clip_300dpi"]["eval_kind"] == "char_level_mismatch"
    summary = summarize_pdf_dpi_rows([row])
    assert summary["source_counts"]["pdf_clip_600dpi"]["correct"] == 1
    assert summary["source_counts"]["pdf_clip_300dpi"]["char_level_mismatch"] == 1


def test_write_report_outputs_markdown_json_and_sidecars(tmp_path):
    sidecars = [{
        "page": "gold_smoke_001",
        "block_id": "block_01",
        "variant_results": {},
    }]
    row = build_pdf_dpi_row(
        page="gold_smoke_001",
        block_id="block_01",
        gold="CPOT0分",
        main_value=None,
        old_col_value="CPOT0分",
        variant_values={"pdf_clip_300dpi": "CPOT0分"},
    )
    summary = summarize_pdf_dpi_rows([row])

    write_pdf_dpi_report(tmp_path, rows=[row], summary=summary, sidecars=sidecars, metadata={"model_calls": 1})

    assert (tmp_path / "observation_pdf_dpi_probe_report.md").exists()
    assert (tmp_path / "observation_pdf_dpi_probe_summary.json").exists()
    assert (tmp_path / "sidecars" / "gold_smoke_001__block_01_pdf_dpi_probe.json").exists()
