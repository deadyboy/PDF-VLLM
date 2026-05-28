import json

from icu_vllm.prompts import PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE
from icu_vllm.target_column_iv_v4_preserve_case import (
    build_v4_preserve_case_row,
    build_v4_preserve_case_sidecar,
    summarize_v4_preserve_case_rows,
    write_v4_preserve_case_report,
)


def test_v4_prompt_preserves_unit_case_and_h_plus_rule():
    assert "如果 raw_lines 中是 ML，final_value 仍保留 ML" in PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE
    assert "不要把 ML 改成 ml" in PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE
    assert "不要把 h 后面的 + 误读成 r" in PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE
    assert "不要因为进行了标准续行合并就设置 needs_review=true" in PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE
    assert "final_value 中应按容量单位输出 ml" not in PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE


def test_build_v4_sidecar_records_prompt_variant():
    payload = build_v4_preserve_case_sidecar(
        block_id="block_09",
        raw_lines=["5%GS100ml+葡萄糖酸钙20MLiv.gtt120"],
        final_value="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        needs_review=False,
        reason="",
        raw_response='{"final_value":"5%GS100ml+葡萄糖酸钙20MLiv.gtt120"}',
        image_path="crops/gold_smoke_001/block_09_col_iv_drug_clean_2x.png",
    )

    assert payload["prompt_variant"] == "v4_preserve_case"
    assert payload["final_value"] == "5%GS100ml+葡萄糖酸钙20MLiv.gtt120"
    assert payload["needs_review"] is False


def test_build_v4_row_uses_refined_iv_eval_kinds():
    row = build_v4_preserve_case_row(
        page="gold_smoke_001",
        block_id="block_09",
        gold="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        main_actual="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        v2_actual="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        v3_actual="5%GS100ml+葡萄糖酸钙20mliv.gtt120",
        v4_actual="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        v2_raw_lines=["5%GS100ml+葡萄糖酸钙20MLiv.gtt120"],
        v3_raw_lines=["5%GS100ml+葡萄糖酸钙20MLiv.gtt120"],
        v4_raw_lines=["5%GS100ml+葡萄糖酸钙20MLiv.gtt120"],
        v2_needs_review=False,
        v3_needs_review=False,
        v4_needs_review=False,
    )

    assert row["v3_unit_eval_kind"] == "unit_case_equal"
    assert row["v4_preserve_case_eval_kind"] == "equal"
    assert row["v4_preserve_case_tail_kind"] == "none"


def test_summarize_v4_rows_counts_refined_kinds_and_review():
    rows = [
        build_v4_preserve_case_row(
            page="p",
            block_id="block_00",
            gold="A12ml/h+B",
            main_actual="A12ml/hrB",
            v2_actual="A12ml/hrB",
            v3_actual="A12ml/h+B",
            v4_actual="A12ml/h+B",
            v2_raw_lines=["A12ml/hrB"],
            v3_raw_lines=["A12ml/h+B"],
            v4_raw_lines=["A12ml/h+B"],
            v2_needs_review=False,
            v3_needs_review=False,
            v4_needs_review=False,
        ),
        build_v4_preserve_case_row(
            page="p",
            block_id="block_01",
            gold="C20MLiv",
            main_actual="C20MLiv",
            v2_actual="C20MLiv",
            v3_actual="C20mliv",
            v4_actual="C20MLiv",
            v2_raw_lines=["C20MLiv"],
            v3_raw_lines=["C20MLiv"],
            v4_raw_lines=["C20MLiv"],
            v2_needs_review=False,
            v3_needs_review=False,
            v4_needs_review=False,
        ),
        build_v4_preserve_case_row(
            page="p",
            block_id="block_02",
            gold="NS50m1",
            main_actual="NS50ml",
            v2_actual="NS50ml",
            v3_actual="NS50ml",
            v4_actual="NS50ml",
            v2_raw_lines=["NS50ml"],
            v3_raw_lines=["NS50ml"],
            v4_raw_lines=["NS50ml"],
            v2_needs_review=False,
            v3_needs_review=False,
            v4_needs_review=False,
        ),
    ]

    summary = summarize_v4_preserve_case_rows(rows)

    assert summary["report_correct"]["v2_clean2x"] == 2
    assert summary["report_correct"]["v3_unit"] == 3
    assert summary["report_correct"]["v4_preserve_case"] == 3
    assert summary["unit_case_equal"]["v3_unit"] == 1
    assert summary["gold_needs_check"]["v4_preserve_case"] == 1
    assert summary["true_char_mismatch"]["v2_clean2x"] == 1


def test_write_v4_report_outputs_expected_files(tmp_path):
    rows = [
        build_v4_preserve_case_row(
            page="gold_smoke_001",
            block_id="block_02",
            gold="A12ml/h+B",
            main_actual="A12ml/hrB",
            v2_actual="A12ml/hrB",
            v3_actual="A12ml/h+B",
            v4_actual="A12ml/h+B",
            v2_raw_lines=["A12ml/hrB"],
            v3_raw_lines=["A12ml/h+B"],
            v4_raw_lines=["A12ml/h+B"],
            v2_needs_review=False,
            v3_needs_review=False,
            v4_needs_review=False,
        )
    ]
    rows.append(
        build_v4_preserve_case_row(
            page="gold_dev_m_002",
            block_id="block_00",
            gold="NS50m1",
            main_actual="NS50ml",
            v2_actual="NS50ml",
            v3_actual="NS50ml",
            v4_actual="NS50ml",
            v2_raw_lines=["NS50ml"],
            v3_raw_lines=["NS50ml"],
            v4_raw_lines=["NS50ml"],
            v2_needs_review=False,
            v3_needs_review=False,
            v4_needs_review=False,
        )
    )
    summary = summarize_v4_preserve_case_rows(rows)

    write_v4_preserve_case_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "target_column_iv_v4_preserve_case_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_02 |" in report
    data = json.loads((tmp_path / "target_column_iv_v4_preserve_case_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    assert data["summary"]["report_correct"]["v4_preserve_case"] == 2
    corrections = (tmp_path / "gold_corrections.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(corrections) == 1
    assert json.loads(corrections[0])["kind"] == "gold_needs_check"
