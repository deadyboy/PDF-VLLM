from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from .config import PipelineConfig, load_config
from .json_utils import parse_model_json
from .observation_header_row_probe import combine_row_texts, read_json, sha256_file
from .observation_recognition_bottleneck_probe import IMAGE_VARIANT_LABELS
from .observation_row_prompt_ablation import _levenshtein, classify_raw_text_diff


OBS_FIELD = "病情观察及处理"
DEFAULT_INPUT_VERSION = "row_only_canvas_h64"
DEFAULT_QWEN_METHOD = "Qwen3-32B:precise_transcription_prompt"
DEFAULT_OCR_METHOD = "PaddleOCR:rec_only"
REVIEWER_GROUPS = (
    "llm_reviewer_no_lexicon",
    "llm_reviewer_with_lexicon",
    "regex_candidates_only",
    "regex_candidates_plus_llm_reviewer",
)
EDIT_TYPES = {"unit", "medical_phrase", "abbreviation", "drug_or_product", "punctuation", "number", "other"}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def load_domain_lexicon(path: str | Path) -> dict[str, list[str]]:
    path = Path(path)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {str(key): [str(item) for item in value or []] for key, value in data.items()}
    except Exception:
        result: dict[str, list[str]] = {}
        current_key: str | None = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if not line.startswith(" ") and line.endswith(":"):
                current_key = line[:-1].strip()
                result.setdefault(current_key, [])
                continue
            stripped = line.strip()
            if current_key and stripped.startswith("- "):
                result[current_key].append(stripped[2:].strip().strip('"').strip("'"))
        return result


def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def _flatten_lexicon(domain_lexicon: dict[str, list[str]]) -> list[str]:
    values: list[str] = []
    for items in domain_lexicon.values():
        values.extend(str(item) for item in items)
    return values


def _lexicon_for_prompt(domain_lexicon: dict[str, list[str]]) -> str:
    lines: list[str] = []
    for category, items in domain_lexicon.items():
        lines.append(f"{category}:")
        for item in items:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _brief_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_reviewer_prompt(
    *,
    original_text: str,
    reviewer_group: str,
    domain_lexicon: dict[str, list[str]] | None = None,
    regex_candidates: list[dict[str, Any]] | None = None,
    gold: str | None = None,
) -> str:
    del gold  # Gold is deliberately excluded from reviewer prompts.
    sections = [
        "你是一名 ICU 护理记录文本审查模型。",
        "",
        "任务：只审查 original_text 中疑似局部字符级错误、单位格式错误、医学短语错误或标点问题。",
        "你可以提出局部修正建议，但不能总结、扩写、改写整句，也不能补写原文没有的信息。",
        "如果证据不足，不要修改 reviewed_text，只把片段放入 uncertain_edits。",
        "药品剂量、数字、单位、设备参数属于高风险内容；除非证据非常强，不要 high confidence。",
        "领域词表只是弱参考，不代表文本中一定应该出现。",
        "",
        "original_text:",
        original_text,
    ]
    if reviewer_group in {"llm_reviewer_with_lexicon", "regex_candidates_plus_llm_reviewer"} and domain_lexicon:
        sections.extend(["", "domain_lexicon:", _lexicon_for_prompt(domain_lexicon)])
    if reviewer_group == "regex_candidates_plus_llm_reviewer":
        sections.extend(["", "regex_candidates:", _brief_json(regex_candidates or [])])
    sections.extend(
        [
            "",
            "输出要求：只输出 JSON，不要输出 Markdown，不要输出额外解释。",
            "JSON 格式：",
            _brief_json(
                {
                    "original_text": original_text,
                    "reviewed_text": original_text,
                    "edits": [
                        {
                            "from": "...",
                            "to": "...",
                            "span_context": "...",
                            "edit_type": "unit|medical_phrase|abbreviation|drug_or_product|punctuation|number|other",
                            "evidence": "为什么建议修改",
                            "confidence": "high|medium|low",
                            "should_auto_apply": True,
                        }
                    ],
                    "uncertain_edits": [
                        {
                            "from": "...",
                            "candidates": ["...", "..."],
                            "reason": "证据不足的原因",
                            "confidence": "low|medium",
                        }
                    ],
                    "review_note": "一句话总结",
                }
            ),
        ]
    )
    return "\n".join(sections)


def parse_reviewer_response(raw: str) -> dict[str, Any]:
    try:
        data = parse_model_json(raw)
        if not isinstance(data, dict):
            raise ValueError("reviewer output is not a JSON object")
        data.setdefault("edits", [])
        data.setdefault("uncertain_edits", [])
        data.setdefault("review_note", "")
        return {"parse_error": "", **data}
    except Exception as exc:
        return {
            "original_text": "",
            "reviewed_text": "",
            "edits": [],
            "uncertain_edits": [],
            "review_note": "",
            "parse_error": repr(exc),
        }


def _candidate_fragments(term: str) -> Iterable[str]:
    cleaned = term.strip()
    if len(cleaned) <= 1:
        return []
    fragments = {cleaned}
    for size in range(2, min(5, len(cleaned)) + 1):
        for idx in range(0, len(cleaned) - size + 1):
            fragments.add(cleaned[idx : idx + size])
    return sorted(fragments, key=len, reverse=True)


def _window_candidates(text: str, target: str, max_distance: int) -> list[str]:
    result: list[str] = []
    size = len(target)
    if size == 0 or len(text) < size:
        return result
    for idx in range(0, len(text) - size + 1):
        window = text[idx : idx + size]
        if window == target:
            continue
        if _levenshtein(window, target) <= max_distance:
            result.append(window)
    return result


def generate_regex_candidates(original_text: str, domain_lexicon: dict[str, list[str]]) -> list[dict[str, Any]]:
    text = _to_text(original_text)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(text_span: str, edit_type: str, reason: str, values: list[str]) -> None:
        key = (text_span, edit_type)
        if not text_span or key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "text": text_span,
                "edit_type": edit_type,
                "reason": reason,
                "candidates": values[:5],
            }
        )

    for match in re.finditer(r"\d+(?:m1|M1|rn|RN|0G|0g)(?:/[A-Za-z]+)?", text):
        span = match.group(0)
        values = [span.replace("m1", "ml").replace("M1", "ML").replace("rn", "m").replace("RN", "M").replace("0G", "UG").replace("0g", "ug")]
        add(span, "unit", "异常单位或英数混排形态", values)

    for match in re.finditer(r"C[Pp][0O]T|CP[0O]T|CPO10|CP0T", text):
        add(match.group(0), "abbreviation", "ICU 评分缩写疑似近形字符", ["CPOT"])

    for term in _flatten_lexicon(domain_lexicon):
        if len(term) < 2 or term in text:
            continue
        for fragment in _candidate_fragments(term):
            max_distance = 1 if len(fragment) <= 4 else 2
            for window in _window_candidates(text, fragment, max_distance):
                if len(window) < 2:
                    continue
                edit_type = "medical_phrase"
                if term.upper() == term and re.search(r"[A-Z]", term):
                    edit_type = "abbreviation"
                elif term in domain_lexicon.get("medications_and_fluids", []):
                    edit_type = "drug_or_product"
                add(window, edit_type, f"与领域词 `{term}` 的局部片段 `{fragment}` 形近", [term])
                break
    return candidates


def _supported_edit(edit: dict[str, Any], original_text: str) -> tuple[bool, str]:
    source = _to_text(edit.get("from"))
    target = _to_text(edit.get("to"))
    evidence = _to_text(edit.get("evidence")).strip()
    confidence = _to_text(edit.get("confidence")).strip().lower()
    edit_type = _to_text(edit.get("edit_type") or "other")
    if not source or not target:
        return False, "missing_from_or_to"
    if source not in original_text:
        return False, "source_span_not_found"
    if not evidence:
        return False, "missing_evidence"
    if edit_type not in EDIT_TYPES:
        return False, "invalid_edit_type"
    if CONFIDENCE_ORDER.get(confidence, -1) < CONFIDENCE_ORDER["medium"]:
        return False, "low_confidence"
    if edit.get("should_auto_apply") is False:
        return False, "should_auto_apply_false"
    if len(source) > 40 or abs(len(target) - len(source)) > 12:
        return False, "edit_too_large_for_local_review"
    return True, ""


def apply_supported_edits(original_text: str, edits: list[dict[str, Any]]) -> str:
    reviewed = original_text
    for edit in edits:
        source = _to_text(edit.get("from"))
        target = _to_text(edit.get("to"))
        if source and source in reviewed:
            reviewed = reviewed.replace(source, target, 1)
    return reviewed


def sanitize_reviewer_output(original_text: str, parsed: dict[str, Any]) -> dict[str, Any]:
    original_text = _to_text(original_text)
    supported: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    for raw_edit in parsed.get("edits", []) if isinstance(parsed.get("edits"), list) else []:
        if not isinstance(raw_edit, dict):
            continue
        ok, reason = _supported_edit(raw_edit, original_text)
        if ok:
            supported.append(raw_edit)
        else:
            uncertain.append(
                {
                    "from": raw_edit.get("from"),
                    "candidates": [raw_edit.get("to")] if raw_edit.get("to") else [],
                    "reason": reason,
                    "confidence": raw_edit.get("confidence", "low"),
                }
            )
    for item in parsed.get("uncertain_edits", []) if isinstance(parsed.get("uncertain_edits"), list) else []:
        if isinstance(item, dict):
            uncertain.append(item)
    reviewed_text = apply_supported_edits(original_text, supported)
    return {
        "original_text": original_text,
        "reviewed_text": reviewed_text,
        "model_reviewed_text": _to_text(parsed.get("reviewed_text")),
        "edits": supported,
        "uncertain_edits": uncertain,
        "review_note": _to_text(parsed.get("review_note")),
        "parse_error": _to_text(parsed.get("parse_error")),
        "reviewed_text_matches_supported_edits": reviewed_text == apply_supported_edits(original_text, supported),
    }


def _regex_only_review(original_text: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "original_text": original_text,
        "reviewed_text": original_text,
        "model_reviewed_text": original_text,
        "edits": [],
        "uncertain_edits": [
            {
                "from": item.get("text"),
                "candidates": item.get("candidates", []),
                "reason": item.get("reason", ""),
                "confidence": "low",
                "edit_type": item.get("edit_type", "other"),
            }
            for item in candidates
        ],
        "review_note": "regex candidate only; no text changed",
        "parse_error": "",
        "reviewed_text_matches_supported_edits": True,
    }


def _cer(distance: int, gold: str) -> float:
    return round(distance / max(1, len(gold)), 6)


def _edit_help_counts(gold: str, original_text: str, edits: list[dict[str, Any]]) -> dict[str, int]:
    before = _levenshtein(gold, original_text)
    counts = {"helpful": 0, "harmful": 0, "neutral": 0, "high_helpful": 0, "high_total": 0, "medium_low_helpful": 0, "medium_low_total": 0}
    for edit in edits:
        candidate_text = apply_supported_edits(original_text, [edit])
        after = _levenshtein(gold, candidate_text)
        confidence = _to_text(edit.get("confidence")).lower()
        is_high = confidence == "high"
        if is_high:
            counts["high_total"] += 1
        else:
            counts["medium_low_total"] += 1
        if after < before:
            counts["helpful"] += 1
            counts["high_helpful" if is_high else "medium_low_helpful"] += 1
        elif after > before:
            counts["harmful"] += 1
        else:
            counts["neutral"] += 1
    return counts


def evaluate_review_record(
    *,
    case_id: str,
    text_source: str,
    reviewer_group: str,
    gold: Any,
    original_text: Any,
    review: dict[str, Any],
) -> dict[str, Any]:
    gold_text = _to_text(gold)
    original = _to_text(original_text)
    reviewed = _to_text(review.get("reviewed_text"))
    before = classify_raw_text_diff(gold_text, original)
    after = classify_raw_text_diff(gold_text, reviewed)
    before_distance = int(before["edit_distance"])
    after_distance = int(after["edit_distance"])
    edit_counts = _edit_help_counts(gold_text, original, review.get("edits", []))
    punctuation_only_change = original != reviewed and classify_raw_text_diff(original, reviewed)["punctuation_space_only"]
    return {
        "case_id": case_id,
        "text_source": text_source,
        "reviewer_group": reviewer_group,
        "gold": gold_text,
        "original_text": original,
        "reviewed_text": reviewed,
        "raw_text_cer": _cer(before_distance, gold_text),
        "reviewed_text_cer": _cer(after_distance, gold_text),
        "exact_match_before": bool(before["exact_equal"]),
        "exact_match_after": bool(after["exact_equal"]),
        "before_edit_distance": before_distance,
        "after_edit_distance": after_distance,
        "net_cer_delta": round(_cer(after_distance, gold_text) - _cer(before_distance, gold_text), 6),
        "corrected_wrong_to_right": (not before["exact_equal"]) and bool(after["exact_equal"]),
        "changed_right_to_wrong": bool(before["exact_equal"]) and (not after["exact_equal"]),
        "overcorrection": after_distance > before_distance,
        "punctuation_only_change": bool(punctuation_only_change),
        "before_error_type": before["error_type"],
        "after_error_type": after["error_type"],
        "before_diff": before["brief_diff"],
        "after_diff": after["brief_diff"],
        "edit_count": len(review.get("edits", [])),
        **edit_counts,
    }


def _find_crop_paths(source_run_dir: Path, input_version: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for sidecar_path in sorted((source_run_dir / "sidecars").glob("*_recognition_bottleneck.json")):
        data = read_json(sidecar_path)
        case_id = f"{data.get('page')}__{data.get('block_id')}"
        paths: list[str] = []
        for row in data.get("rows", []):
            info = row.get("image_variants", {}).get(input_version)
            if info and info.get("image_path"):
                paths.append(str(info["image_path"]))
        result[case_id] = paths
    return result


def load_review_inputs(
    *,
    source_summary_json: str | Path,
    source_run_dir: str | Path,
    input_version: str = DEFAULT_INPUT_VERSION,
    qwen_method: str = DEFAULT_QWEN_METHOD,
    ocr_method: str = DEFAULT_OCR_METHOD,
) -> list[dict[str, Any]]:
    data = read_json(source_summary_json)
    crop_paths = _find_crop_paths(Path(source_run_dir), input_version)
    grouped: dict[str, dict[str, Any]] = {}
    for row in data.get("rows", []):
        if row.get("image_variant") != input_version:
            continue
        method_id = row.get("method_id")
        if method_id not in {qwen_method, ocr_method}:
            continue
        case_id = row.get("case_id") or f"{row.get('page')}__{row.get('block_id')}"
        item = grouped.setdefault(
            case_id,
            {
                "case_id": case_id,
                "page": row.get("page"),
                "block_id": row.get("block_id"),
                "gold": row.get("gold"),
                "input_version": input_version,
                "input_version_label": row.get("image_variant_label") or IMAGE_VARIANT_LABELS.get(input_version, input_version),
                "crop_image_paths": crop_paths.get(case_id, []),
            },
        )
        if method_id == qwen_method:
            item["raw_qwen_text"] = row.get("recognized_text")
            item["raw_qwen_method"] = method_id
        elif method_id == ocr_method:
            item["raw_ocr_text"] = row.get("recognized_text")
            item["raw_ocr_method"] = method_id
    return [item for item in grouped.values() if "raw_qwen_text" in item or "raw_ocr_text" in item]


class TextReviewerRunner:
    def __init__(self, cfg: PipelineConfig):
        from openai import AsyncOpenAI

        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    async def review(self, prompt: str) -> tuple[dict[str, Any], str, str]:
        raw = ""
        try:
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2048,
                    stop=["<|im_end|>", "<|endoftext|>"],
                )
            raw = response.choices[0].message.content or ""
            parsed = parse_reviewer_response(raw)
            return parsed, raw, parsed.get("parse_error", "")
        except Exception as exc:
            return parse_reviewer_response(""), raw, repr(exc)


def _text_sources(case: dict[str, Any]) -> list[tuple[str, Any]]:
    sources = []
    if "raw_qwen_text" in case:
        sources.append(("raw_qwen", case.get("raw_qwen_text")))
    if "raw_ocr_text" in case:
        sources.append(("raw_ocr", case.get("raw_ocr_text")))
    return sources


async def run_review_stage(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lexicon = load_domain_lexicon(args.domain_lexicon)
    cases = load_review_inputs(
        source_summary_json=args.source_summary_json,
        source_run_dir=args.source_run_dir,
        input_version=args.input_version,
        qwen_method=args.qwen_method,
        ocr_method=args.ocr_method,
    )
    cfg = load_config(Path(args.config))
    runner = TextReviewerRunner(cfg)
    records: list[dict[str, Any]] = []
    tasks: list[Any] = []
    task_meta: list[dict[str, Any]] = []
    for case in cases:
        for text_source, original_text in _text_sources(case):
            candidates = generate_regex_candidates(_to_text(original_text), lexicon)
            for group in REVIEWER_GROUPS:
                base = {
                    "case_id": case["case_id"],
                    "page": case.get("page"),
                    "block_id": case.get("block_id"),
                    "input_version": args.input_version,
                    "input_version_label": case.get("input_version_label"),
                    "crop_image_paths": case.get("crop_image_paths", []),
                    "text_source": text_source,
                    "reviewer_group": group,
                    "gold": case.get("gold"),
                    "original_text": _to_text(original_text),
                    "regex_candidates": candidates,
                }
                if group == "regex_candidates_only":
                    review = _regex_only_review(_to_text(original_text), candidates)
                    records.append({**base, "review": review, "raw_response": "", "prompt": "", "model_calls": 0})
                    continue
                prompt = build_reviewer_prompt(
                    original_text=_to_text(original_text),
                    reviewer_group=group,
                    domain_lexicon=lexicon,
                    regex_candidates=candidates,
                )
                tasks.append(runner.review(prompt))
                task_meta.append({**base, "prompt": prompt})
    results = await asyncio.gather(*tasks)
    for meta, (parsed, raw, error) in zip(task_meta, results):
        review = sanitize_reviewer_output(meta["original_text"], parsed)
        if error and not review.get("parse_error"):
            review["parse_error"] = error
        records.append({**meta, "review": review, "raw_response": raw, "model_calls": 1})
    records.sort(key=lambda row: (row["case_id"], row["text_source"], row["reviewer_group"]))
    write_jsonl(output_dir / "observation_text_reviewer_records.jsonl", records)
    write_json(output_dir / "observation_text_reviewer_prompts.json", _prompt_audit(records))
    finalize_report(output_dir, records, metadata=_metadata_from_args(args, cases))


def _prompt_audit(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in records:
        if row.get("prompt"):
            result.append(
                {
                    "case_id": row["case_id"],
                    "text_source": row["text_source"],
                    "reviewer_group": row["reviewer_group"],
                    "prompt": row["prompt"],
                }
            )
    return result


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _safe_rate(num: int, denom: int) -> float:
    return round(num / denom, 4) if denom else 0.0


def _edit_type_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {kind: 0 for kind in sorted(EDIT_TYPES)}
    for row in records:
        for edit in row.get("review", {}).get("edits", []):
            counts[_to_text(edit.get("edit_type") or "other")] = counts.get(_to_text(edit.get("edit_type") or "other"), 0) + 1
    return counts


def summarize_evaluated_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["text_source"], row["reviewer_group"])
        item = grouped.setdefault(
            key,
            {
                "text_source": row["text_source"],
                "reviewer_group": row["reviewer_group"],
                "total": 0,
                "raw_cer_total": 0.0,
                "reviewed_cer_total": 0.0,
                "exact_before": 0,
                "exact_after": 0,
                "corrected_wrong_to_right_count": 0,
                "changed_right_to_wrong_count": 0,
                "overcorrection_count": 0,
                "punctuation_only_change_count": 0,
                "applied_edit_count": 0,
                "helpful_edit_count": 0,
                "harmful_edit_count": 0,
                "high_total": 0,
                "high_helpful": 0,
                "medium_low_total": 0,
                "medium_low_helpful": 0,
            },
        )
        item["total"] += 1
        item["raw_cer_total"] += float(row["raw_text_cer"])
        item["reviewed_cer_total"] += float(row["reviewed_text_cer"])
        item["exact_before"] += int(row["exact_match_before"])
        item["exact_after"] += int(row["exact_match_after"])
        item["corrected_wrong_to_right_count"] += int(row["corrected_wrong_to_right"])
        item["changed_right_to_wrong_count"] += int(row["changed_right_to_wrong"])
        item["overcorrection_count"] += int(row["overcorrection"])
        item["punctuation_only_change_count"] += int(row["punctuation_only_change"])
        item["applied_edit_count"] += int(row["edit_count"])
        item["helpful_edit_count"] += int(row["helpful"])
        item["harmful_edit_count"] += int(row["harmful"])
        item["high_total"] += int(row["high_total"])
        item["high_helpful"] += int(row["high_helpful"])
        item["medium_low_total"] += int(row["medium_low_total"])
        item["medium_low_helpful"] += int(row["medium_low_helpful"])
    summaries = []
    for item in grouped.values():
        total = max(1, int(item["total"]))
        raw_avg = item["raw_cer_total"] / total
        reviewed_avg = item["reviewed_cer_total"] / total
        raw_wrong = item["total"] - item["exact_before"]
        item["raw_text_cer"] = round(raw_avg, 6)
        item["reviewed_text_cer"] = round(reviewed_avg, 6)
        item["net_CER_delta"] = round(reviewed_avg - raw_avg, 6)
        item["edit_precision"] = _safe_rate(item["helpful_edit_count"], item["applied_edit_count"])
        item["edit_recall"] = _safe_rate(item["corrected_wrong_to_right_count"], raw_wrong)
        item["high_confidence_edit_precision"] = _safe_rate(item["high_helpful"], item["high_total"])
        item["medium_low_confidence_edit_precision"] = _safe_rate(item["medium_low_helpful"], item["medium_low_total"])
        summaries.append(item)
    summaries.sort(key=lambda item: (item["text_source"], item["reviewer_group"]))
    return {"by_source_group": summaries}


def evaluate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        metrics = evaluate_review_record(
            case_id=record["case_id"],
            text_source=record["text_source"],
            reviewer_group=record["reviewer_group"],
            gold=record.get("gold"),
            original_text=record.get("original_text"),
            review=record.get("review", {}),
        )
        rows.append({**record, **metrics})
    return rows


def _metadata_from_args(args: argparse.Namespace, cases: list[dict[str, Any]]) -> dict[str, Any]:
    main_hashes = []
    enhanced_hashes = []
    source_run = Path(args.source_run_dir)
    for name, target in (("result.json", main_hashes), ("result_enhanced.json", enhanced_hashes)):
        for path in source_run.glob(f"**/{name}"):
            target.append({"path": str(path), "sha256": sha256_file(path)})
    if not main_hashes or not enhanced_hashes:
        source_metadata = read_json(args.source_summary_json).get("metadata", {})
        if not main_hashes:
            main_hashes = _rehash_source_metadata(source_metadata.get("main_result_hashes", {}))
        if not enhanced_hashes:
            enhanced_hashes = _rehash_source_metadata(source_metadata.get("result_enhanced_hashes", {}))
    return {
        "source_summary_json": str(args.source_summary_json),
        "source_run_dir": str(args.source_run_dir),
        "input_version": args.input_version,
        "qwen_method": args.qwen_method,
        "ocr_method": args.ocr_method,
        "domain_lexicon": str(args.domain_lexicon),
        "case_count": len(cases),
        "reviewer_groups": list(REVIEWER_GROUPS),
        "main_result_hashes": main_hashes,
        "result_enhanced_hashes": enhanced_hashes,
    }


def _rehash_source_metadata(hash_metadata: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(hash_metadata, dict):
        iterable = hash_metadata.items()
    elif isinstance(hash_metadata, list):
        iterable = ((str(index), item) for index, item in enumerate(hash_metadata))
    else:
        return rows
    for label, item in iterable:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        path = Path(item["path"])
        current = sha256_file(path) if path.exists() else ""
        expected = item.get("after") or item.get("sha256") or item.get("before") or ""
        rows.append(
            {
                "label": label,
                "path": str(path),
                "expected_sha256": expected,
                "current_sha256": current,
                "unchanged": bool(expected and current == expected),
            }
        )
    return rows


def _md(value: Any, limit: int = 240) -> str:
    text = "null" if value is None else str(value)
    text = text.replace("\n", "<br>").replace("|", "\\|")
    return text if len(text) <= limit else text[:limit] + "..."


def _group_label(group: str) -> str:
    return {
        "llm_reviewer_no_lexicon": "LLM审查-无词表",
        "llm_reviewer_with_lexicon": "LLM审查-带词表",
        "regex_candidates_only": "仅候选检测",
        "regex_candidates_plus_llm_reviewer": "候选+LLM审查",
    }.get(group, group)


def _source_label(source: str) -> str:
    return {"raw_qwen": "原始Qwen文本", "raw_ocr": "原始OCR文本"}.get(source, source)


def build_report(*, evaluated_rows: list[dict[str, Any]], summary: dict[str, Any], metadata: dict[str, Any], edit_type_counts: dict[str, int]) -> str:
    lines = [
        "# 病情观察及处理文本审查模型实验",
        "",
        "## 实验目的",
        "",
        "本实验不提升原始 OCR/VLM 识别，也不覆盖主结果；只在 raw OCR / raw Qwen 文本之后，用 reviewer 模型生成可审计的局部修正建议，并用 gold 做离线评估。",
        "",
        "## 实验配置",
        "",
        f"- 输入版本：`{metadata.get('input_version')}`",
        f"- case 数量：{metadata.get('case_count')}",
        f"- 词表：`{metadata.get('domain_lexicon')}`",
        "- gold 仅用于评估，没有进入 reviewer prompt。",
        "- `reviewed_text` 是实验侧候选文本，未写回 `result.json` 或 `result_enhanced.json`。",
        "",
        "## 对照组总体结果",
        "",
        "| 文本来源 | reviewer组 | 样本数 | 原始CER | 审查后CER | 净CER变化 | 原始完全一致 | 审查后完全一致 | 修错为对 | 对改错 | 过度纠错 | edit precision | edit recall | 高置信precision | 中低置信precision | 仅标点修改 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["by_source_group"]:
        lines.append(
            f"| {_source_label(row['text_source'])} | {_group_label(row['reviewer_group'])} | {row['total']} | "
            f"{row['raw_text_cer']:.4f} | {row['reviewed_text_cer']:.4f} | {row['net_CER_delta']:.4f} | "
            f"{row['exact_before']} | {row['exact_after']} | {row['corrected_wrong_to_right_count']} | "
            f"{row['changed_right_to_wrong_count']} | {row['overcorrection_count']} | "
            f"{row['edit_precision']:.2%} | {row['edit_recall']:.2%} | "
            f"{row['high_confidence_edit_precision']:.2%} | {row['medium_low_confidence_edit_precision']:.2%} | "
            f"{row['punctuation_only_change_count']} |"
        )

    lines.extend(["", "## edit 类型统计", "", "| 类型 | 数量 |", "|---|---:|"])
    for kind, count in edit_type_counts.items():
        lines.append(f"| {kind} | {count} |")

    successful = [row for row in evaluated_rows if row["corrected_wrong_to_right"]]
    over = [row for row in evaluated_rows if row["overcorrection"]]
    failed = [row for row in evaluated_rows if row["before_edit_distance"] > 0 and row["after_edit_distance"] == row["before_edit_distance"] and row["edit_count"] > 0]
    for title, rows in [
        ("successful correction examples", successful[:12]),
        ("overcorrection examples", over[:12]),
        ("failed correction examples", failed[:12]),
    ]:
        lines.extend(["", f"## {title}", "", "| case | 来源 | reviewer组 | gold | original_text | reviewed_text | before->after | edits |", "|---|---|---|---|---|---|---:|---|"])
        for row in rows:
            lines.append(
                f"| {row['case_id']} | {_source_label(row['text_source'])} | {_group_label(row['reviewer_group'])} | "
                f"{_md(row['gold'])} | {_md(row['original_text'])} | {_md(row['reviewed_text'])} | "
                f"{row['before_edit_distance']}->{row['after_edit_distance']} | {_md(row.get('review', {}).get('edits', []), 160)} |"
            )

    lines.extend(["", "## 明细", "", "| case | 来源 | reviewer组 | gold | original_text | reviewed_text | 错误类型before | 错误类型after | CER变化 | diff after |", "|---|---|---|---|---|---|---|---|---:|---|"])
    for row in evaluated_rows:
        lines.append(
            f"| {row['case_id']} | {_source_label(row['text_source'])} | {_group_label(row['reviewer_group'])} | "
            f"{_md(row['gold'])} | {_md(row['original_text'])} | {_md(row['reviewed_text'])} | "
            f"{row['before_error_type']} | {row['after_error_type']} | {row['net_cer_delta']:.4f} | {_md(row['after_diff'], 100)} |"
        )

    best = min(summary["by_source_group"], key=lambda row: (row["net_CER_delta"], -row["exact_after"])) if summary["by_source_group"] else None
    lines.extend(["", "## 结论", ""])
    if best:
        if best["net_CER_delta"] < 0 and best["changed_right_to_wrong_count"] == 0:
            lines.append(f"- 当前净收益最好的组合是：{_source_label(best['text_source'])} + {_group_label(best['reviewer_group'])}。")
        else:
            lines.append("- 当前没有出现足够稳的 reviewer 净收益组合。")
    lines.append("- regex 组只生成候选，不直接修改文本；LLM reviewer 的建议也只写入实验报告。")
    lines.append("- 后续若要进入候选覆盖，仍需要单独配置开关和更严格的 high-confidence 审核。")
    return "\n".join(lines) + "\n"


def finalize_report(output_dir: Path, records: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    evaluated_rows = evaluate_records(records)
    summary = summarize_evaluated_rows(evaluated_rows)
    edit_type_counts = _edit_type_counts(evaluated_rows)
    write_jsonl(output_dir / "observation_text_reviewer_evaluated.jsonl", evaluated_rows)
    write_json(
        output_dir / "observation_text_reviewer_summary.json",
        {"metadata": metadata, "summary": summary, "edit_type_counts": edit_type_counts, "rows": evaluated_rows},
    )
    (output_dir / "observation_text_reviewer_report.md").write_text(
        build_report(evaluated_rows=evaluated_rows, summary=summary, metadata=metadata, edit_type_counts=edit_type_counts),
        encoding="utf-8",
    )


def run_finalize_stage(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    records = read_jsonl(output_dir / "observation_text_reviewer_records.jsonl")
    cases = load_review_inputs(
        source_summary_json=args.source_summary_json,
        source_run_dir=args.source_run_dir,
        input_version=args.input_version,
        qwen_method=args.qwen_method,
        ocr_method=args.ocr_method,
    )
    finalize_report(output_dir, records, metadata=_metadata_from_args(args, cases))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observation text reviewer experiment.")
    parser.add_argument("--stage", choices=["review", "finalize", "all"], default="all")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--source-summary-json", required=True)
    parser.add_argument("--domain-lexicon", default="config/domain_lexicon.yaml")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--input-version", default=DEFAULT_INPUT_VERSION)
    parser.add_argument("--qwen-method", default=DEFAULT_QWEN_METHOD)
    parser.add_argument("--ocr-method", default=DEFAULT_OCR_METHOD)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    if not args.output_dir:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        runs_dir = load_config(Path(args.config)).runs_dir
        args.output_dir = str(runs_dir / f"observation_text_reviewer_experiment_{stamp}")
    if args.stage in {"review", "all"}:
        asyncio.run(run_review_stage(args))
    elif args.stage == "finalize":
        run_finalize_stage(args)


if __name__ == "__main__":
    main()
