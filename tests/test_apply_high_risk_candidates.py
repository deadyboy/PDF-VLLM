import json

from icu_vllm.apply_high_risk_candidates import (
    IV_FIELD,
    TUBE_FIELD,
    apply_candidate_overrides,
    evaluate_enhanced_rows,
    write_enhanced_outputs,
)


def test_apply_candidate_overrides_only_uses_safe_propose_override():
    main_rows = [
        {"_block_id": "block_00", IV_FIELD: "药Aiv.gtt", TUBE_FIELD: "鼻胃管/是/墨绿色/"},
        {"_block_id": "block_04", IV_FIELD: "药B", TUBE_FIELD: "股静脉导管/是///;43"},
        {"_block_id": "block_08", IV_FIELD: None, TUBE_FIELD: None},
    ]
    candidates = [
        {
            "page": "p",
            "block_id": "block_00",
            "field": IV_FIELD,
            "candidate_value": "药Aiv.gtt250",
            "candidate_source": "iv_clean2x_v4",
            "decision": "propose_override",
            "needs_review": False,
            "reason": "iv_candidate_correct_without_review",
        },
        {
            "page": "p",
            "block_id": "block_04",
            "field": TUBE_FIELD,
            "candidate_value": "股静脉导管/是///43",
            "candidate_source": "tube_col_vlm",
            "decision": "needs_review",
            "needs_review": True,
            "reason": "tube_shadow_missing_or_needs_review",
        },
        {
            "page": "p",
            "block_id": "block_08",
            "field": IV_FIELD,
            "candidate_value": "风险过填",
            "candidate_source": "iv_clean2x_v4",
            "decision": "propose_override",
            "needs_review": False,
            "reason": "should_skip_main_empty",
        },
        {
            "page": "p",
            "block_id": "block_00",
            "field": "病情观察及处理",
            "candidate_value": "不允许处理",
            "candidate_source": "observation",
            "decision": "propose_override",
            "needs_review": False,
            "reason": "wrong_field",
        },
    ]

    enhanced_rows, logs = apply_candidate_overrides(main_rows, candidates, page="p")

    assert main_rows[0][IV_FIELD] == "药Aiv.gtt"
    assert enhanced_rows[0][IV_FIELD] == "药Aiv.gtt250"
    assert enhanced_rows[1][TUBE_FIELD] == "股静脉导管/是///;43"
    assert enhanced_rows[2][IV_FIELD] is None
    assert logs == [
        {
            "page": "p",
            "block_id": "block_00",
            "field": IV_FIELD,
            "old_value": "药Aiv.gtt",
            "new_value": "药Aiv.gtt250",
            "candidate_source": "iv_clean2x_v4",
            "reason": "iv_candidate_correct_without_review",
        }
    ]


def test_evaluate_enhanced_rows_counts_fixed_and_new_errors():
    gold_rows = [
        {"_block_id": "block_00", IV_FIELD: "药Aiv.gtt250", TUBE_FIELD: "鼻胃管/是/墨绿色//"},
        {"_block_id": "block_01", IV_FIELD: "药B", TUBE_FIELD: "导尿管/是///"},
    ]
    main_rows = [
        {"_block_id": "block_00", IV_FIELD: "药Aiv.gtt;250", TUBE_FIELD: "鼻胃管/是/墨绿色/"},
        {"_block_id": "block_01", IV_FIELD: "药B", TUBE_FIELD: "导尿管/是///"},
    ]
    enhanced_rows = [
        {"_block_id": "block_00", IV_FIELD: "药Aiv.gtt250", TUBE_FIELD: "鼻胃管/是/墨绿色//"},
        {"_block_id": "block_01", IV_FIELD: "药B错误", TUBE_FIELD: "导尿管/是///"},
    ]

    rows, page_summary, field_summary = evaluate_enhanced_rows(
        page="p",
        gold_rows=gold_rows,
        main_rows=main_rows,
        enhanced_rows=enhanced_rows,
    )

    assert page_summary["main"]["separator_error"] == 1
    assert page_summary["enhanced"]["strict_total"] == 3
    assert field_summary[IV_FIELD]["fixed_by_override"] == 1
    assert field_summary[IV_FIELD]["new_errors"] == 1
    assert field_summary[TUBE_FIELD]["fixed_by_override"] == 1
    assert {row["result_type"] for row in rows} == {"main", "enhanced"}


def test_write_enhanced_outputs_creates_required_artifacts(tmp_path):
    page_outputs = {
        "p": {
            "enhanced_rows": [{"_block_id": "block_00", IV_FIELD: "药Aiv.gtt250"}],
            "result_container": [{"_block_id": "block_00", IV_FIELD: "药Aiv.gtt250"}],
            "main_hash_before": "abc",
            "main_hash_after": "abc",
            "main_hash_unchanged": True,
        }
    }
    override_logs = [
        {
            "page": "p",
            "block_id": "block_00",
            "field": IV_FIELD,
            "old_value": "药Aiv.gtt",
            "new_value": "药Aiv.gtt250",
            "candidate_source": "iv_clean2x_v4",
            "reason": "iv_candidate_correct_without_review",
        }
    ]
    page_table = [
        {"page": "p", "result_type": "main", "strict_total": 0, "canonical_only": 0, "separator_error": 1, "missing": 0, "overfill": 0, "substantive_mismatch": 0},
        {"page": "p", "result_type": "enhanced", "strict_total": 1, "canonical_only": 0, "separator_error": 0, "missing": 0, "overfill": 0, "substantive_mismatch": 0},
    ]
    field_summary = {
        IV_FIELD: {"main_correct": 0, "enhanced_correct": 1, "fixed_by_override": 1, "new_errors": 0},
        TUBE_FIELD: {"main_correct": 0, "enhanced_correct": 0, "fixed_by_override": 0, "new_errors": 0},
    }

    write_enhanced_outputs(
        output_dir=tmp_path,
        page_outputs=page_outputs,
        override_logs=override_logs,
        page_table=page_table,
        field_summary=field_summary,
        metadata={"model_calls": 0},
    )

    assert (tmp_path / "enhanced_results" / "p" / "result_enhanced.json").exists()
    assert json.loads((tmp_path / "override_log.jsonl").read_text(encoding="utf-8").splitlines()[0])["field"] == IV_FIELD
    report = (tmp_path / "enhanced_eval_report.md").read_text(encoding="utf-8")
    assert "| p | enhanced | 1 | 0 | 0 | 0 | 0 | 0 |" in report
    summary = json.loads((tmp_path / "enhanced_eval_summary.json").read_text(encoding="utf-8"))
    assert summary["metadata"]["model_calls"] == 0
