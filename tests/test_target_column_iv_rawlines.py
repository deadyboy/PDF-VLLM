import json

from icu_vllm.target_column_iv_rawlines import (
    IV_FIELD,
    build_iv_rawlines_sidecar,
    raw_lines_tail_kind,
    summarize_iv_rows,
    write_iv_rawlines_report,
)


def test_build_iv_rawlines_sidecar_preserves_raw_lines_and_final_value():
    payload = build_iv_rawlines_sidecar(
        block_id="block_04",
        raw_lines=["钠钾镁钙葡萄糖注射液250mliv.gtt", "250"],
        final_value="钠钾镁钙葡萄糖注射液250mliv.gtt250",
        needs_review=False,
        reason="",
        raw_response='{"raw_lines":["..."],"final_value":"..."}',
        image_path="block_04_col_iv_drug.png",
    )

    assert payload == {
        "block_id": "block_04",
        "field": IV_FIELD,
        "raw_lines": ["钠钾镁钙葡萄糖注射液250mliv.gtt", "250"],
        "final_value": "钠钾镁钙葡萄糖注射液250mliv.gtt250",
        "needs_review": False,
        "reason": "",
        "_raw_response": '{"raw_lines":["..."],"final_value":"..."}',
        "_image_path": "block_04_col_iv_drug.png",
    }


def test_raw_lines_tail_kind_distinguishes_missing_tail_from_bad_merge():
    gold = "钠钾镁钙葡萄糖注射液250mliv.gtt250"

    assert raw_lines_tail_kind(
        gold,
        "钠钾镁钙葡萄糖注射液250mliv.gtt",
        ["钠钾镁钙葡萄糖注射液250mliv.gtt", "250"],
    ) == "raw_lines_contains_tail_but_final_wrong"
    assert raw_lines_tail_kind(
        gold,
        "钠钾镁钙葡萄糖注射液250mliv.gtt",
        ["钠钾镁钙葡萄糖注射液250mliv.gtt"],
    ) == "raw_lines_missing_tail"
    assert raw_lines_tail_kind(
        gold,
        gold,
        ["钠钾镁钙葡萄糖注射液250mliv.gtt", "250"],
    ) == "none"


def test_summarize_iv_rows_compares_old_col_and_v2():
    rows = [
        {
            "main_eval_kind": "substantive_mismatch",
            "old_col_eval_kind": "substantive_mismatch",
            "iv_v2_eval_kind": "equal",
            "iv_v2_tail_kind": "none",
        },
        {
            "main_eval_kind": "equal",
            "old_col_eval_kind": "equal",
            "iv_v2_eval_kind": "substantive_mismatch",
            "iv_v2_tail_kind": "raw_lines_contains_tail_but_final_wrong",
        },
        {
            "main_eval_kind": "substantive_mismatch",
            "old_col_eval_kind": "missing",
            "iv_v2_eval_kind": "missing",
            "iv_v2_tail_kind": "raw_lines_missing_tail",
        },
    ]

    summary = summarize_iv_rows(rows)

    assert summary["col_correct"]["old_col"] == 1
    assert summary["col_correct"]["iv_v2_rawlines"] == 1
    assert summary["main_wrong_col_correct"]["old_col"] == 0
    assert summary["main_wrong_col_correct"]["iv_v2_rawlines"] == 1
    assert summary["main_correct_col_wrong"]["old_col"] == 0
    assert summary["main_correct_col_wrong"]["iv_v2_rawlines"] == 1
    assert summary["col_missing"]["old_col"] == 1
    assert summary["col_missing"]["iv_v2_rawlines"] == 1
    assert summary["raw_lines_contains_tail_but_final_wrong"]["iv_v2_rawlines"] == 1
    assert summary["raw_lines_missing_tail"]["iv_v2_rawlines"] == 1


def test_write_iv_rawlines_report_outputs_expected_files(tmp_path):
    rows = [{
        "page": "gold_smoke_001",
        "block_id": "block_00",
        "gold": "A250",
        "main_actual": "A",
        "col_vlm_old": "A",
        "col_vlm_iv_v2_rawlines": "A250",
        "main_eval_kind": "substantive_mismatch",
        "old_col_eval_kind": "substantive_mismatch",
        "iv_v2_eval_kind": "equal",
        "raw_lines": ["A", "250"],
        "needs_review": False,
        "reason": "",
        "iv_v2_tail_kind": "none",
    }]
    summary = summarize_iv_rows(rows)

    write_iv_rawlines_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "target_column_iv_rawlines_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_00 |" in report
    data = json.loads((tmp_path / "target_column_iv_rawlines_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    assert data["summary"]["main_wrong_col_correct"]["iv_v2_rawlines"] == 1
