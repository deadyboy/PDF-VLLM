from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from .target_column_observation_compare import OBS_FIELD
from .target_column_vlm import by_block, classify_diff, is_correct, normalize_text_for_eval, read_json, read_rows, sha256_file


ERROR_TYPES = (
    "exact_equal",
    "canonical_only",
    "missing_sentence",
    "extra_text",
    "rewrite_or_paraphrase",
    "char_level_mismatch",
    "punctuation_only",
    "linebreak_join_error",
    "gold_needs_check",
    "main_better_than_col",
    "col_better_than_main",
    "both_wrong",
)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _sort_block_id(block_id: str) -> tuple[int, str]:
    match = re.search(r"block_(\d+)", block_id)
    if match:
        return int(match.group(1)), block_id
    return 999999, block_id


def _strip_punctuation(value: Any) -> str | None:
    text = normalize_text_for_eval(value)
    if text is None:
        return None
    return re.sub(r"[\s,，.。:：;；、/\\()（）\[\]【】{}<>《》\"'“”‘’!！?？\-—_+|]+", "", text)


def _numeric_tokens(value: Any) -> list[str]:
    text = normalize_text_for_eval(value) or ""
    return re.findall(r"-?\d+(?:\.\d+)?", text)


def _normalized_len(value: Any) -> int:
    return len(normalize_text_for_eval(value) or "")


def suggest_error_type(
    gold: Any,
    main_value: Any,
    col_value: Any,
    main_eval_kind: str,
    col_eval_kind: str,
) -> str:
    main_ok = is_correct(main_eval_kind)
    col_ok = is_correct(col_eval_kind)
    if main_eval_kind == "equal" and col_eval_kind == "equal":
        return "exact_equal"
    if main_ok and not col_ok:
        return "main_better_than_col"
    if col_ok and not main_ok:
        return "col_better_than_main"
    if main_eval_kind == "canonical_equal" or col_eval_kind == "canonical_equal":
        return "canonical_only"
    if _strip_punctuation(gold) is not None and _strip_punctuation(gold) == _strip_punctuation(main_value):
        return "punctuation_only"
    if main_eval_kind == "separator_error" or col_eval_kind == "separator_error":
        return "linebreak_join_error"
    if main_eval_kind == "missing" or (not _has_value(main_value) and _has_value(gold)):
        return "missing_sentence"
    if main_eval_kind == "overfill" or (_has_value(main_value) and not _has_value(gold)):
        return "extra_text"

    gold_len = _normalized_len(gold)
    main_len = _normalized_len(main_value)
    if gold_len and main_len < gold_len * 0.75:
        return "missing_sentence"
    if gold_len and main_len > gold_len * 1.25:
        return "extra_text"
    if _numeric_tokens(gold) != _numeric_tokens(main_value):
        return "char_level_mismatch"
    if _has_value(gold) and _has_value(main_value):
        return "rewrite_or_paraphrase"
    return "both_wrong"


def build_observation_case(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    col_value: Any,
    r_slice: str | None,
    observation_col: str | None,
) -> dict[str, Any]:
    main_diff = classify_diff(gold, main_value)
    col_diff = classify_diff(gold, col_value)
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "col_observation_value": col_value,
        "main_eval_kind": main_diff["kind"],
        "col_eval_kind": col_diff["kind"],
        "gold_norm": normalize_text_for_eval(gold),
        "main_norm": normalize_text_for_eval(main_value),
        "col_norm": normalize_text_for_eval(col_value),
        "image_paths": {
            "r_slice": r_slice or "",
            "observation_col": observation_col or "",
        },
        "suggested_error_type": suggest_error_type(
            gold=gold,
            main_value=main_value,
            col_value=col_value,
            main_eval_kind=main_diff["kind"],
            col_eval_kind=col_diff["kind"],
        ),
        "human_error_type": "",
        "note": "",
    }


def _col_value(row: dict[str, Any]) -> Any:
    if OBS_FIELD in row:
        return row.get(OBS_FIELD)
    if "value" in row:
        return row.get("value")
    if "final_value" in row:
        return row.get("final_value")
    return None


def build_observation_cases_for_page(
    page: str,
    gold_rows: list[dict[str, Any]],
    main_rows: list[dict[str, Any]],
    col_rows: list[dict[str, Any]],
    slice_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    gold_blocks = by_block(gold_rows)
    main_blocks = by_block(main_rows)
    col_blocks = by_block(col_rows)
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(col_blocks)
            if block_id.startswith("block_")
        },
        key=_sort_block_id,
    )
    cases: list[dict[str, Any]] = []
    for block_id in block_ids:
        gold_value = gold_blocks.get(block_id, {}).get(OBS_FIELD)
        main_value = main_blocks.get(block_id, {}).get(OBS_FIELD)
        col_value = _col_value(col_blocks.get(block_id, {}))
        main_kind = classify_diff(gold_value, main_value)["kind"]
        col_kind = classify_diff(gold_value, col_value)["kind"]
        if main_kind == "equal" and col_kind == "equal":
            continue
        r_slice = ""
        observation_col = ""
        if slice_root:
            root = Path(slice_root)
            r_slice = str(root / page / f"{block_id}_R.png")
            observation_col = str(root / page / f"{block_id}_col_observation.png")
        cases.append(
            build_observation_case(
                page=page,
                block_id=block_id,
                gold=gold_value,
                main_value=main_value,
                col_value=col_value,
                r_slice=r_slice,
                observation_col=observation_col,
            )
        )
    return cases


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, int]:
    summary = {error_type: 0 for error_type in ERROR_TYPES}
    for case in cases:
        error_type = str(case.get("suggested_error_type") or "both_wrong")
        if error_type not in summary:
            summary[error_type] = 0
        summary[error_type] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_casebook(
    output_dir: Path,
    cases: list[dict[str, Any]],
    summary: dict[str, int],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Observation Residual Casebook",
        "",
        "## Error Type Summary",
        "",
        "| error_type | count |",
        "|---|---:|",
    ]
    for error_type in ERROR_TYPES:
        lines.append(f"| {error_type} | {summary.get(error_type, 0)} |")
    extra_types = sorted(set(summary) - set(ERROR_TYPES))
    for error_type in extra_types:
        lines.append(f"| {error_type} | {summary[error_type]} |")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| page | block_id | gold | main_value | col_value | main_eval_kind | col_eval_kind | suggested_error_type | r_slice | observation_col |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in cases:
        lines.append(
            f"| {case['page']} | {case['block_id']} | {_md_value(case['gold'])} | "
            f"{_md_value(case['main_value'])} | {_md_value(case['col_observation_value'])} | "
            f"{case['main_eval_kind']} | {case['col_eval_kind']} | {case['suggested_error_type']} | "
            f"{_md_value(case['image_paths'].get('r_slice', ''))} | "
            f"{_md_value(case['image_paths'].get('observation_col', ''))} |"
        )
    lines.extend(
        [
            "",
            "## Human Review Template",
            "",
            "Candidate labels: exact_equal, canonical_only, missing_sentence, extra_text, rewrite_or_paraphrase, char_level_mismatch, punctuation_only, linebreak_join_error, gold_needs_check, main_better_than_col, col_better_than_main, both_wrong.",
        ]
    )
    (output_dir / "observation_residual_casebook.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_residual_cases.jsonl").write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )
    (output_dir / "observation_residual_summary.json").write_text(
        json.dumps(
            {
                "metadata": metadata or {},
                "summary": summary,
                "case_count": len(cases),
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


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


def _load_col_rows(page: str, target_column_run_dir: Path | None, observation_sidecar_dir: Path | None) -> list[dict[str, Any]]:
    direct_rows: list[dict[str, Any]] = []
    if observation_sidecar_dir:
        direct_rows = _read_sidecars(observation_sidecar_dir / "sidecars" / page, "block_*_observation_direct_v2.json")
    if direct_rows:
        return direct_rows
    if target_column_run_dir:
        return _read_sidecars(target_column_run_dir / "sidecars" / page, "block_*_col_vlm.json")
    return []


def _hash_enhanced_result(enhanced_results_dir: Path | None, page: str) -> dict[str, Any] | None:
    if not enhanced_results_dir:
        return None
    path = enhanced_results_dir / page / "result_enhanced.json"
    if not path.exists():
        return {"path": str(path), "exists": False}
    before = sha256_file(path)
    after = sha256_file(path)
    return {"path": str(path), "exists": True, "before": before, "after": after, "unchanged": before == after}


def run_casebook(args: argparse.Namespace) -> None:
    start = time.time()
    pages = load_pages(Path(args.pages_json))
    target_column_run_dir = Path(args.target_column_run_dir) if args.target_column_run_dir else None
    observation_sidecar_dir = Path(args.observation_sidecar_dir) if args.observation_sidecar_dir else None
    enhanced_results_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    slice_root = target_column_run_dir / "slices" if target_column_run_dir else None

    all_cases: list[dict[str, Any]] = []
    main_hashes: dict[str, Any] = {}
    enhanced_hashes: dict[str, Any] = {}
    page_case_counts: dict[str, int] = {}
    for page_info in pages:
        page = str(page_info["page"])
        gold_path = Path(page_info["gold_json"])
        main_path = Path(page_info["main_result_json"])
        before = sha256_file(main_path)
        cases = build_observation_cases_for_page(
            page=page,
            gold_rows=read_rows(gold_path),
            main_rows=read_rows(main_path),
            col_rows=_load_col_rows(page, target_column_run_dir, observation_sidecar_dir),
            slice_root=slice_root,
        )
        after = sha256_file(main_path)
        all_cases.extend(cases)
        page_case_counts[page] = len(cases)
        main_hashes[page] = {"path": str(main_path), "before": before, "after": after, "unchanged": before == after}
        enhanced_hash = _hash_enhanced_result(enhanced_results_dir, page)
        if enhanced_hash is not None:
            enhanced_hashes[page] = enhanced_hash

    summary = summarize_cases(all_cases)
    metadata = {
        "pages_json": str(args.pages_json),
        "target_column_run_dir": str(target_column_run_dir) if target_column_run_dir else "",
        "observation_sidecar_dir": str(observation_sidecar_dir) if observation_sidecar_dir else "",
        "enhanced_results_dir": str(enhanced_results_dir) if enhanced_results_dir else "",
        "elapsed_seconds": round(time.time() - start, 3),
        "model_calls": 0,
        "page_case_counts": page_case_counts,
        "main_result_hashes": main_hashes,
        "result_enhanced_hashes": enhanced_hashes,
    }
    write_casebook(Path(args.output_dir), all_cases, summary, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build observation residual casebook without model calls.")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--target-column-run-dir", default="")
    parser.add_argument("--observation-sidecar-dir", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_casebook(args)


if __name__ == "__main__":
    main()
