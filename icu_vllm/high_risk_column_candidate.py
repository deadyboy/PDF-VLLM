from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from .iv_eval import classify_iv_diff, is_report_correct
from .target_column_iv_rawlines import IV_FIELD
from .target_column_vlm import by_block, classify_diff, is_correct, read_json, read_rows, sha256_file


TUBE_FIELD = "管路护理"
FIELDS = (TUBE_FIELD, IV_FIELD)
TUBE_SOURCE = "tube_col_vlm"
IV_SOURCE = "iv_clean2x_v4"
IV_OVERRIDE_KINDS = {"equal", "canonical_equal", "unit_case_equal", "manufacturer_punctuation_equal"}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _values_same(left: Any, right: Any, field: str) -> bool:
    if field == IV_FIELD:
        return classify_iv_diff(left, right)["kind"] in {"equal", "canonical_equal", "unit_case_equal"}
    return classify_diff(left, right)["kind"] in {"equal", "canonical_equal"}


def _field_diff(field: str, gold: Any, actual: Any) -> dict[str, Any]:
    if field == IV_FIELD:
        return classify_iv_diff(gold, actual)
    return classify_diff(gold, actual)


def _field_correct(field: str, kind: str) -> bool:
    if field == IV_FIELD:
        return is_report_correct(kind)
    return is_correct(kind)


def build_tube_candidate(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    tube_col_value: Any,
    tube_shadow_value: Any,
    tube_shadow_needs_review: bool,
    tube_shadow_missing: bool = False,
) -> dict[str, Any]:
    main_diff = _field_diff(TUBE_FIELD, gold, main_value)
    candidate_diff = _field_diff(TUBE_FIELD, gold, tube_col_value)
    shadow_compare = classify_diff(tube_col_value, tube_shadow_value)

    needs_review = False
    reason = ""
    if _values_same(main_value, tube_col_value, TUBE_FIELD):
        decision = "keep_main"
        reason = "main_candidate_same"
    elif not _has_value(tube_col_value) and _has_value(main_value):
        decision = "keep_main"
        reason = "col_missing_candidate"
    elif not _has_value(main_value) and _has_value(tube_col_value):
        decision = "possible_overfill_review"
        needs_review = True
        reason = "main_empty_candidate_non_empty"
    elif _has_value(tube_col_value) and (
        shadow_compare["kind"] in {"equal", "canonical_equal"} and not tube_shadow_needs_review and not tube_shadow_missing
    ):
        decision = "propose_override"
        reason = "tube_col_matches_shadow"
    elif _has_value(tube_col_value):
        decision = "needs_review"
        needs_review = True
        reason = "tube_shadow_missing_or_needs_review"
    else:
        decision = "keep_main"
        reason = "both_empty_or_no_candidate"

    return {
        "page": page,
        "block_id": block_id,
        "field": TUBE_FIELD,
        "gold": gold,
        "main_value": main_value,
        "candidate_value": tube_col_value,
        "candidate_source": TUBE_SOURCE,
        "main_eval_kind": main_diff["kind"],
        "candidate_eval_kind": candidate_diff["kind"],
        "needs_review": needs_review,
        "decision": decision,
        "reason": reason,
        "main_correct": _field_correct(TUBE_FIELD, main_diff["kind"]),
        "candidate_correct": _field_correct(TUBE_FIELD, candidate_diff["kind"]),
        "support": {
            "tube_shadow_value": tube_shadow_value,
            "tube_shadow_needs_review": bool(tube_shadow_needs_review),
            "tube_shadow_missing": bool(tube_shadow_missing),
            "tube_col_shadow_eval_kind": shadow_compare["kind"],
        },
    }


def build_iv_candidate(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    iv_value: Any,
    iv_needs_review: bool,
    iv_reason: str = "",
    iv_raw_lines: list[str] | None = None,
) -> dict[str, Any]:
    main_diff = _field_diff(IV_FIELD, gold, main_value)
    candidate_diff = _field_diff(IV_FIELD, gold, iv_value)
    candidate_kind = candidate_diff["kind"]

    needs_review = False
    reason = ""
    if _values_same(main_value, iv_value, IV_FIELD):
        decision = "keep_main"
        reason = "main_candidate_same"
    elif not _has_value(iv_value) and _has_value(main_value):
        decision = "keep_main"
        reason = "col_missing_candidate"
    elif not _has_value(main_value) and _has_value(iv_value):
        decision = "possible_overfill_review"
        needs_review = True
        reason = "main_empty_candidate_non_empty"
    elif candidate_kind == "gold_needs_check":
        decision = "needs_review"
        needs_review = True
        reason = "gold_needs_check"
    elif candidate_kind == "true_char_mismatch":
        decision = "needs_review"
        needs_review = True
        reason = "true_char_mismatch"
    elif _has_value(iv_value) and not iv_needs_review and candidate_kind in IV_OVERRIDE_KINDS:
        decision = "propose_override"
        reason = "iv_candidate_correct_without_review"
    elif _has_value(iv_value):
        decision = "needs_review"
        needs_review = True
        reason = "iv_candidate_needs_review_or_uncertain"
    else:
        decision = "keep_main"
        reason = "both_empty_or_no_candidate"

    if iv_needs_review and decision != "keep_main":
        needs_review = True
        if reason == "iv_candidate_correct_without_review":
            reason = "iv_sidecar_needs_review"

    return {
        "page": page,
        "block_id": block_id,
        "field": IV_FIELD,
        "gold": gold,
        "main_value": main_value,
        "candidate_value": iv_value,
        "candidate_source": IV_SOURCE,
        "main_eval_kind": main_diff["kind"],
        "candidate_eval_kind": candidate_kind,
        "needs_review": needs_review,
        "decision": decision,
        "reason": reason,
        "main_correct": _field_correct(IV_FIELD, main_diff["kind"]),
        "candidate_correct": _field_correct(IV_FIELD, candidate_kind),
        "support": {
            "iv_needs_review": bool(iv_needs_review),
            "iv_reason": iv_reason or "",
            "iv_raw_lines": iv_raw_lines or [],
        },
    }


def _empty_field_summary() -> dict[str, int]:
    return {
        "total": 0,
        "main_correct": 0,
        "candidate_correct": 0,
        "keep_main": 0,
        "propose_override": 0,
        "needs_review": 0,
        "possible_overfill_review": 0,
        "main_correct_candidate_wrong": 0,
    }


def summarize_candidates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"fields": {field: _empty_field_summary() for field in FIELDS}}
    for row in rows:
        field = row["field"]
        if field not in summary["fields"]:
            continue
        item = summary["fields"][field]
        item["total"] += 1
        if row["main_correct"]:
            item["main_correct"] += 1
        if row["candidate_correct"]:
            item["candidate_correct"] += 1
        decision = row["decision"]
        if decision in item:
            item[decision] += 1
        if row["main_correct"] and not row["candidate_correct"]:
            item["main_correct_candidate_wrong"] += 1
    summary["overall"] = _empty_field_summary()
    for item in summary["fields"].values():
        for key, value in item.items():
            summary["overall"][key] += value
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_candidate_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# High Risk Column Candidate Report",
        "",
        "## Summary",
        "",
        "| field | total | main_correct | candidate_correct | propose_override | needs_review | possible_overfill_review | main_correct_candidate_wrong |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field in FIELDS:
        item = summary["fields"][field]
        lines.append(
            f"| {field} | {item['total']} | {item['main_correct']} | {item['candidate_correct']} | "
            f"{item['propose_override']} | {item['needs_review']} | {item['possible_overfill_review']} | "
            f"{item['main_correct_candidate_wrong']} |"
        )
    lines.extend([
        "",
        "## Candidates",
        "",
        "| page | block_id | field | gold | main_value | candidate_value | candidate_source | main_eval_kind | candidate_eval_kind | needs_review | decision | reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {row['field']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_value'])} | {_md_value(row['candidate_value'])} | "
            f"{row['candidate_source']} | {row['main_eval_kind']} | {row['candidate_eval_kind']} | "
            f"{row['needs_review']} | {row['decision']} | {_md_value(row['reason'])} |"
        )

    (output_dir / "high_risk_column_candidate_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    (output_dir / "high_risk_column_candidate_summary.json").write_text(
        json.dumps({"metadata": metadata or {}, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "high_risk_column_candidates.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _read_sidecars(sidecar_dir: Path, pattern: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob(pattern)):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _read_tube_shadow(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"normalized_candidate": None, "needs_review": True, "_missing": True}
    data = read_json(path)
    if not isinstance(data, dict):
        return {"normalized_candidate": None, "needs_review": True, "_missing": True}
    data["_missing"] = False
    return data


def build_candidates_for_page(
    page: dict[str, Any],
    tube_col_run_dir: Path,
    tube_shadow_dir: Path,
    iv_v4_run_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    tube_blocks = by_block(_read_sidecars(tube_col_run_dir / "sidecars" / page_label, "block_*_col_vlm.json"))
    iv_blocks = by_block(_read_sidecars(iv_v4_run_dir / "sidecars" / page_label, "block_*_col_iv_drug_v4_preserve_case.json"))
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(tube_blocks) | set(iv_blocks)
            if block_id.startswith("block_")
        }
    )

    rows: list[dict[str, Any]] = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        tube_row = tube_blocks.get(block_id, {})
        iv_row = iv_blocks.get(block_id, {})
        tube_shadow = _read_tube_shadow(tube_shadow_dir / page_label / f"{block_id}_tube_care.shadow.json")

        rows.append(
            build_tube_candidate(
                page=page_label,
                block_id=block_id,
                gold=gold_row.get(TUBE_FIELD),
                main_value=main_row.get(TUBE_FIELD),
                tube_col_value=tube_row.get(TUBE_FIELD),
                tube_shadow_value=tube_shadow.get("normalized_candidate"),
                tube_shadow_needs_review=bool(tube_shadow.get("needs_review", True)),
                tube_shadow_missing=bool(tube_shadow.get("_missing", False)),
            )
        )
        rows.append(
            build_iv_candidate(
                page=page_label,
                block_id=block_id,
                gold=gold_row.get(IV_FIELD),
                main_value=main_row.get(IV_FIELD),
                iv_value=iv_row.get("final_value"),
                iv_needs_review=bool(iv_row.get("needs_review", False)),
                iv_reason=str(iv_row.get("reason") or ""),
                iv_raw_lines=[str(item) for item in iv_row.get("raw_lines", [])] if isinstance(iv_row.get("raw_lines"), list) else [],
            )
        )

    after_hash = sha256_file(main_path)
    return rows, {"path": str(main_path), "before": before_hash, "after": after_hash, "unchanged": before_hash == after_hash}


def run_report(args: argparse.Namespace) -> None:
    start = time.time()
    pages = load_pages(Path(args.pages_json))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    hashes = {}
    for page in pages:
        page_rows, page_hash = build_candidates_for_page(
            page,
            tube_col_run_dir=Path(args.tube_col_run_dir),
            tube_shadow_dir=Path(args.tube_shadow_dir),
            iv_v4_run_dir=Path(args.iv_v4_run_dir),
        )
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hash
    summary = summarize_candidates(rows)
    metadata = {
        "pages_json": str(args.pages_json),
        "tube_col_run_dir": str(args.tube_col_run_dir),
        "tube_shadow_dir": str(args.tube_shadow_dir),
        "iv_v4_run_dir": str(args.iv_v4_run_dir),
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
        "model_calls": 0,
    }
    write_candidate_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build high-risk column candidate override report without model calls.")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--tube-col-run-dir", required=True)
    parser.add_argument("--tube-shadow-dir", required=True)
    parser.add_argument("--iv-v4-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_report(args)


if __name__ == "__main__":
    main()
