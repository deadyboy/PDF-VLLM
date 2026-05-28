from __future__ import annotations

import re
from typing import Any

from .target_column_vlm import classify_diff, normalize_text_for_eval


REPORT_CORRECT_KINDS = {
    "equal",
    "canonical_equal",
    "unit_case_equal",
    "manufacturer_punctuation_equal",
    "gold_needs_check",
}


def _unit_case_canonical(value: Any) -> str | None:
    text = normalize_text_for_eval(value)
    if text is None:
        return None

    def lower_unit(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2).lower()}"

    return re.sub(r"(\d(?:\.\d+)?)(ML|mL|ml|MG|mg|UG|ug)(?=[A-Za-z+\-;),，。:]|$)", lower_unit, text)


def _strip_manufacturer_punctuation(value: Any) -> str | None:
    text = normalize_text_for_eval(value)
    if text is None:
        return None

    def clean_parenthetical(match: re.Match[str]) -> str:
        inner = match.group(1)
        inner = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z]),(?=-?\d)", "", inner)
        inner = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z]),(?=[\u4e00-\u9fffA-Za-z])", "", inner)
        inner = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z])-+(?=\d)", "", inner)
        return f"({inner})"

    return re.sub(r"\(([^()]*)\)", clean_parenthetical, text)


def _gold_m1_to_ml(value: Any) -> str | None:
    text = normalize_text_for_eval(value)
    if text is None:
        return None
    return re.sub(r"(?<=\d)m1(?=[+;),，。:]|$)", "ml", text)


def classify_iv_diff(gold: Any, actual: Any) -> dict[str, Any]:
    base = classify_diff(gold, actual)
    if base["kind"] in {"equal", "canonical_equal", "missing", "overfill", "separator_error"}:
        return base

    unit_gold = _unit_case_canonical(gold)
    unit_actual = _unit_case_canonical(actual)
    if unit_gold is not None and unit_gold == unit_actual:
        return {**base, "kind": "unit_case_equal", "gold_iv_norm": unit_gold, "actual_iv_norm": unit_actual}

    mfg_gold = _strip_manufacturer_punctuation(gold)
    mfg_actual = _strip_manufacturer_punctuation(actual)
    if mfg_gold is not None and mfg_gold == mfg_actual:
        return {
            **base,
            "kind": "manufacturer_punctuation_equal",
            "gold_iv_norm": mfg_gold,
            "actual_iv_norm": mfg_actual,
        }

    gold_checked = _gold_m1_to_ml(gold)
    actual_norm = normalize_text_for_eval(actual)
    if gold_checked is not None and gold_checked == actual_norm and gold_checked != base["gold_norm"]:
        return {
            **base,
            "kind": "gold_needs_check",
            "gold_iv_norm": gold_checked,
            "actual_iv_norm": actual_norm,
        }

    if base["kind"] == "substantive_mismatch":
        return {**base, "kind": "true_char_mismatch"}
    return base


def is_report_correct(kind: str) -> bool:
    return kind in REPORT_CORRECT_KINDS
