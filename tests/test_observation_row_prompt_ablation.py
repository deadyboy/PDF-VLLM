from __future__ import annotations

import json

import cv2
import numpy as np

from icu_vllm.observation_row_prompt_ablation import (
    PRECISION_TRANSCRIPTION_PROMPT,
    build_recognition_record,
    crop_row_only_variants,
    parse_precise_transcription_response,
    snapshot_file_hash,
)


def _header_row_image() -> np.ndarray:
    image = np.full((132, 320, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (8, 8), (312, 124), (0, 0, 0), 2)
    cv2.line(image, (8, 78), (312, 78), (0, 0, 0), 2)
    cv2.putText(image, "OBS", (132, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(image, "CPOT0", (18, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 1, cv2.LINE_AA)
    return image


def test_row_only_crop_is_nonempty_shorter_than_header_row_and_keeps_text(tmp_path):
    header_row_path = tmp_path / "block_00_obs_header_row_00.png"
    cv2.imwrite(str(header_row_path), _header_row_image())

    variants = crop_row_only_variants(
        header_row_image_path=header_row_path,
        output_dir=tmp_path,
        page="gold_smoke_001",
        block_id="block_00",
        row_id="00",
        data_start_y_in_image=82,
        vertical_padding_px=4,
        horizontal_padding_px=6,
        scales=(2, 3),
    )

    row_only = cv2.imread(str(tmp_path / variants["row_only_crop"]["image_path"]))
    header_row = cv2.imread(str(header_row_path))
    assert row_only is not None
    assert row_only.size > 0
    assert row_only.shape[0] < header_row.shape[0]
    assert np.count_nonzero(cv2.cvtColor(row_only, cv2.COLOR_BGR2GRAY) < 180) > 10
    assert variants["row_only_crop"]["source"] == "text_bbox_from_header_row_crop"


def test_scaled_crop_sizes_match_expected(tmp_path):
    header_row_path = tmp_path / "block_00_obs_header_row_00.png"
    cv2.imwrite(str(header_row_path), _header_row_image())

    variants = crop_row_only_variants(
        header_row_image_path=header_row_path,
        output_dir=tmp_path,
        page="gold_smoke_001",
        block_id="block_00",
        row_id="00",
        data_start_y_in_image=82,
        scales=(2, 3),
    )

    native = cv2.imread(str(tmp_path / variants["row_only_crop"]["image_path"]))
    scaled_2x = cv2.imread(str(tmp_path / variants["row_only_crop_scaled_2x"]["image_path"]))
    scaled_3x = cv2.imread(str(tmp_path / variants["row_only_crop_scaled_3x"]["image_path"]))
    assert scaled_2x.shape[:2] == (native.shape[0] * 2, native.shape[1] * 2)
    assert scaled_3x.shape[:2] == (native.shape[0] * 3, native.shape[1] * 3)


def test_precise_prompt_response_parser_keeps_uncertainty_json():
    raw = json.dumps(
        {
            "transcription": "CPOT0分",
            "uncertain_spans": [{"text": "0", "candidates": ["0", "O"], "reason": "字形相近"}],
            "visual_quality_note": "小字贴近表格线",
        },
        ensure_ascii=False,
    )

    parsed = parse_precise_transcription_response(raw)

    assert "逐字转录" in PRECISION_TRANSCRIPTION_PROMPT
    assert parsed["transcription"] == "CPOT0分"
    assert parsed["uncertain_spans"][0]["candidates"] == ["0", "O"]
    assert parsed["visual_quality_note"] == "小字贴近表格线"


def test_recognition_record_retains_raw_outputs_without_correction():
    record = build_recognition_record(
        page="gold_smoke_001",
        block_id="block_01",
        row_id="00",
        variant="row_only_crop",
        source="PaddleOCR",
        prompt_name="",
        text="CPOTO分",
        raw_output={"items": [{"text": "CPOTO分"}]},
        parse_error="",
    )

    assert record["text"] == "CPOTO分"
    assert record["raw_output"]["items"][0]["text"] == "CPOTO分"
    assert record["parse_error"] == ""


def test_snapshot_file_hash_reports_unchanged_file(tmp_path):
    result_json = tmp_path / "result.json"
    result_json.write_text('{"病情观察及处理": "CPOT0分"}', encoding="utf-8")

    snapshot = snapshot_file_hash(result_json)

    assert snapshot["unchanged"] is True
    assert snapshot["before"] == snapshot["after"]
