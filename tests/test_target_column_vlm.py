import json

from icu_vllm.target_column_vlm import (
    TARGET_FIELDS,
    build_sidecar_payload,
    classify_diff,
    summarize_rows,
    write_report,
)


def test_build_sidecar_payload_keeps_column_outputs_separate():
    payload = build_sidecar_payload(
        "block_04",
        values={
            "入量_静脉用药": "药物250mliv.gtt250",
            "管路护理": "股静脉导管/是///43",
            "病情观察及处理": None,
        },
        raw_responses={
            "入量_静脉用药": '{"入量_静脉用药":"药物250mliv.gtt250"}',
            "管路护理": '{"管路护理":"股静脉导管/是///43"}',
            "病情观察及处理": '{"病情观察及处理":null}',
        },
        image_paths={
            "入量_静脉用药": "block_04_col_iv_drug.png",
            "管路护理": "block_04_col_tube_care.png",
            "病情观察及处理": "block_04_col_observation.png",
        },
    )

    assert payload["block_id"] == "block_04"
    assert [field for field in TARGET_FIELDS if field in payload] == list(TARGET_FIELDS)
    assert payload["入量_静脉用药"] == "药物250mliv.gtt250"
    assert payload["管路护理"] == "股静脉导管/是///43"
    assert payload["病情观察及处理"] is None
    assert payload["_raw_responses"]["管路护理"].startswith('{"管路护理"')
    assert payload["_image_paths"]["入量_静脉用药"] == "block_04_col_iv_drug.png"


def test_classify_diff_separates_equal_separator_missing_and_overfill():
    assert classify_diff("A，B", "A,B")["kind"] == "canonical_equal"
    assert classify_diff("A;B", "A；B")["kind"] == "canonical_equal"
    assert classify_diff("A;B", "AB")["kind"] == "separator_error"
    assert classify_diff("A", None)["kind"] == "missing"
    assert classify_diff(None, "A")["kind"] == "overfill"
    assert classify_diff("A1", "A2")["kind"] == "substantive_mismatch"


def test_summarize_rows_counts_column_vlm_outcomes():
    rows = [
        {
            "field": "管路护理",
            "main_eval_kind": "equal",
            "col_vlm_eval_kind": "equal",
        },
        {
            "field": "管路护理",
            "main_eval_kind": "separator_error",
            "col_vlm_eval_kind": "equal",
        },
        {
            "field": "管路护理",
            "main_eval_kind": "equal",
            "col_vlm_eval_kind": "missing",
        },
        {
            "field": "入量_静脉用药",
            "main_eval_kind": "substantive_mismatch",
            "col_vlm_eval_kind": "overfill",
        },
    ]

    summary = summarize_rows(rows)

    assert summary["管路护理"] == {
        "main_correct": 2,
        "col_correct": 2,
        "main_wrong_col_correct": 1,
        "main_correct_col_wrong": 1,
        "both_wrong": 0,
        "col_overfill": 0,
        "col_missing": 1,
    }
    assert summary["入量_静脉用药"]["col_overfill"] == 1


def test_write_report_outputs_markdown_and_summary_json(tmp_path):
    rows = [{
        "page": "gold_smoke_001",
        "block_id": "block_00",
        "field": "管路护理",
        "gold": "鼻胃管/是/墨绿色//",
        "main_actual": "鼻胃管/是/墨绿色/",
        "col_vlm_actual": "鼻胃管/是/墨绿色//",
        "main_eval_kind": "missing",
        "col_vlm_eval_kind": "equal",
    }]
    summary = summarize_rows(rows)

    write_report(tmp_path, rows, summary)

    report = (tmp_path / "target_column_vlm_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_00 | 管路护理 |" in report
    data = json.loads((tmp_path / "target_column_vlm_summary.json").read_text(encoding="utf-8"))
    assert data["summary"]["管路护理"]["main_wrong_col_correct"] == 1
