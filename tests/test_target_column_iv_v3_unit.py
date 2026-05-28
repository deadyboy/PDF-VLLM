import json

from icu_vllm.prompts import PROMPT_COL_IV_DRUG_V3_UNIT_AWARE
from icu_vllm.target_column_iv_v3_unit import (
    build_v3_unit_row,
    build_v3_unit_sidecar,
    summarize_v3_unit_rows,
    write_v3_unit_report,
)


def test_v3_prompt_contains_unit_and_review_calibration_rules():
    assert "只有图像中存在明确字母 r 时，才输出 /hr" in PROMPT_COL_IV_DRUG_V3_UNIT_AWARE
    assert "UG/ug 不要误读成 0G/0g" in PROMPT_COL_IV_DRUG_V3_UNIT_AWARE
    assert "不要因为进行了标准续行合并就设置 needs_review=true" in PROMPT_COL_IV_DRUG_V3_UNIT_AWARE


def test_build_v3_unit_sidecar_keeps_raw_lines_and_review_state():
    payload = build_v3_unit_sidecar(
        block_id="block_04",
        raw_lines=["药物12ml/h+下一药物"],
        final_value="药物12ml/h+下一药物",
        needs_review=False,
        reason="",
        raw_response='{"final_value":"药物12ml/h+下一药物"}',
        image_path="crops/gold_dev_m_002/block_04_col_iv_drug_clean_2x.png",
    )

    assert payload["block_id"] == "block_04"
    assert payload["field"] == "入量_静脉用药"
    assert payload["prompt_variant"] == "v3_unit_aware"
    assert payload["raw_lines"] == ["药物12ml/h+下一药物"]
    assert payload["final_value"] == "药物12ml/h+下一药物"
    assert payload["needs_review"] is False


def test_build_v3_unit_row_compares_v2_clean2x_and_v3():
    row = build_v3_unit_row(
        page="gold_dev_m_002",
        block_id="block_04",
        gold="药物12ml/h+下一药物",
        main_actual="药物12ml/hr下一药物",
        v2_actual="药物12ml/hr下一药物",
        v3_actual="药物12ml/h+下一药物",
        v2_raw_lines=["药物12ml/hr下一药物"],
        v3_raw_lines=["药物12ml/h+下一药物"],
        v2_needs_review=True,
        v3_needs_review=False,
        v2_reason="unit uncertain",
        v3_reason="",
    )

    assert row["main_eval_kind"] == "substantive_mismatch"
    assert row["v2_clean2x_eval_kind"] == "substantive_mismatch"
    assert row["v3_unit_eval_kind"] == "equal"
    assert row["v2_clean2x_needs_review"] is True
    assert row["v3_unit_needs_review"] is False


def test_summarize_v3_unit_rows_counts_review_and_char_metrics():
    rows = [
        build_v3_unit_row(
            page="p",
            block_id="block_00",
            gold="A250",
            main_actual="A",
            v2_actual="A",
            v3_actual="A250",
            v2_raw_lines=["A"],
            v3_raw_lines=["A", "250"],
            v2_needs_review=True,
            v3_needs_review=False,
        ),
        build_v3_unit_row(
            page="p",
            block_id="block_01",
            gold="B12ml/h+",
            main_actual="B12ml/h+",
            v2_actual="B12ml/h+",
            v3_actual="B12ml/h+",
            v2_raw_lines=["B12ml/h+"],
            v3_raw_lines=["B12ml/h+"],
            v2_needs_review=True,
            v3_needs_review=False,
        ),
        build_v3_unit_row(
            page="p",
            block_id="block_02",
            gold="C200UG",
            main_actual="C200UG",
            v2_actual="C200UG",
            v3_actual="C2000G",
            v2_raw_lines=["C200UG"],
            v3_raw_lines=["C2000G"],
            v2_needs_review=False,
            v3_needs_review=True,
        ),
    ]

    summary = summarize_v3_unit_rows(rows)

    assert summary["col_correct"]["v2_clean2x"] == 2
    assert summary["col_correct"]["v3_unit"] == 2
    assert summary["main_wrong_col_correct"]["v3_unit"] == 1
    assert summary["main_correct_col_wrong"]["v3_unit"] == 1
    assert summary["raw_lines_missing_tail"]["v2_clean2x"] == 1
    assert summary["char_level_mismatch"]["v3_unit"] == 1
    assert summary["needs_review_true"]["v2_clean2x"] == 2
    assert summary["needs_review_true"]["v3_unit"] == 1
    assert summary["correct_but_needs_review"]["v2_clean2x"] == 1
    assert summary["correct_but_needs_review"]["v3_unit"] == 0


def test_write_v3_unit_report_outputs_expected_files(tmp_path):
    rows = [
        build_v3_unit_row(
            page="gold_smoke_001",
            block_id="block_04",
            gold="A250",
            main_actual="A",
            v2_actual="A",
            v3_actual="A250",
            v2_raw_lines=["A"],
            v3_raw_lines=["A", "250"],
            v2_needs_review=True,
            v3_needs_review=False,
        )
    ]
    summary = summarize_v3_unit_rows(rows)

    write_v3_unit_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "target_column_iv_v3_unit_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_04 |" in report
    data = json.loads((tmp_path / "target_column_iv_v3_unit_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    assert data["summary"]["main_wrong_col_correct"]["v3_unit"] == 1
