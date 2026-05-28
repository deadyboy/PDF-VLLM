from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .observation_row_prompt_ablation import _levenshtein


TEXT_SOURCES = ("raw_ocr", "raw_qwen")
REVIEWER_GROUPS = (
    "llm_reviewer_no_lexicon",
    "llm_reviewer_with_lexicon",
    "regex_candidates_only",
    "regex_candidates_plus_llm_reviewer",
)
NUMERIC_UNIT_SLOTS = {"ECMO转速", "转速", "流量", "血流量", "流速", "给药速度", "APTT", "CPOT"}
MEDICATION_TERMS = ("肝素钠", "舒芬太尼", "咪达唑仑", "氯化钠注射液", "肠内营养液", "枸橼酸舒芬太尼")
DEVICE_TERMS = ("VV-ECMO", "CVVHDF", "ECMO")


def load_equivalence_rules(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        data = _default_rules()
    return data


def _default_rules() -> dict[str, Any]:
    return {
        "punctuation_equivalence": {"enabled": True, "cpot_score_optional_space": True},
        "unit_surface_equivalence": {
            "enabled": True,
            "units": {
                "r/min": ["转/分", "转/分钟", "r/min", "rpm"],
                "L/min": ["L/分", "L/min", "L/分钟"],
                "ml": ["ml", "mL", "ML"],
                "mg": ["mg", "MG"],
                "ug": ["ug", "UG", "μg"],
                "℃": ["℃", "°C"],
            },
        },
        "numeric_equivalence": {"enabled": True, "allow_leading_zero_equivalence": True, "rounding_tolerance": False},
        "score_spacing_equivalence": {"enabled": True, "cpot_zero_spacing": True, "o_zero_sensitivity": False},
    }


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def _unit_mapping(rules: dict[str, Any]) -> dict[str, str]:
    units = rules.get("unit_surface_equivalence", {}).get("units", {})
    mapping: dict[str, str] = {}
    if not rules.get("unit_surface_equivalence", {}).get("enabled", True):
        return mapping
    for canonical, variants in units.items():
        for variant in variants or []:
            mapping[str(variant)] = str(canonical)
    return mapping


def _normalize_number_leading_zero(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        number = match.group(0)
        if number.startswith("0") and len(number.split(".", 1)[0]) > 1:
            if "." in number:
                left, right = number.split(".", 1)
                return f"{int(left)}.{right}"
            return str(int(number))
        return number

    return re.sub(r"(?<![\d.])0+[1-9]\d*(?:\.\d+)?", repl, text)


def normalize_format_tolerant(value: Any, rules: dict[str, Any]) -> str:
    text = _as_text(value)
    if rules.get("punctuation_equivalence", {}).get("enabled", True):
        replacements = {
            "，": ",",
            "：": ":",
            "；": ";",
            "（": "(",
            "）": ")",
            "％": "%",
            "　": "",
            " ": "",
            "\t": "",
            "\r": "",
            "\n": "",
        }
        replacements.update(rules.get("punctuation_equivalence", {}).get("normalize", {}) or {})
        for source, target in replacements.items():
            text = text.replace(str(source), str(target))
    if rules.get("score_spacing_equivalence", {}).get("enabled", True):
        text = re.sub(r"CPOT\s+([0-9])分", r"CPOT\1分", text)
    mapping = _unit_mapping(rules)
    for variant, canonical in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        if not variant:
            continue
        text = text.replace(variant, canonical)
    if rules.get("numeric_equivalence", {}).get("enabled", True) and rules.get("numeric_equivalence", {}).get("allow_leading_zero_equivalence", True):
        text = _normalize_number_leading_zero(text)
    return text


def evaluate_format_tolerant(gold: Any, actual: Any, rules: dict[str, Any]) -> dict[str, Any]:
    norm_gold = normalize_format_tolerant(gold, rules)
    norm_actual = normalize_format_tolerant(actual, rules)
    distance = _levenshtein(norm_gold, norm_actual)
    return {
        "normalized_gold": norm_gold,
        "normalized_actual": norm_actual,
        "cer": _cer(distance, norm_gold),
        "exact": norm_gold == norm_actual,
        "edit_distance": distance,
    }


def _cer(distance: int, gold_text: str) -> float:
    return round(distance / max(1, len(gold_text)), 6)


def _canonical_unit(unit: str, rules: dict[str, Any]) -> str:
    unit = unit.strip()
    if not unit:
        return ""
    normalized = normalize_format_tolerant(unit, rules)
    return normalized


def _slot_key(slot: dict[str, Any]) -> tuple[str, str, str]:
    return str(slot.get("slot")), str(slot.get("value", "")), str(slot.get("unit", ""))


def _append_slot(slots: list[dict[str, Any]], slot: str, value: str = "", unit: str = "", surface: str = "", rules: dict[str, Any] | None = None) -> None:
    if rules is not None:
        unit = _canonical_unit(unit, rules)
    item = {"slot": slot, "value": value, "unit": unit, "surface": surface}
    if _slot_key(item) not in {_slot_key(existing) for existing in slots}:
        slots.append(item)


def extract_clinical_slots(text: Any, rules: dict[str, Any]) -> list[dict[str, Any]]:
    value = _as_text(text)
    slots: list[dict[str, Any]] = []
    for match in re.finditer(r"(?:ECMO)?转速(?:调整至|[:：])?\s*([0-9]+(?:\.\d+)?)(?:\s*(转/分|转/分钟|r/min|rpm))?", value):
        _append_slot(slots, "转速", match.group(1), match.group(2) or "", match.group(0), rules)
    for match in re.finditer(r"(流量|血流量|流速)[:：]?\s*([0-9]+(?:\.\d+)?)(?:\s*(L/分|L/min|L/分钟))?", value):
        _append_slot(slots, match.group(1), match.group(2), match.group(3) or "", match.group(0), rules)
    for match in re.finditer(r"([0-9]+(?:\.\d+)?)(ml/h|mL/h|ML/h)", value):
        _append_slot(slots, "给药速度", match.group(1), match.group(2), match.group(0), rules)
    for match in re.finditer(r"APTT[:：]?\s*([0-9]+(?:\.\d+)?)(?:\s*(s|秒))?", value, flags=re.IGNORECASE):
        _append_slot(slots, "APTT", match.group(1), match.group(2) or "", match.group(0), rules)
    for match in re.finditer(r"CPOT\s*([0-9])分", value):
        _append_slot(slots, "CPOT", match.group(1), "分", match.group(0), rules)
    for term in MEDICATION_TERMS:
        if term in value:
            _append_slot(slots, "药品/液体", term, "", term, rules)
    for term in DEVICE_TERMS:
        if term in value:
            _append_slot(slots, "设备缩写", term, "", term, rules)
    return slots


def _slot_sets(slots: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    return {_slot_key(slot) for slot in slots}


def _slot_name_value(slot: dict[str, Any]) -> tuple[str, str]:
    return str(slot.get("slot")), str(slot.get("value", ""))


def _dangerous_slot_changes(gold_slots: list[dict[str, Any]], actual_slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    gold_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actual_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slot in gold_slots:
        gold_by_name[str(slot.get("slot"))].append(slot)
    for slot in actual_slots:
        actual_by_name[str(slot.get("slot"))].append(slot)
    for name, gold_items in gold_by_name.items():
        for gold in gold_items:
            candidates = actual_by_name.get(name, [])
            if not candidates:
                continue
            if _slot_key(gold) in {_slot_key(item) for item in candidates}:
                continue
            same_value = [item for item in candidates if str(item.get("value")) == str(gold.get("value"))]
            if same_value:
                changes.append({"slot": name, "gold": gold, "actual": same_value[0], "reason": "unit_changed_or_added"})
            elif name in NUMERIC_UNIT_SLOTS:
                changes.append({"slot": name, "gold": gold, "actual": candidates[0], "reason": "numeric_value_changed"})
    return changes


def evaluate_clinical_semantic(gold: Any, actual: Any, rules: dict[str, Any]) -> dict[str, Any]:
    gold_slots = extract_clinical_slots(gold, rules)
    actual_slots = extract_clinical_slots(actual, rules)
    gold_set = {str(slot.get("slot")) for slot in gold_slots}
    actual_set = {str(slot.get("slot")) for slot in actual_slots}
    true_positive = len(gold_set & actual_set)
    precision = round(true_positive / max(1, len(actual_set)), 6)
    recall = round(true_positive / max(1, len(gold_set)), 6)
    f1 = round((2 * precision * recall / (precision + recall)), 6) if precision + recall else 0.0
    gold_name_values = {_slot_name_value(slot) for slot in gold_slots}
    actual_name_values = {_slot_name_value(slot) for slot in actual_slots}
    value_matches = len(gold_name_values & actual_name_values)
    value_match_rate = round(value_matches / max(1, len(gold_name_values)), 6)
    unit_equiv_matches = 0
    comparable_units = 0
    for gold_slot in gold_slots:
        if not gold_slot.get("unit"):
            continue
        for actual_slot in actual_slots:
            if _slot_name_value(gold_slot) == _slot_name_value(actual_slot):
                comparable_units += 1
                if str(gold_slot.get("unit")) == str(actual_slot.get("unit")):
                    unit_equiv_matches += 1
                break
    return {
        "gold_slots": gold_slots,
        "actual_slots": actual_slots,
        "slot_precision": precision,
        "slot_recall": recall,
        "slot_f1": f1,
        "value_match_rate": value_match_rate,
        "unit_equivalent_rate": round(unit_equiv_matches / max(1, comparable_units), 6),
        "dangerous_slot_changes": _dangerous_slot_changes(gold_slots, actual_slots),
    }


def _effect(before: int | float, after: int | float) -> str:
    if after < before:
        return "improve"
    if after > before:
        return "worsen"
    return "same"


def _apply_single_edit(original_text: str, source: str, target: str) -> str:
    return original_text.replace(source, target, 1) if source in original_text else original_text


def _digit_signature(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text)


def _looks_like_semantic_inference(source: str, target: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", source.strip()) and re.fullmatch(r"\d+(?:\.\d+)?\s*(?:r/min|L/min|ml/h|mL/h|ML/h)", target.strip()))


def _looks_risky_unit_substitution(source: str, target: str) -> bool:
    source_clean = source.strip()
    target_clean = target.strip()
    if re.fullmatch(r"\d+[Mm]", source_clean) and re.fullmatch(r"\d+(?:ml|mg|ug|mL|ML|MG|UG|μg)", target_clean):
        return True
    if re.search(r"\d+胍", source_clean) and re.search(r"\d+mg", target_clean, re.IGNORECASE):
        return True
    if re.fullmatch(r"\d+(?:mg|MG)", source_clean) and re.fullmatch(r"\d+(?:ml|mL|ML)", target_clean):
        return True
    if "uX" in source_clean and "ug" in target_clean:
        return True
    return False


def _punctuation_only(source: str, target: str, rules: dict[str, Any]) -> bool:
    return source != target and normalize_format_tolerant(source, rules) == normalize_format_tolerant(target, rules)


def classify_edit_effect(source: Any, target: Any, gold: Any, original_text: Any, rules: dict[str, Any]) -> dict[str, Any]:
    source_text = _as_text(source)
    target_text = _as_text(target)
    gold_text = _as_text(gold)
    original = _as_text(original_text)
    edited = _apply_single_edit(original, source_text, target_text)
    strict_before = _levenshtein(gold_text, original)
    strict_after = _levenshtein(gold_text, edited)
    tolerant_before = evaluate_format_tolerant(gold_text, original, rules)["edit_distance"]
    tolerant_after = evaluate_format_tolerant(gold_text, edited, rules)["edit_distance"]
    semantic_before = evaluate_clinical_semantic(gold_text, original, rules)["slot_f1"]
    semantic_after = evaluate_clinical_semantic(gold_text, edited, rules)["slot_f1"]
    strict_effect = _effect(strict_before, strict_after)
    tolerant_effect = _effect(tolerant_before, tolerant_after)
    semantic_effect = _effect(-semantic_before, -semantic_after)

    if re.search(r"CPOT[O0]分", source_text) and re.search(r"CPOT分", target_text):
        final_category = "harmful_deletion_or_insertion"
        reason = "CPOT score marker was removed or made ambiguous"
    elif re.search(r"\dm1/h", source_text, flags=re.IGNORECASE) and re.search(r"\dml/h", target_text, flags=re.IGNORECASE):
        final_category = "true_character_correction"
        reason = "m1/h was corrected to the explicit ml/h unit form"
    elif _looks_risky_unit_substitution(source_text, target_text):
        final_category = "risky_unit_substitution"
        reason = "incomplete or mismatched unit type was converted to a concrete unit"
    elif _looks_like_semantic_inference(source_text, target_text):
        final_category = "semantic_inference"
        reason = "unit was inferred from context rather than surface-equivalent text"
    elif _digit_signature(source_text) != _digit_signature(target_text):
        final_category = "harmful_deletion_or_insertion"
        reason = "digit sequence changed"
    elif _punctuation_only(source_text, target_text, rules):
        if re.sub(r"[\s,，:：;；()（）]", "", source_text) == re.sub(r"[\s,，:：;；()（）]", "", target_text):
            final_category = "punctuation_only"
            reason = "only punctuation or spacing changed"
        else:
            final_category = "benign_format_normalization"
            reason = "surface format changed but tolerant normalization is equal"
    elif strict_effect == "improve" and tolerant_effect in {"improve", "same"}:
        final_category = "true_character_correction"
        reason = "edit moves text closer to gold without tolerant degradation"
    elif strict_effect == "worsen" or tolerant_effect == "worsen":
        final_category = "harmful_deletion_or_insertion"
        reason = "edit worsens strict or tolerant distance"
    else:
        final_category = "benign_format_normalization"
        reason = "no dangerous surface change detected"

    return {
        "from": source_text,
        "to": target_text,
        "final_category": final_category,
        "strict_effect": strict_effect,
        "tolerant_effect": tolerant_effect,
        "semantic_effect": semantic_effect,
        "reason": reason,
    }


def _strict_metric(gold: str, actual: str) -> dict[str, Any]:
    distance = _levenshtein(gold, actual)
    return {"cer": _cer(distance, gold), "exact": gold == actual, "edit_distance": distance}


def build_tolerant_eval_record(evaluated_row: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    gold = _as_text(evaluated_row.get("gold"))
    original = _as_text(evaluated_row.get("original_text"))
    reviewed = _as_text(evaluated_row.get("reviewed_text"))
    strict_before = _strict_metric(gold, original)
    strict_after = _strict_metric(gold, reviewed)
    tolerant_before = evaluate_format_tolerant(gold, original, rules)
    tolerant_after = evaluate_format_tolerant(gold, reviewed, rules)
    semantic_before = evaluate_clinical_semantic(gold, original, rules)
    semantic_after = evaluate_clinical_semantic(gold, reviewed, rules)
    edits = evaluated_row.get("review", {}).get("edits", []) if isinstance(evaluated_row.get("review"), dict) else []
    reclassified = []
    for edit in edits if isinstance(edits, list) else []:
        if not isinstance(edit, dict):
            continue
        item = classify_edit_effect(edit.get("from"), edit.get("to"), gold, original, rules)
        item["original_edit_type"] = edit.get("edit_type", "")
        reclassified.append(item)
    return {
        "case_id": evaluated_row.get("case_id"),
        "text_source": evaluated_row.get("text_source"),
        "reviewer_group": evaluated_row.get("reviewer_group"),
        "gold": gold,
        "original_text": original,
        "reviewed_text": reviewed,
        "strict": {
            "cer_before": strict_before["cer"],
            "cer_after": strict_after["cer"],
            "exact_before": strict_before["exact"],
            "exact_after": strict_after["exact"],
            "delta": round(strict_after["cer"] - strict_before["cer"], 6),
            "edit_distance_before": strict_before["edit_distance"],
            "edit_distance_after": strict_after["edit_distance"],
        },
        "format_tolerant": {
            "normalized_gold": tolerant_before["normalized_gold"],
            "normalized_original": tolerant_before["normalized_actual"],
            "normalized_reviewed": tolerant_after["normalized_actual"],
            "cer_before": tolerant_before["cer"],
            "cer_after": tolerant_after["cer"],
            "exact_before": tolerant_before["exact"],
            "exact_after": tolerant_after["exact"],
            "delta": round(tolerant_after["cer"] - tolerant_before["cer"], 6),
            "edit_distance_before": tolerant_before["edit_distance"],
            "edit_distance_after": tolerant_after["edit_distance"],
        },
        "clinical_semantic": {
            "gold_slots": semantic_before["gold_slots"],
            "original_slots": semantic_before["actual_slots"],
            "reviewed_slots": semantic_after["actual_slots"],
            "slot_precision_before": semantic_before["slot_precision"],
            "slot_precision_after": semantic_after["slot_precision"],
            "slot_recall_before": semantic_before["slot_recall"],
            "slot_recall_after": semantic_after["slot_recall"],
            "slot_f1_before": semantic_before["slot_f1"],
            "slot_f1_after": semantic_after["slot_f1"],
            "value_match_rate_before": semantic_before["value_match_rate"],
            "value_match_rate_after": semantic_after["value_match_rate"],
            "unit_equivalent_rate_before": semantic_before["unit_equivalent_rate"],
            "unit_equivalent_rate_after": semantic_after["unit_equivalent_rate"],
            "dangerous_slot_changes_before": semantic_before["dangerous_slot_changes"],
            "dangerous_slot_changes": semantic_after["dangerous_slot_changes"],
        },
        "edit_reclassification": reclassified,
    }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    categories = Counter()
    strict_worse_but_tolerant_same = 0
    strict_worse_but_tolerant_better = 0
    strict_worse_and_tolerant_worse = 0
    for record in records:
        key = (str(record["text_source"]), str(record["reviewer_group"]))
        item = grouped.setdefault(
            key,
            {
                "text_source": key[0],
                "reviewer_group": key[1],
                "total": 0,
                "strict_cer_before_total": 0.0,
                "strict_cer_after_total": 0.0,
                "tolerant_cer_before_total": 0.0,
                "tolerant_cer_after_total": 0.0,
                "strict_exact_before": 0,
                "strict_exact_after": 0,
                "tolerant_exact_before": 0,
                "tolerant_exact_after": 0,
                "slot_precision_before_total": 0.0,
                "slot_precision_after_total": 0.0,
                "slot_recall_before_total": 0.0,
                "slot_recall_after_total": 0.0,
                "slot_f1_before_total": 0.0,
                "slot_f1_after_total": 0.0,
                "value_match_rate_before_total": 0.0,
                "value_match_rate_after_total": 0.0,
                "unit_equivalent_rate_before_total": 0.0,
                "unit_equivalent_rate_after_total": 0.0,
                "dangerous_slot_change_count": 0,
                "strict_worse_but_tolerant_same_count": 0,
                "strict_worse_but_tolerant_better_count": 0,
                "strict_worse_and_tolerant_worse_count": 0,
            },
        )
        item["total"] += 1
        for prefix, metric in (("strict", "strict"), ("tolerant", "format_tolerant")):
            item[f"{prefix}_cer_before_total"] += float(record[metric]["cer_before"])
            item[f"{prefix}_cer_after_total"] += float(record[metric]["cer_after"])
            item[f"{prefix}_exact_before"] += int(record[metric]["exact_before"])
            item[f"{prefix}_exact_after"] += int(record[metric]["exact_after"])
        semantic = record["clinical_semantic"]
        for name in ("slot_precision", "slot_recall", "slot_f1", "value_match_rate", "unit_equivalent_rate"):
            item[f"{name}_before_total"] += float(semantic[f"{name}_before"])
            item[f"{name}_after_total"] += float(semantic[f"{name}_after"])
        item["dangerous_slot_change_count"] += len(semantic.get("dangerous_slot_changes", []))
        strict_delta = float(record["strict"]["delta"])
        tolerant_delta = float(record["format_tolerant"]["delta"])
        if strict_delta > 0 and tolerant_delta == 0:
            item["strict_worse_but_tolerant_same_count"] += 1
            strict_worse_but_tolerant_same += 1
        elif strict_delta > 0 and tolerant_delta < 0:
            item["strict_worse_but_tolerant_better_count"] += 1
            strict_worse_but_tolerant_better += 1
        elif strict_delta > 0 and tolerant_delta > 0:
            item["strict_worse_and_tolerant_worse_count"] += 1
            strict_worse_and_tolerant_worse += 1
        for edit in record.get("edit_reclassification", []):
            categories[str(edit.get("final_category"))] += 1
    by_group = []
    for item in grouped.values():
        total = max(1, int(item["total"]))
        for key in list(item):
            if key.endswith("_total"):
                item[key[:-6]] = round(float(item[key]) / total, 6)
        by_group.append(item)
    by_group.sort(key=lambda row: (row["text_source"], row["reviewer_group"]))
    return {
        "by_source_group": by_group,
        "edit_effect_category_counts": dict(categories),
        "strict_worse_but_tolerant_same_count": strict_worse_but_tolerant_same,
        "strict_worse_but_tolerant_better_count": strict_worse_but_tolerant_better,
        "strict_worse_and_tolerant_worse_count": strict_worse_and_tolerant_worse,
        "total": len(records),
    }


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_hash_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entry in entries:
        path = Path(entry.get("path", ""))
        current = _hash_file(path) if path.exists() else ""
        expected = entry.get("expected_sha256") or entry.get("current_sha256") or entry.get("after") or entry.get("before") or entry.get("sha256") or ""
        rows.append({**entry, "current_sha256": current, "expected_sha256": expected, "unchanged": bool(expected and current == expected)})
    return rows


def _md(value: Any, limit: int = 220) -> str:
    text = "null" if value is None else str(value)
    text = text.replace("\n", "<br>").replace("|", "\\|")
    return text if len(text) <= limit else text[:limit] + "..."


def _label_source(value: str) -> str:
    return {"raw_ocr": "原始OCR文本", "raw_qwen": "原始Qwen文本"}.get(value, value)


def _label_group(value: str) -> str:
    return {
        "llm_reviewer_no_lexicon": "LLM审查-无词表",
        "llm_reviewer_with_lexicon": "LLM审查-带词表",
        "regex_candidates_only": "仅候选检测",
        "regex_candidates_plus_llm_reviewer": "候选+LLM审查",
    }.get(value, value)


def build_report(records: list[dict[str, Any]], summary: dict[str, Any], metadata: dict[str, Any]) -> str:
    lines = [
        "# 病情观察及处理 reviewer 宽容评估实验",
        "",
        "## 实验目的",
        "",
        "本轮只重算评估指标，不重跑 OCR、Qwen 或 reviewer。目标是区分 strict transcription、format-tolerant equivalence、clinical semantic equivalence，以及 unsafe inference / risky substitution。",
        "",
        "## 输入",
        "",
        f"- reviewer run：`{metadata.get('reviewer_run_dir')}`",
        f"- evaluated JSONL：`{metadata.get('evaluated_jsonl')}`",
        f"- equivalence config：`{metadata.get('equivalence_config')}`",
        f"- 记录数：{summary['total']}",
        "",
        "## strict metric 总表",
        "",
        "| 文本来源 | reviewer组 | 样本数 | strict_CER_before | strict_CER_after | strict_exact_before | strict_exact_after |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["by_source_group"]:
        lines.append(
            f"| {_label_source(row['text_source'])} | {_label_group(row['reviewer_group'])} | {row['total']} | "
            f"{row['strict_cer_before']:.4f} | {row['strict_cer_after']:.4f} | {row['strict_exact_before']} | {row['strict_exact_after']} |"
        )
    lines.extend(
        [
            "",
            "## format-tolerant metric 总表",
            "",
            "| 文本来源 | reviewer组 | tolerant_CER_before | tolerant_CER_after | tolerant_exact_before | tolerant_exact_after | strict变差但tolerant不变 | strict变差但tolerant变好 | strict/tolerant都变差 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["by_source_group"]:
        lines.append(
            f"| {_label_source(row['text_source'])} | {_label_group(row['reviewer_group'])} | "
            f"{row['tolerant_cer_before']:.4f} | {row['tolerant_cer_after']:.4f} | "
            f"{row['tolerant_exact_before']} | {row['tolerant_exact_after']} | "
            f"{row['strict_worse_but_tolerant_same_count']} | {row['strict_worse_but_tolerant_better_count']} | {row['strict_worse_and_tolerant_worse_count']} |"
        )
    lines.extend(
        [
            "",
            "## clinical semantic metric 总表",
            "",
            "| 文本来源 | reviewer组 | slot_f1_before | slot_f1_after | value_match_before | value_match_after | unit_equiv_before | unit_equiv_after | dangerous_slot_change_count |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["by_source_group"]:
        lines.append(
            f"| {_label_source(row['text_source'])} | {_label_group(row['reviewer_group'])} | "
            f"{row['slot_f1_before']:.4f} | {row['slot_f1_after']:.4f} | "
            f"{row['value_match_rate_before']:.4f} | {row['value_match_rate_after']:.4f} | "
            f"{row['unit_equivalent_rate_before']:.4f} | {row['unit_equivalent_rate_after']:.4f} | "
            f"{row['dangerous_slot_change_count']} |"
        )
    lines.extend(["", "## edit_effect_category 统计", "", "| category | count |", "|---|---:|"])
    for category, count in sorted(summary["edit_effect_category_counts"].items()):
        lines.append(f"| {category} | {count} |")
    _append_example_section(lines, "strict CER 变差但 tolerant 不变的例子", [r for r in records if r["strict"]["delta"] > 0 and r["format_tolerant"]["delta"] == 0])
    _append_example_section(lines, "strict CER 变差但 semantic slot 不变的例子", [r for r in records if r["strict"]["delta"] > 0 and r["clinical_semantic"]["slot_f1_after"] == r["clinical_semantic"]["slot_f1_before"]])
    _append_example_section(lines, "strict 和 tolerant 都变差的真实失败例子", [r for r in records if r["strict"]["delta"] > 0 and r["format_tolerant"]["delta"] > 0])
    _append_edit_section(lines, "semantic_inference 例子", records, "semantic_inference")
    _append_edit_section(lines, "risky_unit_substitution 例子", records, "risky_unit_substitution")
    lines.extend(
        [
            "",
            "## 结论",
            "",
            "- strict transcription 仍然必须保留，因为 reviewer 会做单位和书写规范化，严格逐字任务下这些会被判错。",
            "- format-tolerant metric 可以把 `转/分/r/min`、`L/分/L/min`、`CPOT0分/CPOT 0分`、`ML/mL/ml`、`UG/μg/ug` 归为表面等价。",
            "- 但 `3660 -> 3660 r/min`、`4.28 -> 4.28 L/min` 属于 semantic_inference，不是表面等价。",
            "- `50M -> 50ml`、`45M -> 45mg`、`MG/ML` 类型互换属于 risky_unit_substitution，必须禁止自动覆盖。",
            "- reviewer 若进入系统，只适合先作为 QC suggestion / semantic normalization 辅助，不适合作为 raw transcription 覆盖来源。",
        ]
    )
    return "\n".join(lines) + "\n"


def _append_example_section(lines: list[str], title: str, rows: list[dict[str, Any]]) -> None:
    lines.extend(["", f"## {title}", "", "| case | 来源 | reviewer组 | gold | original_text | reviewed_text | strict_delta | tolerant_delta |", "|---|---|---|---|---|---|---:|---:|"])
    for row in rows[:12]:
        lines.append(
            f"| {row['case_id']} | {_label_source(row['text_source'])} | {_label_group(row['reviewer_group'])} | "
            f"{_md(row['gold'])} | {_md(row['original_text'])} | {_md(row['reviewed_text'])} | "
            f"{row['strict']['delta']:.4f} | {row['format_tolerant']['delta']:.4f} |"
        )


def _append_edit_section(lines: list[str], title: str, rows: list[dict[str, Any]], category: str) -> None:
    lines.extend(["", f"## {title}", "", "| case | 来源 | reviewer组 | from | to | strict_effect | tolerant_effect | semantic_effect | reason |", "|---|---|---|---|---|---|---|---|---|"])
    count = 0
    for row in rows:
        for edit in row.get("edit_reclassification", []):
            if edit.get("final_category") != category:
                continue
            lines.append(
                f"| {row['case_id']} | {_label_source(row['text_source'])} | {_label_group(row['reviewer_group'])} | "
                f"{_md(edit.get('from'), 80)} | {_md(edit.get('to'), 80)} | {edit.get('strict_effect')} | "
                f"{edit.get('tolerant_effect')} | {edit.get('semantic_effect')} | {_md(edit.get('reason'), 120)} |"
            )
            count += 1
            if count >= 16:
                return


def run_eval(args: argparse.Namespace) -> None:
    rules = load_equivalence_rules(args.equivalence_config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluated_rows = read_jsonl(args.evaluated_jsonl)
    records = [build_tolerant_eval_record(row, rules) for row in evaluated_rows]
    summary = summarize_records(records)
    reviewer_summary_path = Path(args.reviewer_run_dir) / "observation_text_reviewer_summary.json"
    reviewer_summary = json.loads(reviewer_summary_path.read_text(encoding="utf-8")) if reviewer_summary_path.exists() else {}
    source_metadata = reviewer_summary.get("metadata", {})
    main_hashes = verify_hash_entries(source_metadata.get("main_result_hashes", []))
    enhanced_hashes = verify_hash_entries(source_metadata.get("result_enhanced_hashes", []))
    metadata = {
        "reviewer_run_dir": str(args.reviewer_run_dir),
        "records_jsonl": str(args.records_jsonl),
        "evaluated_jsonl": str(args.evaluated_jsonl),
        "equivalence_config": str(args.equivalence_config),
        "rules_summary": _rules_summary(rules),
        "main_result_hashes": main_hashes,
        "result_enhanced_hashes": enhanced_hashes,
    }
    write_jsonl(output_dir / "observation_text_reviewer_tolerant_eval_records.jsonl", records)
    write_json(output_dir / "observation_text_reviewer_tolerant_eval_summary.json", {"metadata": metadata, "summary": summary, "rows": records})
    (output_dir / "observation_text_reviewer_tolerant_eval_report.md").write_text(build_report(records, summary, metadata), encoding="utf-8")


def _rules_summary(rules: dict[str, Any]) -> dict[str, Any]:
    return {
        "punctuation_equivalence": bool(rules.get("punctuation_equivalence", {}).get("enabled", True)),
        "unit_canonicals": sorted((rules.get("unit_surface_equivalence", {}).get("units", {}) or {}).keys()),
        "rounding_tolerance": bool(rules.get("numeric_equivalence", {}).get("rounding_tolerance", False)),
        "o_zero_sensitivity": bool(rules.get("score_spacing_equivalence", {}).get("o_zero_sensitivity", False)),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline tolerant evaluation for observation text reviewer outputs.")
    parser.add_argument("--reviewer-run-dir", required=True)
    parser.add_argument("--records-jsonl", required=True)
    parser.add_argument("--evaluated-jsonl", required=True)
    parser.add_argument("--equivalence-config", default="config/clinical_equivalence_rules.yaml")
    parser.add_argument("--output-dir", default="")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    if not args.output_dir:
        args.output_dir = str(Path(args.reviewer_run_dir).parent / f"observation_text_reviewer_tolerant_eval_{time.strftime('%Y%m%d-%H%M%S')}")
    run_eval(args)


if __name__ == "__main__":
    main()
