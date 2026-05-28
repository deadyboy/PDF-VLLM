from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any

from .high_risk_column_candidate import IV_FIELD, TUBE_FIELD
from .iv_eval import classify_iv_diff, is_report_correct
from .target_column_vlm import by_block, classify_diff, is_correct, read_json, read_rows, sha256_file


FIELDS = (TUBE_FIELD, IV_FIELD)
PAGE_METRICS = (
    "strict_total",
    "canonical_only",
    "separator_error",
    "missing",
    "overfill",
    "substantive_mismatch",
)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _block_id(row: dict[str, Any], index: int) -> str:
    return str(row.get("_block_id") or row.get("block_id") or f"idx_{index}")


def _field_diff(field: str, gold: Any, actual: Any) -> dict[str, Any]:
    if field == IV_FIELD:
        return classify_iv_diff(gold, actual)
    return classify_diff(gold, actual)


def _field_correct(field: str, kind: str) -> bool:
    if field == IV_FIELD:
        return is_report_correct(kind)
    return is_correct(kind)


def _metric_bucket(kind: str) -> str:
    if kind == "equal":
        return "strict_total"
    if kind in {"canonical_equal", "unit_case_equal", "manufacturer_punctuation_equal", "gold_needs_check"}:
        return "canonical_only"
    if kind == "separator_error":
        return "separator_error"
    if kind == "missing":
        return "missing"
    if kind == "overfill":
        return "overfill"
    return "substantive_mismatch"


def _empty_page_metrics() -> dict[str, int]:
    return {metric: 0 for metric in PAGE_METRICS}


def _empty_field_metrics() -> dict[str, int]:
    return {
        "main_correct": 0,
        "enhanced_correct": 0,
        "fixed_by_override": 0,
        "new_errors": 0,
    }


def load_candidates(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _replace_rows_in_container(container: Any, enhanced_rows: list[dict[str, Any]]) -> Any:
    if isinstance(container, list):
        return enhanced_rows
    if isinstance(container, dict) and isinstance(container.get("rows"), list):
        clone = copy.deepcopy(container)
        clone["rows"] = enhanced_rows
        return clone
    if isinstance(container, dict) and len(enhanced_rows) == 1:
        return enhanced_rows[0]
    return enhanced_rows


def apply_candidate_overrides(
    main_rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    page: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enhanced_rows = copy.deepcopy(main_rows)
    rows_by_block = {_block_id(row, idx): row for idx, row in enumerate(enhanced_rows)}
    logs: list[dict[str, Any]] = []

    for candidate in candidates:
        if str(candidate.get("page")) != page:
            continue
        if candidate.get("decision") != "propose_override":
            continue
        if bool(candidate.get("needs_review", False)):
            continue
        field = str(candidate.get("field"))
        if field not in FIELDS:
            continue
        block_id = str(candidate.get("block_id"))
        target_row = rows_by_block.get(block_id)
        if target_row is None:
            continue
        new_value = candidate.get("candidate_value")
        old_value = target_row.get(field)
        if not _has_value(old_value) and _has_value(new_value):
            continue
        if old_value == new_value:
            continue
        target_row[field] = new_value
        logs.append(
            {
                "page": page,
                "block_id": block_id,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "candidate_source": str(candidate.get("candidate_source") or ""),
                "reason": str(candidate.get("reason") or ""),
            }
        )

    return enhanced_rows, logs


def evaluate_enhanced_rows(
    page: str,
    gold_rows: list[dict[str, Any]],
    main_rows: list[dict[str, Any]],
    enhanced_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    gold_blocks = by_block(gold_rows)
    main_blocks = by_block(main_rows)
    enhanced_blocks = by_block(enhanced_rows)
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(enhanced_blocks)
            if block_id.startswith("block_") or block_id.startswith("idx_")
        }
    )

    page_summary = {"main": _empty_page_metrics(), "enhanced": _empty_page_metrics()}
    field_summary = {field: _empty_field_metrics() for field in FIELDS}
    detail_rows: list[dict[str, Any]] = []

    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        enhanced_row = enhanced_blocks.get(block_id, {})
        for field in FIELDS:
            gold_value = gold_row.get(field)
            main_value = main_row.get(field)
            enhanced_value = enhanced_row.get(field)
            main_diff = _field_diff(field, gold_value, main_value)
            enhanced_diff = _field_diff(field, gold_value, enhanced_value)
            main_kind = main_diff["kind"]
            enhanced_kind = enhanced_diff["kind"]
            page_summary["main"][_metric_bucket(main_kind)] += 1
            page_summary["enhanced"][_metric_bucket(enhanced_kind)] += 1

            main_ok = _field_correct(field, main_kind)
            enhanced_ok = _field_correct(field, enhanced_kind)
            if main_ok:
                field_summary[field]["main_correct"] += 1
            if enhanced_ok:
                field_summary[field]["enhanced_correct"] += 1
            if not main_ok and enhanced_ok:
                field_summary[field]["fixed_by_override"] += 1
            if main_ok and not enhanced_ok:
                field_summary[field]["new_errors"] += 1

            for result_type, actual, kind in (
                ("main", main_value, main_kind),
                ("enhanced", enhanced_value, enhanced_kind),
            ):
                detail_rows.append(
                    {
                        "page": page,
                        "block_id": block_id,
                        "field": field,
                        "gold": gold_value,
                        "result_type": result_type,
                        "actual": actual,
                        "eval_kind": kind,
                    }
                )

    return detail_rows, page_summary, field_summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def _combine_field_summaries(summaries: list[dict[str, dict[str, int]]]) -> dict[str, dict[str, int]]:
    combined = {field: _empty_field_metrics() for field in FIELDS}
    for summary in summaries:
        for field in FIELDS:
            for key, value in summary[field].items():
                combined[field][key] += value
    return combined


def _page_table_rows(page_summaries: dict[str, dict[str, dict[str, int]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page, summary in page_summaries.items():
        for result_type in ("main", "enhanced"):
            item = {"page": page, "result_type": result_type}
            item.update(summary[result_type])
            rows.append(item)
    return rows


def write_enhanced_outputs(
    output_dir: Path,
    page_outputs: dict[str, dict[str, Any]],
    override_logs: list[dict[str, Any]],
    page_table: list[dict[str, Any]],
    field_summary: dict[str, dict[str, int]],
    metadata: dict[str, Any] | None = None,
    detail_rows: list[dict[str, Any]] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    enhanced_root = output_dir / "enhanced_results"
    enhanced_root.mkdir(parents=True, exist_ok=True)

    result_paths: dict[str, str] = {}
    for page, payload in page_outputs.items():
        page_dir = enhanced_root / page
        page_dir.mkdir(parents=True, exist_ok=True)
        result_path = page_dir / "result_enhanced.json"
        result_path.write_text(
            json.dumps(payload["result_container"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result_paths[page] = str(result_path)

    (output_dir / "override_log.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in override_logs),
        encoding="utf-8",
    )

    lines = [
        "# High Risk Column Enhanced Eval Report",
        "",
        "## Page Summary",
        "",
        "| page | result_type | strict_total | canonical_only | separator_error | missing | overfill | substantive_mismatch |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in page_table:
        lines.append(
            f"| {row['page']} | {row['result_type']} | {row['strict_total']} | {row['canonical_only']} | "
            f"{row['separator_error']} | {row['missing']} | {row['overfill']} | {row['substantive_mismatch']} |"
        )
    lines.extend(
        [
            "",
            "## Field Summary",
            "",
            "| field | main_correct | enhanced_correct | fixed_by_override | new_errors |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for field in FIELDS:
        item = field_summary[field]
        lines.append(
            f"| {field} | {item['main_correct']} | {item['enhanced_correct']} | "
            f"{item['fixed_by_override']} | {item['new_errors']} |"
        )
    lines.extend(
        [
            "",
            "## Overrides",
            "",
            "| page | block_id | field | old_value | new_value | candidate_source | reason |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in override_logs:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {row['field']} | {_md_value(row['old_value'])} | "
            f"{_md_value(row['new_value'])} | {row['candidate_source']} | {_md_value(row['reason'])} |"
        )
    (output_dir / "enhanced_eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary_payload = {
        "metadata": metadata or {},
        "result_paths": result_paths,
        "page_summary": page_table,
        "field_summary": field_summary,
        "override_count": len(override_logs),
        "overrides": override_logs,
        "detail_rows": detail_rows or [],
    }
    (output_dir / "enhanced_eval_summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_enhancement(args: argparse.Namespace) -> None:
    start = time.time()
    pages = load_pages(Path(args.pages_json))
    candidates = load_candidates(Path(args.candidates_jsonl))
    output_dir = Path(args.output_dir)

    page_outputs: dict[str, dict[str, Any]] = {}
    all_override_logs: list[dict[str, Any]] = []
    all_detail_rows: list[dict[str, Any]] = []
    page_summaries: dict[str, dict[str, dict[str, int]]] = {}
    field_summaries: list[dict[str, dict[str, int]]] = []

    for page_info in pages:
        page = str(page_info["page"])
        main_path = Path(page_info["main_result_json"])
        gold_path = Path(page_info["gold_json"])
        main_container = read_json(main_path)
        main_rows = read_rows(main_path)
        gold_rows = read_rows(gold_path)
        before_hash = sha256_file(main_path)

        enhanced_rows, page_logs = apply_candidate_overrides(main_rows, candidates, page=page)
        enhanced_container = _replace_rows_in_container(main_container, enhanced_rows)
        detail_rows, page_summary, field_summary = evaluate_enhanced_rows(page, gold_rows, main_rows, enhanced_rows)
        after_hash = sha256_file(main_path)

        page_outputs[page] = {
            "enhanced_rows": enhanced_rows,
            "result_container": enhanced_container,
            "main_hash_before": before_hash,
            "main_hash_after": after_hash,
            "main_hash_unchanged": before_hash == after_hash,
        }
        all_override_logs.extend(page_logs)
        all_detail_rows.extend(detail_rows)
        page_summaries[page] = page_summary
        field_summaries.append(field_summary)

    combined_field_summary = _combine_field_summaries(field_summaries)
    page_table = _page_table_rows(page_summaries)
    metadata = {
        "pages_json": str(args.pages_json),
        "candidates_jsonl": str(args.candidates_jsonl),
        "elapsed_seconds": round(time.time() - start, 3),
        "model_calls": 0,
        "allowed_fields": list(FIELDS),
        "main_result_hashes": {
            page: {
                "before": payload["main_hash_before"],
                "after": payload["main_hash_after"],
                "unchanged": payload["main_hash_unchanged"],
            }
            for page, payload in page_outputs.items()
        },
    }
    write_enhanced_outputs(
        output_dir=output_dir,
        page_outputs=page_outputs,
        override_logs=all_override_logs,
        page_table=page_table,
        field_summary=combined_field_summary,
        metadata=metadata,
        detail_rows=all_detail_rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply safe high-risk column candidates to enhanced result copies.")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--candidates-jsonl", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_enhancement(args)


if __name__ == "__main__":
    main()
