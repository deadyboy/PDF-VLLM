import json

from icu_vllm.observation_eval import (
    OBS_EVAL_TYPES,
    classify_observation_diff,
    build_observation_eval_row,
    summarize_observation_eval_rows,
    write_observation_eval_report,
)


def test_classify_observation_diff_separates_exact_canonical_and_punctuation():
    assert classify_observation_diff("CPOT0分", "CPOT0分")["kind"] == "exact_equal"
    assert classify_observation_diff("APTT：43.6s", "APTT:43.6s")["kind"] == "canonical_equal"
    assert classify_observation_diff("A;B，C。", "A，B;C")["kind"] == "punctuation_only"


def test_classify_observation_diff_keeps_medical_numbers_strict():
    rass = classify_observation_diff("RASS-4分，CPOT0分", "RASS-3分，CPOT0分")
    rass_sign = classify_observation_diff("RASS-4分", "RASS4分")
    aptt = classify_observation_diff("APTT:43.6s", "APTT:43.8s")

    assert rass["kind"] == "char_level_mismatch"
    assert "4" in rass["numeric_token_diff"]
    assert rass_sign["kind"] == "char_level_mismatch"
    assert aptt["kind"] == "char_level_mismatch"


def test_classify_observation_diff_identifies_missing_extra_rewrite_and_gold_check():
    assert classify_observation_diff("患者ECMO应用，机器运转正常。CPOT0分", "患者ECMO应用")["kind"] == "missing_text"
    assert classify_observation_diff("CPOT0分", "CPOT0分，另有无关补写")["kind"] == "extra_text"
    assert classify_observation_diff("遵医嘱予碘伏擦浴一次", "遵医嘱予碘优擦浴一次")["kind"] == "char_level_mismatch"
    assert classify_observation_diff("暂停胰岛素应用;。CPOT0分", "暂停胰岛素应用；CPOT0分")["kind"] == "gold_needs_check"


def test_classify_observation_diff_has_conservative_minor_equivalence():
    diff = classify_observation_diff("沪第一生化-1.25万ux10支", "沪第一生化-1.25万u×10支")

    assert diff["kind"] == "text_equivalent_minor"


def test_build_row_and_summary_count_main_vs_old_col():
    rows = [
        build_observation_eval_row(
            page="p",
            block_id="block_00",
            gold="CPOT0分",
            main_value=None,
            old_col_value="CPOT0分",
        ),
        build_observation_eval_row(
            page="p",
            block_id="block_01",
            gold="APTT：43.6s",
            main_value="APTT:43.6s",
            old_col_value="APTT:43.8s",
        ),
        build_observation_eval_row(
            page="p",
            block_id="block_02",
            gold="A;B",
            main_value="A，B",
            old_col_value="A，B",
        ),
    ]

    summary = summarize_observation_eval_rows(rows)

    assert summary["source_counts"]["main"]["missing_text"] == 1
    assert summary["source_counts"]["main"]["canonical_equal"] == 1
    assert summary["source_counts"]["main"]["punctuation_only"] == 1
    assert summary["source_counts"]["old_col"]["exact_equal"] == 1
    assert summary["source_counts"]["old_col"]["char_level_mismatch"] == 1
    assert summary["review_queue_count"] == 2
    assert set(summary["source_counts"]) == {"main", "old_col"}
    assert set(summary["case_error_type_counts"]).issuperset(set(OBS_EVAL_TYPES))


def test_write_observation_eval_report_outputs_required_files(tmp_path):
    rows = [
        build_observation_eval_row(
            page="p",
            block_id="block_00",
            gold="CPOT0分",
            main_value=None,
            old_col_value="CPOT0分",
        )
    ]
    summary = summarize_observation_eval_rows(rows)

    write_observation_eval_report(tmp_path, rows, summary, metadata={"model_calls": 0})

    report = (tmp_path / "observation_eval_refined_report.md").read_text(encoding="utf-8")
    assert "verbatim sidecar 不进入候选覆盖" in report
    assert "| p | block_00 |" in report
    assert "missing_text" in report
    payload = json.loads((tmp_path / "observation_eval_refined_summary.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_calls"] == 0
    assert payload["metadata"]["verbatim_candidate_status"] == "not_candidate"
    cases = (tmp_path / "observation_eval_refined_cases.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(cases[0])["field"] == "病情观察及处理"
