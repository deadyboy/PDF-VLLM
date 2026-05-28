from __future__ import annotations

import json

import cv2
import numpy as np

from icu_vllm.observation_recognition_bottleneck_probe import (
    build_ocr_record,
    build_rec_only_skip_record,
    build_vlm_record,
    create_normalized_canvas_variants,
    draw_detection_overlay,
    snapshot_file_hash,
)


def _row_image() -> np.ndarray:
    image = np.full((34, 240, 3), 255, dtype=np.uint8)
    cv2.putText(image, "CPOT0", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 0), 1, cv2.LINE_AA)
    return image


def test_canvas_h48_h64_h96_are_nonempty_and_preserve_original(tmp_path):
    source = tmp_path / "row_only.png"
    cv2.imwrite(str(source), _row_image())
    before = source.read_bytes()

    variants = create_normalized_canvas_variants(
        row_only_image_path=source,
        output_dir=tmp_path,
        page="gold_smoke_001",
        block_id="block_01",
        row_id="00",
        target_text_heights=(48, 64, 96),
    )

    assert source.read_bytes() == before
    assert set(variants) == {"row_only_canvas_h48", "row_only_canvas_h64", "row_only_canvas_h96"}
    previous_height = 0
    for name in ("row_only_canvas_h48", "row_only_canvas_h64", "row_only_canvas_h96"):
        canvas = cv2.imread(str(tmp_path / variants[name]["image_path"]))
        assert canvas is not None
        assert canvas.size > 0
        assert canvas.shape[0] > previous_height
        assert canvas.shape[1] >= 240
        assert variants[name]["estimated_text_height_px"] > 0
        previous_height = canvas.shape[0]


def test_detection_overlay_accepts_empty_boxes(tmp_path):
    image_path = tmp_path / "row.png"
    overlay_path = tmp_path / "overlay.png"
    cv2.imwrite(str(image_path), _row_image())

    draw_detection_overlay(image_path=image_path, boxes=[], output_path=overlay_path)

    assert overlay_path.exists()
    assert cv2.imread(str(overlay_path)) is not None


def test_rec_only_skip_record_is_explicit():
    record = build_rec_only_skip_record(
        page="p",
        block_id="block_00",
        row_id="00",
        image_variant="row_only_canvas_h64",
        reason="PaddleOCR det=False rec=True unavailable",
    )

    assert record["ocr_mode"] == "rec_only"
    assert record["skipped"] is True
    assert "unavailable" in record["skip_reason"]


def test_ocr_and_vlm_records_retain_raw_without_correction():
    ocr_record = build_ocr_record(
        page="p",
        block_id="block_00",
        row_id="00",
        image_variant="row_only_original",
        ocr_mode="det_rec",
        text="CPOTO分",
        raw_output={"items": [{"text": "CPOTO分"}]},
        detected_box_count=1,
        confidence=0.91,
        parse_error="",
    )
    vlm_record = build_vlm_record(
        page="p",
        block_id="block_00",
        row_id="00",
        image_variant="row_only_canvas_h64",
        text="CPOTO分",
        raw_response='{"transcription":"CPOTO分"}',
        parsed={"transcription": "CPOTO分", "uncertain_spans": []},
        parse_error="",
    )

    assert ocr_record["text"] == "CPOTO分"
    assert ocr_record["raw_output"]["items"][0]["text"] == "CPOTO分"
    assert vlm_record["text"] == "CPOTO分"
    assert vlm_record["raw_response"] == '{"transcription":"CPOTO分"}'
    assert "corrected_text" not in json.dumps(vlm_record, ensure_ascii=False)


def test_snapshot_file_hash_unchanged(tmp_path):
    result = tmp_path / "result_enhanced.json"
    result.write_text('{"x": 1}', encoding="utf-8")

    snapshot = snapshot_file_hash(result)

    assert snapshot["before"] == snapshot["after"]
    assert snapshot["unchanged"] is True
