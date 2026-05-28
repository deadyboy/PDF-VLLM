from __future__ import annotations

import json

import cv2
import numpy as np

from icu_vllm.observation_header_row_probe import (
    build_header_row_probe_row,
    combine_ocr_items_text,
    crop_header_row_images,
    filter_ocr_items_below_header,
    normalize_paddle_ocr_items,
    parse_row_response,
    summarize_header_row_probe_rows,
)


def _sample_observation_col() -> np.ndarray:
    image = np.full((220, 260, 3), 255, dtype=np.uint8)
    for y in [10, 90, 130, 170, 210]:
        cv2.line(image, (5, y), (255, y), (0, 0, 0), 2)
    cv2.line(image, (5, 10), (5, 210), (0, 0, 0), 2)
    cv2.line(image, (255, 10), (255, 210), (0, 0, 0), 2)
    cv2.putText(image, "OBS", (90, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(image, "CPOT0", (16, 117), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(image, "APTT44.8", (16, 157), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    return image


def test_crop_header_row_images_repeats_header_and_skips_empty_rows(tmp_path):
    image_path = tmp_path / "block_00_col_observation.png"
    cv2.imwrite(str(image_path), _sample_observation_col())

    manifest = crop_header_row_images(
        image_path=image_path,
        output_dir=tmp_path,
        page="gold_smoke_001",
        block_id="block_00",
    )

    assert manifest["header_bottom_y"] == 90
    assert manifest["row_count"] == 2
    assert [row["source_y1"] for row in manifest["rows"]] == [90, 130]
    for row in manifest["rows"]:
        assert row["data_start_y_in_image"] > row["header_height"]
        row_image = tmp_path / row["image_path"]
        assert row_image.exists()
        cropped = cv2.imread(str(row_image))
        assert cropped.shape[0] > (row["source_y2"] - row["source_y1"])


def test_parse_row_response_accepts_row_text_and_review_flags():
    parsed = parse_row_response('{"row_text": "CPOT0分", "needs_review": false, "reason": ""}')

    assert parsed["row_text"] == "CPOT0分"
    assert parsed["needs_review"] is False
    assert parsed["reason"] == ""


def test_ocr_items_filter_out_header_and_join_data_text():
    paddle_result = [[
        [[[10, 20], [80, 20], [80, 35], [10, 35]], ("病情观察及处理", 0.99)],
        [[[10, 100], [55, 100], [55, 115], [10, 115]], ("CPOT", 0.98)],
        [[[60, 100], [72, 100], [72, 115], [60, 115]], ("0分", 0.97)],
    ]]

    items = normalize_paddle_ocr_items(paddle_result)
    data_items = filter_ocr_items_below_header(items, data_start_y=80)

    assert [item["text"] for item in data_items] == ["CPOT", "0分"]
    assert combine_ocr_items_text(data_items) == "CPOT0分"


def test_build_row_and_summary_compare_ocr_and_qwen():
    row = build_header_row_probe_row(
        page="gold_smoke_001",
        block_id="block_01",
        gold="CPOT0分",
        old_col_value="CPOT0分",
        qwen_value="CPOT0分",
        ocr_value="CPOTO分",
    )

    assert row["qwen_kind"] == "exact_equal"
    assert row["ocr_kind"] == "char_level_mismatch"
    summary = summarize_header_row_probe_rows([row])
    assert summary["source_counts"]["qwen_header_row"]["correct"] == 1
    assert summary["source_counts"]["ocr_header_row"]["char_level_mismatch"] == 1


def test_summary_json_serializable(tmp_path):
    row = build_header_row_probe_row(
        page="p",
        block_id="block_00",
        gold="A",
        old_col_value="A",
        qwen_value=None,
        ocr_value="A",
    )
    summary = summarize_header_row_probe_rows([row])

    payload = {"summary": summary, "rows": [row]}
    (tmp_path / "summary.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["summary"]["case_count"] == 1
