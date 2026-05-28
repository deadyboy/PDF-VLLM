from __future__ import annotations

import json

from icu_vllm.observation_text_reviewer_tolerant_eval import (
    build_tolerant_eval_record,
    classify_edit_effect,
    evaluate_clinical_semantic,
    evaluate_format_tolerant,
    load_equivalence_rules,
    normalize_format_tolerant,
    verify_hash_entries,
)


def _rules(tmp_path):
    path = tmp_path / "clinical_equivalence_rules.yaml"
    path.write_text(
        """
punctuation_equivalence:
  enabled: true
  cpot_score_optional_space: true
unit_surface_equivalence:
  enabled: true
  units:
    r/min: ["转/分", "转/分钟", "r/min", "rpm"]
    L/min: ["L/分", "L/min", "L/分钟"]
    ml: ["ml", "mL", "ML"]
    mg: ["mg", "MG"]
    ug: ["ug", "UG", "μg"]
    ℃: ["℃", "°C"]
numeric_equivalence:
  enabled: true
  allow_leading_zero_equivalence: true
  rounding_tolerance: false
score_spacing_equivalence:
  enabled: true
  cpot_zero_spacing: true
forbidden_inferred_unit_equivalence:
  examples:
    - "3660 -> 3660 r/min"
""".strip(),
        encoding="utf-8",
    )
    return load_equivalence_rules(path)


def test_surface_units_are_equal_when_units_exist_on_both_sides(tmp_path):
    rules = _rules(tmp_path)

    assert evaluate_format_tolerant("转速：3220转/分", "转速:3220 r/min", rules)["exact"] is True
    assert evaluate_format_tolerant("流量：3.74L/分", "流量:3.74 L/min", rules)["exact"] is True
    assert evaluate_format_tolerant("50ML 0.4MG 200UG", "50ml 0.4mg 200μg", rules)["exact"] is True


def test_score_spacing_and_punctuation_are_equal_but_o_zero_is_not(tmp_path):
    rules = _rules(tmp_path)

    assert evaluate_format_tolerant("CPOT0分", "CPOT 0分", rules)["exact"] is True
    assert evaluate_format_tolerant("CPOT分", "CPOT0分", rules)["exact"] is False
    assert evaluate_format_tolerant("CPOTO分", "CPOT0分", rules)["exact"] is False


def test_forbidden_inferred_units_are_not_surface_equivalent(tmp_path):
    rules = _rules(tmp_path)

    assert evaluate_format_tolerant("3660", "3660 r/min", rules)["exact"] is False
    assert evaluate_format_tolerant("4.28", "4.28 L/min", rules)["exact"] is False
    assert evaluate_format_tolerant("50M", "50ml", rules)["exact"] is False
    assert evaluate_format_tolerant("45M", "45mg", rules)["exact"] is False
    assert evaluate_format_tolerant("45胍", "45mg", rules)["exact"] is False


def test_numeric_equivalence_is_strict_except_leading_zero(tmp_path):
    rules = _rules(tmp_path)

    assert evaluate_format_tolerant("APTT：03.40", "APTT:3.40", rules)["exact"] is True
    assert evaluate_format_tolerant("流量：3.741L/分", "流量:3.74L/min", rules)["exact"] is False
    assert evaluate_format_tolerant("50MG", "50ML", rules)["exact"] is False


def test_clinical_semantic_slots_treat_unit_surface_as_equal(tmp_path):
    rules = _rules(tmp_path)

    result = evaluate_clinical_semantic(
        "转速：3220转/分，流量：3.74L/分，CPOT0分，肝素钠7ml/h",
        "转速：3220r/min，流量：3.74L/min，CPOT 0分，肝素钠7mL/h",
        rules,
    )

    assert result["slot_f1"] == 1.0
    assert result["value_match_rate"] == 1.0
    assert result["unit_equivalent_rate"] == 1.0
    assert result["dangerous_slot_changes"] == []


def test_clinical_semantic_detects_dangerous_numeric_change(tmp_path):
    rules = _rules(tmp_path)

    result = evaluate_clinical_semantic("流量：3.74L/分", "流量：3.741L/min", rules)

    assert result["slot_f1"] == 1.0
    assert result["dangerous_slot_changes"][0]["slot"] == "流量"


def test_edit_reclassification_categories_and_effects(tmp_path):
    rules = _rules(tmp_path)

    assert classify_edit_effect("80m1/h", "80ml/h", "肠内营养液80ml/h", "肠内营养液80m1/h", rules)["final_category"] == "true_character_correction"
    assert classify_edit_effect("转/分", "r/min", "转速：3220转/分", "转速：3220转/分", rules)["final_category"] == "benign_format_normalization"
    assert classify_edit_effect("3660", "3660 r/min", "ECMO转速调整至3660", "ECMO转速调整至3660", rules)["final_category"] == "semantic_inference"
    assert classify_edit_effect("50M", "50ml", "50M", "50M", rules)["final_category"] == "risky_unit_substitution"
    assert classify_edit_effect("CPOT0分", "CPOT分", "CPOT0分", "CPOT0分", rules)["final_category"] == "harmful_deletion_or_insertion"
    assert classify_edit_effect("CPOTO分", "CPOT分", "CPOT0分", "CPOTO分", rules)["final_category"] == "harmful_deletion_or_insertion"
    assert classify_edit_effect("5mg|:1ml", "5mg:1ml", "5mg:1ml", "5mg|:1ml", rules)["final_category"] != "risky_unit_substitution"


def test_build_record_preserves_raw_reviewer_output(tmp_path):
    rules = _rules(tmp_path)
    evaluated = {
        "case_id": "c",
        "text_source": "raw_qwen",
        "reviewer_group": "llm",
        "gold": "CPOT0分",
        "original_text": "CPOT0分",
        "reviewed_text": "CPOT 0分",
        "review": {
            "edits": [{"from": "CPOT0分", "to": "CPOT 0分", "edit_type": "punctuation"}],
            "model_reviewed_text": "CPOT 0分",
        },
    }

    record = build_tolerant_eval_record(evaluated, rules)

    assert record["original_text"] == "CPOT0分"
    assert record["reviewed_text"] == "CPOT 0分"
    assert evaluated["review"]["model_reviewed_text"] == "CPOT 0分"
    assert record["format_tolerant"]["exact_after"] is True


def test_verify_hash_entries_reports_unchanged(tmp_path):
    path = tmp_path / "result.json"
    path.write_text(json.dumps({"x": 1}), encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    rows = verify_hash_entries([{"path": str(path), "expected_sha256": digest}])

    assert rows[0]["unchanged"] is True
