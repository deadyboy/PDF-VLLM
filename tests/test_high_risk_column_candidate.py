import json

from icu_vllm.high_risk_column_candidate import (
    IV_FIELD,
    TUBE_FIELD,
    build_iv_candidate,
    build_tube_candidate,
    summarize_candidates,
    write_candidate_report,
)


def test_tube_candidate_proposes_override_when_shadow_agrees():
    row = build_tube_candidate(
        page="p",
        block_id="block_04",
        gold="股静脉导管/是///43",
        main_value="股静脉导管/是///;43",
        tube_col_value="股静脉导管/是///43",
        tube_shadow_value="股静脉导管/是///43",
        tube_shadow_needs_review=False,
    )

    assert row["field"] == TUBE_FIELD
    assert row["candidate_source"] == "tube_col_vlm"
    assert row["decision"] == "propose_override"
    assert row["needs_review"] is False


def test_tube_candidate_requires_review_when_shadow_missing_or_review():
    row = build_tube_candidate(
        page="p",
        block_id="block_04",
        gold="股静脉导管/是///43",
        main_value="股静脉导管/是///;43",
        tube_col_value="股静脉导管/是///43",
        tube_shadow_value=None,
        tube_shadow_needs_review=True,
    )

    assert row["decision"] == "needs_review"
    assert row["needs_review"] is True


def test_tube_candidate_possible_overfill_when_main_empty():
    row = build_tube_candidate(
        page="p",
        block_id="block_01",
        gold=None,
        main_value=None,
        tube_col_value="导尿管/是///",
        tube_shadow_value="导尿管/是///",
        tube_shadow_needs_review=False,
    )

    assert row["decision"] == "possible_overfill_review"
    assert row["needs_review"] is True


def test_iv_candidate_proposes_override_for_correct_non_review_candidate():
    row = build_iv_candidate(
        page="p",
        block_id="block_02",
        gold="药物12ml/h+下一药物",
        main_value="药物12ml/hr下一药物",
        iv_value="药物12ml/h+下一药物",
        iv_needs_review=False,
    )

    assert row["field"] == IV_FIELD
    assert row["candidate_source"] == "iv_clean2x_v4"
    assert row["decision"] == "propose_override"
    assert row["needs_review"] is False


def test_iv_candidate_gold_needs_check_and_true_char_mismatch_require_review():
    gold_check = build_iv_candidate(
        page="p",
        block_id="block_00",
        gold="NS50m1",
        main_value="NS50",
        iv_value="NS50ml",
        iv_needs_review=False,
    )
    true_mismatch = build_iv_candidate(
        page="p",
        block_id="block_23",
        gold="药物4ml/l",
        main_value="药物4ml",
        iv_value="药物4ml/1",
        iv_needs_review=False,
    )

    assert gold_check["candidate_eval_kind"] == "gold_needs_check"
    assert gold_check["decision"] == "needs_review"
    assert true_mismatch["candidate_eval_kind"] == "true_char_mismatch"
    assert true_mismatch["decision"] == "needs_review"


def test_summarize_candidates_counts_only_two_fields():
    rows = [
        build_iv_candidate(
            page="p",
            block_id="block_02",
            gold="A12ml/h+B",
            main_value="A12ml/hrB",
            iv_value="A12ml/h+B",
            iv_needs_review=False,
        ),
        build_tube_candidate(
            page="p",
            block_id="block_04",
            gold="B",
            main_value="B",
            tube_col_value="B",
            tube_shadow_value="B",
            tube_shadow_needs_review=False,
        ),
    ]

    summary = summarize_candidates(rows)

    assert set(summary["fields"]) == {IV_FIELD, TUBE_FIELD}
    assert summary["fields"][IV_FIELD]["propose_override"] == 1
    assert summary["fields"][TUBE_FIELD]["keep_main"] == 1
    assert summary["fields"][IV_FIELD]["main_correct_candidate_wrong"] == 0


def test_write_candidate_report_outputs_required_files(tmp_path):
    rows = [
        build_iv_candidate(
            page="gold_smoke_001",
            block_id="block_02",
            gold="A12ml/h+B",
            main_value="A12ml/hrB",
            iv_value="A12ml/h+B",
            iv_needs_review=False,
        )
    ]
    summary = summarize_candidates(rows)

    write_candidate_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "high_risk_column_candidate_report.md").read_text(encoding="utf-8")
    assert "| 入量_静脉用药 |" in report
    assert "病情观察" not in report
    data = json.loads((tmp_path / "high_risk_column_candidate_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    lines = (tmp_path / "high_risk_column_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["decision"] == "propose_override"
