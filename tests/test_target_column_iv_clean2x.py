import json

from icu_vllm.target_column_iv_clean2x import (
    IV_CROP_VARIANT,
    build_clean2x_row,
    clean2x_image_name,
    summarize_clean2x_rows,
    write_clean2x_report,
)


def test_clean2x_image_name_is_variant_specific():
    assert IV_CROP_VARIANT == "clean_2x"
    assert clean2x_image_name("block_04") == "block_04_col_iv_drug_clean_2x.png"


def test_build_clean2x_row_compares_main_old_crop_and_clean2x():
    row = build_clean2x_row(
        page="gold_smoke_001",
        block_id="block_04",
        gold="药物250mliv.gtt250",
        main_actual="药物250mliv.gtt;250",
        old_crop_actual="药物250mliv.gtt;250",
        clean2x_actual="药物250mliv.gtt250",
        clean2x_raw_lines=["药物250mliv.gtt", "250"],
        clean2x_needs_review=False,
        clean2x_reason="",
    )

    assert row["main_eval_kind"] == "separator_error"
    assert row["old_crop_eval_kind"] == "separator_error"
    assert row["clean_2x_eval_kind"] == "equal"
    assert row["clean_2x_tail_kind"] == "none"
    assert row["clean_2x_raw_lines"] == ["药物250mliv.gtt", "250"]


def test_summarize_clean2x_rows_counts_metrics_and_char_mismatch():
    rows = [
        {
            "main_eval_kind": "substantive_mismatch",
            "old_crop_eval_kind": "substantive_mismatch",
            "clean_2x_eval_kind": "equal",
            "old_crop_tail_kind": "raw_lines_missing_tail",
            "clean_2x_tail_kind": "none",
        },
        {
            "main_eval_kind": "equal",
            "old_crop_eval_kind": "equal",
            "clean_2x_eval_kind": "substantive_mismatch",
            "old_crop_tail_kind": "none",
            "clean_2x_tail_kind": "raw_lines_contains_tail_but_final_wrong",
        },
        {
            "main_eval_kind": "substantive_mismatch",
            "old_crop_eval_kind": "missing",
            "clean_2x_eval_kind": "missing",
            "old_crop_tail_kind": "raw_lines_missing_tail",
            "clean_2x_tail_kind": "raw_lines_missing_tail",
        },
    ]

    summary = summarize_clean2x_rows(rows)

    assert summary["col_correct"]["old_crop"] == 1
    assert summary["col_correct"]["clean_2x"] == 1
    assert summary["main_wrong_col_correct"]["clean_2x"] == 1
    assert summary["main_correct_col_wrong"]["clean_2x"] == 1
    assert summary["both_wrong"]["old_crop"] == 2
    assert summary["col_missing"]["clean_2x"] == 1
    assert summary["raw_lines_contains_tail_but_final_wrong"]["clean_2x"] == 1
    assert summary["raw_lines_missing_tail"]["old_crop"] == 2
    assert summary["raw_lines_missing_tail"]["clean_2x"] == 1
    assert summary["char_level_mismatch"]["old_crop"] == 1
    assert summary["char_level_mismatch"]["clean_2x"] == 1


def test_write_clean2x_report_outputs_expected_files(tmp_path):
    rows = [{
        "page": "gold_smoke_001",
        "block_id": "block_00",
        "gold": "A250",
        "main_actual": "A",
        "iv_v2_rawlines_old_crop": "A",
        "iv_v2_rawlines_clean_2x": "A250",
        "main_eval_kind": "substantive_mismatch",
        "old_crop_eval_kind": "substantive_mismatch",
        "clean_2x_eval_kind": "equal",
        "old_crop_raw_lines": ["A"],
        "clean_2x_raw_lines": ["A", "250"],
        "clean_2x_needs_review": False,
        "clean_2x_reason": "",
        "old_crop_tail_kind": "raw_lines_missing_tail",
        "clean_2x_tail_kind": "none",
    }]
    summary = summarize_clean2x_rows(rows)

    write_clean2x_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "target_column_iv_rawlines_clean2x_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_00 |" in report
    data = json.loads((tmp_path / "target_column_iv_rawlines_clean2x_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    assert data["summary"]["main_wrong_col_correct"]["clean_2x"] == 1
