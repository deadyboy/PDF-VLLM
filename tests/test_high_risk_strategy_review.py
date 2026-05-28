import json

from icu_vllm.high_risk_strategy_review import (
    HIGH_RISK_FIELDS,
    build_high_risk_row,
    summarize_high_risk_rows,
    write_high_risk_report,
)


def test_build_high_risk_row_uses_iv_refined_eval():
    row = build_high_risk_row(
        page="gold_smoke_001",
        block_id="block_09",
        field="入量_静脉用药",
        strategy="iv_v4_preserve_case_clean2x",
        gold="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        main_actual="5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        candidate_actual="5%GS100ml+葡萄糖酸钙20mliv.gtt120",
        raw_lines=["5%GS100ml+葡萄糖酸钙20MLiv.gtt120"],
        needs_review=False,
        reason="",
    )

    assert row["candidate_eval_kind"] == "unit_case_equal"
    assert row["candidate_report_correct"] is True
    assert row["main_report_correct"] is True


def test_build_high_risk_row_uses_standard_eval_for_tube_and_observation():
    tube = build_high_risk_row(
        page="p",
        block_id="block_04",
        field="管路护理",
        strategy="tube_care_single_col_vlm",
        gold="股静脉导管/是///43",
        main_actual="股静脉导管/是///;43",
        candidate_actual="股静脉导管/是///43",
    )
    obs = build_high_risk_row(
        page="p",
        block_id="block_01",
        field="病情观察及处理",
        strategy="observation_direct_v2",
        gold="CPOT0分",
        main_actual=None,
        candidate_actual="CPOT0分",
    )

    assert tube["main_eval_kind"] == "separator_error"
    assert tube["candidate_eval_kind"] == "equal"
    assert obs["main_eval_kind"] == "missing"
    assert obs["candidate_eval_kind"] == "equal"


def test_summarize_high_risk_rows_counts_improvements_and_regressions():
    rows = [
        build_high_risk_row(
            page="p",
            block_id="block_00",
            field="入量_静脉用药",
            strategy="iv_v4_preserve_case_clean2x",
            gold="A250",
            main_actual="A",
            candidate_actual="A250",
        ),
        build_high_risk_row(
            page="p",
            block_id="block_01",
            field="管路护理",
            strategy="tube_care_single_col_vlm",
            gold="B",
            main_actual="B",
            candidate_actual=None,
        ),
        build_high_risk_row(
            page="p",
            block_id="block_02",
            field="病情观察及处理",
            strategy="observation_direct_v2",
            gold="C",
            main_actual="X",
            candidate_actual="Y",
            needs_review=True,
        ),
    ]

    summary = summarize_high_risk_rows(rows)

    assert set(HIGH_RISK_FIELDS).issubset(summary["fields"])
    assert summary["overall"]["total"] == 3
    assert summary["overall"]["candidate_correct"] == 1
    assert summary["overall"]["main_wrong_candidate_correct"] == 1
    assert summary["overall"]["main_correct_candidate_wrong"] == 1
    assert summary["overall"]["both_wrong"] == 1
    assert summary["overall"]["needs_review_true"] == 1
    assert summary["fields"]["管路护理"]["candidate_missing"] == 1


def test_write_high_risk_report_outputs_markdown_and_summary_json(tmp_path):
    rows = [
        build_high_risk_row(
            page="gold_smoke_001",
            block_id="block_00",
            field="入量_静脉用药",
            strategy="iv_v4_preserve_case_clean2x",
            gold="A250",
            main_actual="A",
            candidate_actual="A250",
        )
    ]
    summary = summarize_high_risk_rows(rows)

    write_high_risk_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "high_risk_strategy_review_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_00 | 入量_静脉用药 |" in report
    data = json.loads((tmp_path / "high_risk_strategy_review_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    assert data["summary"]["overall"]["main_wrong_candidate_correct"] == 1
