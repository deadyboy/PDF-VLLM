from __future__ import annotations

import json

from icu_vllm.observation_med_context_prompt_probe import (
    MED_CONTEXT_PROMPT,
    _map_med_records_to_rows,
    build_med_context_record,
    compare_prompt_rows,
    load_precise_baseline_rows,
    parse_med_context_response,
    summarize_prompt_comparison,
)


def test_med_context_prompt_contains_reference_terms_without_correction_language():
    for term in ["遵医嘱", "泵入", "肠内营养液", "肝素钠", "VV-ECMO", "CVVHDF", "CPOT0分", "APTT"]:
        assert term in MED_CONTEXT_PROMPT
    assert "纠错" not in MED_CONTEXT_PROMPT
    assert "替换为" not in MED_CONTEXT_PROMPT


def test_parse_med_context_response_keeps_uncertain_spans():
    raw = json.dumps(
        {
            "transcription": "APTT:43.6s,遵医嘱",
            "uncertain_spans": [{"text": "43.6", "candidates": ["43.6", "48.6"], "reason": "小字"}],
            "visual_quality_note": "文字较小",
        },
        ensure_ascii=False,
    )

    parsed = parse_med_context_response(raw)

    assert parsed["transcription"] == "APTT:43.6s,遵医嘱"
    assert parsed["uncertain_spans"][0]["candidates"] == ["43.6", "48.6"]
    assert parsed["parse_error"] == ""


def test_build_med_context_record_keeps_raw_response_without_correction():
    record = build_med_context_record(
        page="p",
        block_id="block_00",
        row_id="00",
        image_variant="row_only_canvas_h64",
        text="80m1/h",
        raw_response='{"transcription":"80m1/h"}',
        parsed={"transcription": "80m1/h"},
        parse_error="",
    )

    assert record["text"] == "80m1/h"
    assert record["raw_response"] == '{"transcription":"80m1/h"}'
    assert "corrected" not in json.dumps(record, ensure_ascii=False)


def test_load_precise_baseline_rows_filters_qwen_precise(tmp_path):
    data = {
        "rows": [
            {
                "case_id": "p__block_00",
                "gold": "CPOT0分",
                "image_variant": "row_only_canvas_h64",
                "image_variant_label": "固定文字高64",
                "method_id": "Qwen3-32B:precise_transcription_prompt",
                "method_label": "Qwen精密prompt",
                "recognized_text": "CPOT0分",
                "edit_distance": 0,
                "brief_diff": "",
                "error_type": "完全一致",
            },
            {
                "case_id": "p__block_00",
                "gold": "CPOT0分",
                "image_variant": "row_only_canvas_h64",
                "method_id": "PaddleOCR:det_rec",
                "recognized_text": "CPOTO分",
            },
        ]
    }
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rows = load_precise_baseline_rows(path)

    assert len(rows) == 1
    assert rows[0]["method"] == "Qwen3-32B:precise_transcription_prompt"
    assert rows[0]["raw_prediction"] == "CPOT0分"


def test_compare_and_summarize_prompt_rows():
    baseline = [
        {
            "case_id": "p__block_00",
            "gold": "80ml/h",
            "input_version": "row_only_canvas_h64",
            "input_version_label": "固定文字高64",
            "method": "Qwen3-32B:precise_transcription_prompt",
            "method_label": "Qwen精密prompt",
            "raw_prediction": "80m1/h",
            "edit_distance": 1,
            "diff": "-l;+1",
        }
    ]
    med_rows = [
        {
            "case_id": "p__block_00",
            "gold": "80ml/h",
            "input_version": "row_only_canvas_h64",
            "input_version_label": "固定文字高64",
            "method": "Qwen3-32B:medical_context_prompt",
            "method_label": "Qwen医学参考prompt",
            "raw_prediction": "80ml/h",
            "edit_distance": 0,
            "diff": "",
        }
    ]

    compared = compare_prompt_rows(baseline, med_rows)
    summary = summarize_prompt_comparison(compared)

    assert compared[0]["delta_edit_distance"] == -1
    assert compared[0]["change"] == "improved"
    assert summary["overall"]["improved"] == 1


def test_med_records_are_combined_by_case_variant_before_compare():
    baseline = [
        {
            "case_id": "p__block_00",
            "page": "p",
            "block_id": "block_00",
            "gold": "AB",
            "input_version": "row_only_canvas_h64",
            "input_version_label": "固定文字高64",
            "method": "Qwen3-32B:precise_transcription_prompt",
            "method_label": "Qwen精密prompt",
            "raw_prediction": "A1",
            "edit_distance": 1,
            "diff": "",
        }
    ]
    records = [
        {"page": "p", "block_id": "block_00", "row_id": "01", "image_variant": "row_only_canvas_h64", "text": "B", "parsed": {}},
        {"page": "p", "block_id": "block_00", "row_id": "00", "image_variant": "row_only_canvas_h64", "text": "A", "parsed": {}},
    ]

    rows = _map_med_records_to_rows(records, baseline)

    assert len(rows) == 1
    assert rows[0]["raw_prediction"] == "AB"
    assert rows[0]["edit_distance"] == 0
