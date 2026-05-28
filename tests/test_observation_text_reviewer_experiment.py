from __future__ import annotations

import json

from icu_vllm.observation_text_reviewer_experiment import (
    apply_supported_edits,
    build_reviewer_prompt,
    evaluate_review_record,
    generate_regex_candidates,
    load_domain_lexicon,
    parse_reviewer_response,
    sanitize_reviewer_output,
)


def test_domain_lexicon_yaml_loads_categories(tmp_path):
    path = tmp_path / "domain_lexicon.yaml"
    path.write_text(
        """
units_and_measurements:
  - ml/h
  - L/min
icu_abbreviations:
  - CPOT
common_medical_phrases:
  - 遵医嘱
""".strip(),
        encoding="utf-8",
    )

    lexicon = load_domain_lexicon(path)

    assert lexicon["units_and_measurements"] == ["ml/h", "L/min"]
    assert lexicon["icu_abbreviations"] == ["CPOT"]
    assert lexicon["common_medical_phrases"] == ["遵医嘱"]


def test_reviewer_prompt_injects_lexicon_without_gold():
    lexicon = {"icu_abbreviations": ["CPOT"], "common_medical_phrases": ["遵医嘱"]}
    prompt = build_reviewer_prompt(
        original_text="CP0T0分，遵医嘱",
        reviewer_group="llm_reviewer_with_lexicon",
        domain_lexicon=lexicon,
        regex_candidates=[],
        gold="CPOT0分，遵医嘱",
    )

    assert "CPOT" in prompt
    assert "遵医嘱" in prompt
    assert "CP0T0分，遵医嘱" in prompt
    assert "CPOT0分，遵医嘱" not in prompt
    assert "gold" not in prompt.lower()


def test_parse_reviewer_json_and_preserve_original_text():
    raw = json.dumps(
        {
            "original_text": "CP0T0分",
            "reviewed_text": "CPOT0分",
            "edits": [
                {
                    "from": "CP0T",
                    "to": "CPOT",
                    "span_context": "CP0T0分",
                    "edit_type": "abbreviation",
                    "evidence": "CPOT 是 ICU 评分缩写，0 更像字母 O 的误识别",
                    "confidence": "high",
                    "should_auto_apply": True,
                }
            ],
            "uncertain_edits": [],
            "review_note": "局部缩写审查",
        },
        ensure_ascii=False,
    )

    parsed = parse_reviewer_response(raw)
    sanitized = sanitize_reviewer_output("CP0T0分", parsed)

    assert sanitized["original_text"] == "CP0T0分"
    assert sanitized["reviewed_text"] == "CPOT0分"
    assert sanitized["model_reviewed_text"] == "CPOT0分"
    assert sanitized["edits"][0]["evidence"]


def test_apply_supported_edits_keeps_reviewed_text_consistent():
    edits = [{"from": "80m1/h", "to": "80ml/h", "evidence": "单位候选", "confidence": "high"}]

    assert apply_supported_edits("肠内营养液80m1/h胃管泵入", edits) == "肠内营养液80ml/h胃管泵入"


def test_unsupported_edit_moves_to_uncertain_and_does_not_change_text():
    parsed = {
        "original_text": "80m1/h",
        "reviewed_text": "80ml/h",
        "edits": [{"from": "80m1/h", "to": "80ml/h", "confidence": "high"}],
        "uncertain_edits": [],
    }

    sanitized = sanitize_reviewer_output("80m1/h", parsed)

    assert sanitized["reviewed_text"] == "80m1/h"
    assert sanitized["edits"] == []
    assert sanitized["uncertain_edits"][0]["from"] == "80m1/h"


def test_regex_candidate_generator_only_marks_candidates():
    lexicon = {"icu_abbreviations": ["CPOT"], "common_medical_phrases": ["继续观察"]}

    candidates = generate_regex_candidates("CP0T0分，医嘱维观", lexicon)

    assert any(item["text"] == "CP0T" for item in candidates)
    assert any("继续观察" in item.get("candidates", []) for item in candidates)
    assert "reviewed_text" not in candidates[0]


def test_evaluate_review_record_counts_helpful_and_harmful_changes():
    helpful = evaluate_review_record(
        case_id="c",
        text_source="raw_qwen",
        reviewer_group="llm_reviewer_with_lexicon",
        gold="CPOT0分",
        original_text="CP0T0分",
        review={"reviewed_text": "CPOT0分", "edits": [{"from": "CP0T", "to": "CPOT", "confidence": "high", "edit_type": "abbreviation"}]},
    )
    harmful = evaluate_review_record(
        case_id="c",
        text_source="raw_qwen",
        reviewer_group="llm_reviewer_with_lexicon",
        gold="CPOT0分",
        original_text="CPOT0分",
        review={"reviewed_text": "CP0T0分", "edits": [{"from": "CPOT", "to": "CP0T", "confidence": "high", "edit_type": "abbreviation"}]},
    )

    assert helpful["corrected_wrong_to_right"] is True
    assert helpful["net_cer_delta"] < 0
    assert harmful["changed_right_to_wrong"] is True
    assert harmful["overcorrection"] is True
