from __future__ import annotations

import json

from icu_vllm.observation_layered_eval import (
    classify_layered_difference,
    load_previous_rows,
    normalize_ascii_case,
    normalize_punctuation_space,
    normalize_unit_style,
    summarize_layered_rows,
)


def test_layered_classification_strict_and_punctuation_space():
    strict = classify_layered_difference("CPOT0分", "CPOT0分", original_error_type="完全一致")
    punctuation = classify_layered_difference("APTT：43.6s；遵医嘱", "APTT:43.6s;遵医嘱", original_error_type="字符级错误")

    assert strict["layer"] == "strict_exact"
    assert punctuation["layer"] == "punctuation_space_normalized_exact"


def test_ascii_case_and_unit_style_layers_do_not_change_digits():
    assert normalize_ascii_case("100mL ux R/min") == normalize_ascii_case("100ml uX r/min")
    assert normalize_unit_style("5μg 37℃") == normalize_unit_style("5ug 37°C")
    mismatch = classify_layered_difference("80ml/h", "80m1/h", original_error_type="字符级错误")

    assert classify_layered_difference("100mL", "100ml", original_error_type="字符级错误")["layer"] == "ascii_case_normalized_exact"
    assert classify_layered_difference("5μg", "5ug", original_error_type="字符级错误")["layer"] == "unit_style_normalized_exact"
    assert mismatch["layer"] == "meaningful_text_difference"


def test_severe_failure_layer_uses_original_failure_type():
    missing = classify_layered_difference("APTT:43.6s", None, original_error_type="漏识别")
    rewrite = classify_layered_difference("患者清醒", "患者病情稳定，继续观察", original_error_type="改写/概括")

    assert missing["layer"] == "severe_failure"
    assert rewrite["layer"] == "severe_failure"


def test_load_previous_rows_maps_expected_columns(tmp_path):
    summary = {
        "rows": [
            {
                "case_id": "p__block_00",
                "gold": "CPOT0分",
                "image_variant": "row_only_original",
                "image_variant_label": "原始正文窄带",
                "method_id": "Qwen3-32B:precise_transcription_prompt",
                "method_label": "Qwen精密prompt",
                "recognized_text": "CPOTO分",
                "edit_distance": 1,
                "brief_diff": "-0;+O",
                "error_type": "字符级错误",
            }
        ]
    }
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")

    rows = load_previous_rows(path)

    assert rows[0]["input_version"] == "row_only_original"
    assert rows[0]["method"] == "Qwen3-32B:precise_transcription_prompt"
    assert rows[0]["raw_prediction"] == "CPOTO分"
    assert rows[0]["diff"] == "-0;+O"


def test_summary_counts_layered_pass_rates():
    rows = [
        {"input_version": "v", "input_version_label": "V", "method": "Qwen3-32B:x", "method_label": "Qwen", "layer": "strict_exact", "edit_distance": 0},
        {"input_version": "v", "input_version_label": "V", "method": "Qwen3-32B:x", "method_label": "Qwen", "layer": "unit_style_normalized_exact", "edit_distance": 2},
        {"input_version": "v", "input_version_label": "V", "method": "PaddleOCR:det_rec", "method_label": "OCR", "layer": "meaningful_text_difference", "edit_distance": 9},
    ]

    summary = summarize_layered_rows(rows)
    qwen = next(item for item in summary["by_input_method"] if item["method"] == "Qwen3-32B:x")

    assert qwen["total"] == 2
    assert qwen["unit_style_pass_rate"] == 1.0
    assert qwen["meaningful_text_difference"] == 0
    assert qwen["average_edit_distance"] == 1.0
