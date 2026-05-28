from __future__ import annotations

import argparse
import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .target_column_observation_compare import OBS_FIELD
from .target_column_vlm import by_block, read_json, read_rows, sha256_file


OBS_EVAL_TYPES = (
    "exact_equal",
    "canonical_equal",
    "punctuation_only",
    "text_equivalent_minor",
    "rewrite_or_paraphrase",
    "missing_text",
    "extra_text",
    "char_level_mismatch",
    "gold_needs_check",
)
SOURCES = ("main", "old_col")
HIGH_PRIORITY_REVIEW_TYPES = {
    "rewrite_or_paraphrase",
    "missing_text",
    "extra_text",
    "char_level_mismatch",
    "gold_needs_check",
}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def normalize_observation_canonical(value: Any) -> str | None:
    if not _has_value(value):
        return None
    text = _to_text(value)
    replacements = {
        "：": ":",
        "，": ",",
        "；": ";",
        "（": "(",
        "）": ")",
        "　": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", "", text)
    return text


def _strip_punctuation(value: Any) -> str | None:
    text = normalize_observation_canonical(value)
    if text is None:
        return None
    return re.sub(r"[\s,，.。:：;；、/\\()（）\[\]【】{}<>《》\"'“”‘’!！?？\-—_+|·]+", "", text)


def _minor_equiv_norm(value: Any) -> str | None:
    text = normalize_observation_canonical(value)
    if text is None:
        return None
    text = re.sub(r"(?<=[A-Za-z0-9])(?:×|x|X|\*)(?=\d)", "x", text)
    text = text.replace("℃", "°C")
    return text


def _number_tokens(value: Any) -> list[str]:
    text = normalize_observation_canonical(value) or ""
    return re.findall(r"-?\d+(?:\.\d+)?", text)


def _medical_token_diff(gold: Any, actual: Any) -> str:
    pattern = re.compile(r"[A-Za-z]+(?:[-_/]?\d+(?:\.\d+)?)?|\d+(?:\.\d+)?(?:ml/h|mL/h|ML/h|L/min|r/min|分|s|支|ml|mL|ML|mg|MG|ug|UG)?")
    gold_tokens = pattern.findall(normalize_observation_canonical(gold) or "")
    actual_tokens = pattern.findall(normalize_observation_canonical(actual) or "")
    if gold_tokens == actual_tokens:
        return ""
    return f"gold_tokens={gold_tokens}; actual_tokens={actual_tokens}"


def _brief_diff(gold_norm: str, actual_norm: str, limit: int = 100) -> str:
    parts: list[str] = []
    matcher = SequenceMatcher(a=gold_norm, b=actual_norm)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in {"delete", "replace"} and i1 != i2:
            parts.append(f"-{gold_norm[i1:i2]}")
        if tag in {"insert", "replace"} and j1 != j2:
            parts.append(f"+{actual_norm[j1:j2]}")
        if len("; ".join(parts)) >= limit:
            break
    text = "; ".join(parts)
    return text[:limit] if len(text) > limit else text


def _looks_like_gold_needs_check(gold: Any, actual: Any) -> bool:
    gold_text = normalize_observation_canonical(gold) or ""
    actual_text = normalize_observation_canonical(actual) or ""
    if re.search(r"(?:;|,|:|\.)。|。(?:;|,|:|\.)|；。|。，|,。|;。", gold_text):
        return True
    if re.sub(r"(?<=\d)m1(?=[;,.，。:]|$)", "ml", gold_text) == actual_text and "m1" in gold_text:
        return True
    if gold_text.count("(") != gold_text.count(")") or gold_text.count("（") != gold_text.count("）"):
        return True
    return False


def _shared_ratio(gold_norm: str, actual_norm: str) -> float:
    if not gold_norm and not actual_norm:
        return 1.0
    if not gold_norm or not actual_norm:
        return 0.0
    return SequenceMatcher(a=gold_norm, b=actual_norm).ratio()


def classify_observation_diff(gold: Any, actual: Any) -> dict[str, Any]:
    gold_norm = normalize_observation_canonical(gold)
    actual_norm = normalize_observation_canonical(actual)
    numeric_token_diff = ""
    medical_token_diff = ""
    if gold == actual:
        kind = "exact_equal"
    elif gold_norm == actual_norm and gold_norm is not None:
        kind = "canonical_equal"
    elif _looks_like_gold_needs_check(gold, actual):
        kind = "gold_needs_check"
    elif gold_norm is not None and actual_norm is None:
        kind = "missing_text"
    elif gold_norm is None and actual_norm is not None:
        kind = "extra_text"
    elif gold_norm and actual_norm and len(actual_norm) < len(gold_norm) * 0.75:
        kind = "missing_text"
    elif gold_norm and actual_norm and len(actual_norm) > len(gold_norm) * 1.25:
        kind = "extra_text"
    elif _number_tokens(gold) != _number_tokens(actual):
        numeric_token_diff = f"gold_numbers={_number_tokens(gold)}; actual_numbers={_number_tokens(actual)}"
        kind = "char_level_mismatch"
    elif _medical_token_diff(gold, actual) and _strip_punctuation(gold) == _strip_punctuation(actual):
        medical_token_diff = _medical_token_diff(gold, actual)
        kind = "char_level_mismatch"
    elif _strip_punctuation(gold) is not None and _strip_punctuation(gold) == _strip_punctuation(actual):
        kind = "punctuation_only"
    elif _minor_equiv_norm(gold) is not None and _minor_equiv_norm(gold) == _minor_equiv_norm(actual):
        kind = "text_equivalent_minor"
    else:
        numeric_token_diff = ""
        gold_text = gold_norm or ""
        actual_text = actual_norm or ""
        if gold_text and actual_text and len(actual_text) < len(gold_text) * 0.75:
            kind = "missing_text"
        elif gold_text and actual_text and len(actual_text) > len(gold_text) * 1.25:
            kind = "extra_text"
        else:
            kind = ""
        gold_numbers = _number_tokens(gold)
        actual_numbers = _number_tokens(actual)
        if kind:
            pass
        elif gold_numbers != actual_numbers:
            numeric_token_diff = f"gold_numbers={gold_numbers}; actual_numbers={actual_numbers}"
            kind = "char_level_mismatch"
        else:
            medical_token_diff = _medical_token_diff(gold, actual)
            if medical_token_diff:
                kind = "char_level_mismatch"
            elif gold_text and actual_text and _shared_ratio(gold_text, actual_text) >= 0.88:
                kind = "char_level_mismatch"
            else:
                kind = "rewrite_or_paraphrase"
    if not numeric_token_diff:
        gold_numbers = _number_tokens(gold)
        actual_numbers = _number_tokens(actual)
        if gold_numbers != actual_numbers:
            numeric_token_diff = f"gold_numbers={gold_numbers}; actual_numbers={actual_numbers}"
    if not medical_token_diff:
        medical_token_diff = _medical_token_diff(gold, actual)
    return {
        "kind": kind,
        "gold": gold,
        "actual": actual,
        "gold_norm": gold_norm,
        "actual_norm": actual_norm,
        "punctuationless_gold": _strip_punctuation(gold),
        "punctuationless_actual": _strip_punctuation(actual),
        "numeric_token_diff": numeric_token_diff,
        "medical_token_diff": medical_token_diff,
        "brief_diff": _brief_diff(gold_norm or "", actual_norm or ""),
    }


def _case_kind(main_kind: str, old_col_kind: str) -> str:
    priority = (
        "gold_needs_check",
        "char_level_mismatch",
        "missing_text",
        "extra_text",
        "rewrite_or_paraphrase",
        "text_equivalent_minor",
        "punctuation_only",
        "canonical_equal",
        "exact_equal",
    )
    for kind in priority:
        if main_kind == kind or old_col_kind == kind:
            return kind
    return main_kind


def build_observation_eval_row(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    old_col_value: Any,
) -> dict[str, Any]:
    main_diff = classify_observation_diff(gold, main_value)
    old_col_diff = classify_observation_diff(gold, old_col_value)
    suggested = _case_kind(main_diff["kind"], old_col_diff["kind"])
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "old_col_value": old_col_value,
        "main_kind": main_diff["kind"],
        "old_col_kind": old_col_diff["kind"],
        "main_norm": main_diff["actual_norm"],
        "old_col_norm": old_col_diff["actual_norm"],
        "gold_norm": main_diff["gold_norm"],
        "main_diff": main_diff,
        "old_col_diff": old_col_diff,
        "suggested_review": suggested if suggested in HIGH_PRIORITY_REVIEW_TYPES else "no_high_priority_review",
        "case_error_type": suggested,
    }


def _empty_counts() -> dict[str, int]:
    return {kind: 0 for kind in OBS_EVAL_TYPES}


def summarize_observation_eval_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = {source: _empty_counts() for source in SOURCES}
    case_counts = _empty_counts()
    review_queue_count = 0
    for row in rows:
        source_counts["main"][row["main_kind"]] += 1
        source_counts["old_col"][row["old_col_kind"]] += 1
        case_counts[row["case_error_type"]] += 1
        if row["suggested_review"] != "no_high_priority_review":
            review_queue_count += 1
    return {
        "case_error_type_counts": case_counts,
        "source_counts": source_counts,
        "review_queue_count": review_queue_count,
        "total_rows": len(rows),
    }


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_observation_eval_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_payload = {
        "verbatim_candidate_status": "not_candidate",
        **(metadata or {}),
    }
    metadata_payload["verbatim_candidate_status"] = "not_candidate"

    lines = [
        "# Observation Eval Refined Report",
        "",
        "说明：verbatim sidecar 不进入候选覆盖；本报告只做规则归因，不修改任何结果。",
        "",
        "## 分类汇总",
        "",
        "| error_type | count |",
        "|---|---:|",
    ]
    for kind in OBS_EVAL_TYPES:
        lines.append(f"| {kind} | {summary['case_error_type_counts'].get(kind, 0)} |")
    lines.extend(
        [
            "",
            "## Main vs Old Column",
            "",
            "| source | exact_equal | canonical_equal | punctuation_only | text_equivalent_minor | rewrite_or_paraphrase | missing_text | extra_text | char_level_mismatch | gold_needs_check |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source in SOURCES:
        counts = summary["source_counts"][source]
        lines.append(
            f"| {source} | {counts['exact_equal']} | {counts['canonical_equal']} | "
            f"{counts['punctuation_only']} | {counts['text_equivalent_minor']} | "
            f"{counts['rewrite_or_paraphrase']} | {counts['missing_text']} | "
            f"{counts['extra_text']} | {counts['char_level_mismatch']} | {counts['gold_needs_check']} |"
        )
    lines.extend(
        [
            "",
            "## Case 明细",
            "",
            "| page | block_id | gold | main_value | old_col_value | main_kind | old_col_kind | suggested_review |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_value'])} | {_md_value(row['old_col_value'])} | "
            f"{row['main_kind']} | {row['old_col_kind']} | {row['suggested_review']} |"
        )
    review_rows = [row for row in rows if row["suggested_review"] != "no_high_priority_review"]
    lines.extend(
        [
            "",
            "## 人工复核队列",
            "",
            "| page | block_id | suggested_review | gold | main_value | old_col_value |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in review_rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {row['suggested_review']} | "
            f"{_md_value(row['gold'])} | {_md_value(row['main_value'])} | {_md_value(row['old_col_value'])} |"
        )

    (output_dir / "observation_eval_refined_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_eval_refined_cases.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    (output_dir / "observation_eval_refined_summary.json").write_text(
        json.dumps(
            {
                "metadata": metadata_payload,
                "summary": summary,
                "rows": rows,
                "review_queue": review_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _sort_block_id(block_id: str) -> tuple[int, str]:
    match = re.search(r"block_(\d+)", block_id)
    return (int(match.group(1)) if match else 999999, block_id)


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _read_sidecars(sidecar_dir: Path, pattern: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not sidecar_dir.exists():
        return rows
    for path in sorted(sidecar_dir.glob(pattern), key=lambda item: _sort_block_id(item.name)):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _col_value(row: dict[str, Any]) -> Any:
    if OBS_FIELD in row:
        return row.get(OBS_FIELD)
    if "value" in row:
        return row.get("value")
    if "final_value" in row:
        return row.get("final_value")
    return None


def load_old_col_rows(page: str, target_column_run_dir: Path | None, observation_sidecar_dir: Path | None) -> list[dict[str, Any]]:
    if observation_sidecar_dir:
        rows = _read_sidecars(observation_sidecar_dir / "sidecars" / page, "block_*_observation_direct_v2.json")
        if rows:
            return rows
    if target_column_run_dir:
        return _read_sidecars(target_column_run_dir / "sidecars" / page, "block_*_col_vlm.json")
    return []


def build_rows_for_page(page: dict[str, Any], target_column_run_dir: Path | None, observation_sidecar_dir: Path | None) -> list[dict[str, Any]]:
    page_label = str(page["page"])
    gold_blocks = by_block(read_rows(Path(page["gold_json"])))
    main_blocks = by_block(read_rows(Path(page["main_result_json"])))
    old_col_blocks = by_block(load_old_col_rows(page_label, target_column_run_dir, observation_sidecar_dir))
    block_ids = sorted(
        {block_id for block_id in set(gold_blocks) | set(main_blocks) | set(old_col_blocks) if block_id.startswith("block_")},
        key=_sort_block_id,
    )
    rows = []
    for block_id in block_ids:
        gold = gold_blocks.get(block_id, {}).get(OBS_FIELD)
        main_value = main_blocks.get(block_id, {}).get(OBS_FIELD)
        old_col_value = _col_value(old_col_blocks.get(block_id, {}))
        rows.append(build_observation_eval_row(page_label, block_id, gold, main_value, old_col_value))
    return rows


def _hash_result_enhanced(enhanced_results_dir: Path | None, page: str) -> dict[str, Any] | None:
    if enhanced_results_dir is None:
        return None
    path = enhanced_results_dir / page / "result_enhanced.json"
    if not path.exists():
        return {"path": str(path), "exists": False}
    before = sha256_file(path)
    after = sha256_file(path)
    return {"path": str(path), "exists": True, "before": before, "after": after, "unchanged": before == after}


def run_report(args: argparse.Namespace) -> None:
    start = time.time()
    pages = load_pages(Path(args.pages_json))
    target_column_run_dir = Path(args.target_column_run_dir) if args.target_column_run_dir else None
    observation_sidecar_dir = Path(args.observation_sidecar_dir) if args.observation_sidecar_dir else None
    enhanced_results_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    rows: list[dict[str, Any]] = []
    main_hashes: dict[str, Any] = {}
    enhanced_hashes: dict[str, Any] = {}
    page_counts: dict[str, int] = {}
    for page in pages:
        page_label = str(page["page"])
        main_path = Path(page["main_result_json"])
        before = sha256_file(main_path)
        page_rows = build_rows_for_page(page, target_column_run_dir, observation_sidecar_dir)
        after = sha256_file(main_path)
        rows.extend(page_rows)
        page_counts[page_label] = len(page_rows)
        main_hashes[page_label] = {"path": str(main_path), "before": before, "after": after, "unchanged": before == after}
        enhanced_hash = _hash_result_enhanced(enhanced_results_dir, page_label)
        if enhanced_hash is not None:
            enhanced_hashes[page_label] = enhanced_hash
    summary = summarize_observation_eval_rows(rows)
    metadata = {
        "pages_json": str(args.pages_json),
        "target_column_run_dir": str(target_column_run_dir) if target_column_run_dir else "",
        "observation_sidecar_dir": str(observation_sidecar_dir) if observation_sidecar_dir else "",
        "enhanced_results_dir": str(enhanced_results_dir) if enhanced_results_dir else "",
        "elapsed_seconds": round(time.time() - start, 3),
        "model_calls": 0,
        "page_counts": page_counts,
        "main_result_hashes": main_hashes,
        "result_enhanced_hashes": enhanced_hashes,
    }
    write_observation_eval_report(Path(args.output_dir), rows, summary, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build refined observation eval report without model calls.")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--target-column-run-dir", default="")
    parser.add_argument("--observation-sidecar-dir", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_report(args)


if __name__ == "__main__":
    main()
