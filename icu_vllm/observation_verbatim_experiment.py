from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import PipelineConfig, load_config
from .json_utils import normalize_nulls, parse_model_json
from .prompts import PROMPT_COL_OBSERVATION_V2_VERBATIM_LINES
from .target_column_observation_compare import OBS_FIELD, _block_sort_key
from .target_column_vlm import by_block, classify_diff, normalize_text_for_eval, read_json, read_rows, read_rows_from_sidecars, sha256_file


METHODS = ("main", "old_col", "verbatim")
METRICS = ("correct", "canonical_only", "punctuation_only", "rewrite_or_paraphrase", "missing", "overfill")


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _as_raw_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _normalize_observation_value(value: Any) -> Any:
    return normalize_nulls({OBS_FIELD: value}).get(OBS_FIELD)


def _strip_punctuation(value: Any) -> str | None:
    text = normalize_text_for_eval(value)
    if text is None:
        return None
    return re.sub(r"[\s,，.。:：;；、/\\()（）\[\]【】{}<>《》\"'“”‘’!！?？\-—_+|]+", "", text)


def classify_observation_outcome(gold: Any, actual: Any) -> str:
    diff = classify_diff(gold, actual)
    kind = diff["kind"]
    if kind == "equal":
        return "correct"
    if kind == "canonical_equal":
        return "canonical_only"
    if kind == "missing":
        return "missing"
    if kind == "overfill":
        return "overfill"
    if _strip_punctuation(gold) is not None and _strip_punctuation(gold) == _strip_punctuation(actual):
        return "punctuation_only"
    if kind == "separator_error":
        return "punctuation_only"

    gold_norm = normalize_text_for_eval(gold) or ""
    actual_norm = normalize_text_for_eval(actual) or ""
    if gold_norm and len(actual_norm) < len(gold_norm) * 0.75:
        return "missing"
    if gold_norm and len(actual_norm) > len(gold_norm) * 1.25:
        return "overfill"
    return "rewrite_or_paraphrase"


def _is_report_correct(outcome: str) -> bool:
    return outcome in {"correct", "canonical_only", "punctuation_only"}


def parse_verbatim_response(raw: str) -> tuple[list[str], Any, bool, str, str | None]:
    try:
        data = parse_model_json(raw)
    except Exception as exc:
        return [], None, True, "parse_error", str(exc)
    raw_lines = _as_raw_lines(data.get("raw_lines"))
    final_text = _normalize_observation_value(data.get("final_text"))
    needs_review = bool(data.get("needs_review", False))
    reason = str(data.get("reason") or "")
    return raw_lines, final_text, needs_review, reason, None


def build_verbatim_sidecar(
    block_id: str,
    raw_lines: list[str],
    final_text: Any,
    needs_review: bool,
    reason: str,
    raw_response: str,
    image_path: str,
    error: str | None = None,
) -> dict[str, Any]:
    payload = {
        "block_id": block_id,
        "field": OBS_FIELD,
        "raw_lines": raw_lines,
        "final_text": _normalize_observation_value(final_text),
        "needs_review": bool(needs_review),
        "reason": reason or "",
        "_raw_response": raw_response,
        "_image_path": image_path,
    }
    if error:
        payload["_error"] = error
    return payload


def build_verbatim_row(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    old_col_value: Any,
    verbatim_value: Any,
    raw_lines: list[str],
    needs_review: bool,
    reason: str,
    image_path: str,
) -> dict[str, Any]:
    main_diff = classify_diff(gold, main_value)
    old_col_diff = classify_diff(gold, old_col_value)
    verbatim_diff = classify_diff(gold, verbatim_value)
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "old_col_value": old_col_value,
        "verbatim_value": verbatim_value,
        "main_eval_kind": main_diff["kind"],
        "old_col_eval_kind": old_col_diff["kind"],
        "verbatim_eval_kind": verbatim_diff["kind"],
        "main_outcome": classify_observation_outcome(gold, main_value),
        "old_col_outcome": classify_observation_outcome(gold, old_col_value),
        "verbatim_outcome": classify_observation_outcome(gold, verbatim_value),
        "raw_lines": raw_lines,
        "needs_review": bool(needs_review),
        "reason": reason or "",
        "image_path": image_path,
    }


def summarize_verbatim_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "metrics": {method: {metric: 0 for metric in METRICS} for method in METHODS},
        "comparisons": {
            "total": len(rows),
            "main_wrong_verbatim_correct": 0,
            "main_correct_verbatim_wrong": 0,
            "old_col_wrong_verbatim_correct": 0,
            "old_col_correct_verbatim_wrong": 0,
            "verbatim_needs_review": 0,
        },
    }
    for row in rows:
        outcomes = {
            "main": row["main_outcome"],
            "old_col": row["old_col_outcome"],
            "verbatim": row["verbatim_outcome"],
        }
        for method, outcome in outcomes.items():
            summary["metrics"][method][outcome] += 1
        main_ok = _is_report_correct(outcomes["main"])
        old_ok = _is_report_correct(outcomes["old_col"])
        verbatim_ok = _is_report_correct(outcomes["verbatim"])
        if not main_ok and verbatim_ok:
            summary["comparisons"]["main_wrong_verbatim_correct"] += 1
        if main_ok and not verbatim_ok:
            summary["comparisons"]["main_correct_verbatim_wrong"] += 1
        if not old_ok and verbatim_ok:
            summary["comparisons"]["old_col_wrong_verbatim_correct"] += 1
        if old_ok and not verbatim_ok:
            summary["comparisons"]["old_col_correct_verbatim_wrong"] += 1
        if row.get("needs_review"):
            summary["comparisons"]["verbatim_needs_review"] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_verbatim_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    sidecars: dict[str, list[dict[str, Any]]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar_root = output_dir / "observation_verbatim_sidecars"
    for page, page_sidecars in sidecars.items():
        page_dir = sidecar_root / page
        page_dir.mkdir(parents=True, exist_ok=True)
        for sidecar in page_sidecars:
            path = page_dir / f"{sidecar['block_id']}_observation_verbatim_v2.json"
            path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Observation Verbatim Sidecar Report",
        "",
        "## Summary",
        "",
        "| metric | main | old_col | verbatim |",
        "|---|---:|---:|---:|",
    ]
    for metric in METRICS:
        lines.append(
            f"| {metric} | {summary['metrics']['main'][metric]} | "
            f"{summary['metrics']['old_col'][metric]} | {summary['metrics']['verbatim'][metric]} |"
        )
    lines.extend(
        [
            "",
            "## Comparisons",
            "",
            "| metric | count |",
            "|---|---:|",
        ]
    )
    for key, value in summary["comparisons"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Details",
            "",
            "| page | block_id | gold | main_value | old_col_value | verbatim_value | main_eval_kind | old_col_eval_kind | verbatim_eval_kind |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_value'])} | {_md_value(row['old_col_value'])} | "
            f"{_md_value(row['verbatim_value'])} | {row['main_eval_kind']} | "
            f"{row['old_col_eval_kind']} | {row['verbatim_eval_kind']} |"
        )
    (output_dir / "observation_verbatim_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_verbatim_summary.json").write_text(
        json.dumps(
            {
                "metadata": metadata or {},
                "summary": summary,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


class VerbatimObservationRunner:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(image_path: Path) -> str:
        return base64.b64encode(image_path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[list[str], Any, bool, str, str, str | None]:
        if not image_path.exists():
            return [], None, True, "missing_image", "", f"missing image: {image_path}"
        request_kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            request_kwargs["extra_body"] = {"mm_processor_kwargs": self.cfg.mm_processor_kwargs}
        try:
            image_b64 = self.encode_image_base64(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPT_COL_OBSERVATION_V2_VERBATIM_LINES},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                            ],
                        }
                    ],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            raw = response.choices[0].message.content or ""
        except Exception as exc:
            return [], None, True, "request_error", "", str(exc)
        raw_lines, final_text, needs_review, reason, parse_error = parse_verbatim_response(raw)
        return raw_lines, final_text, needs_review, reason, raw, parse_error


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def read_verbatim_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not sidecar_dir.exists():
        return rows
    for path in sorted(sidecar_dir.glob("block_*_observation_verbatim_v2.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _read_direct_observation_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not sidecar_dir.exists():
        return rows
    for path in sorted(sidecar_dir.glob("block_*_observation_direct_v2.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def load_old_col_rows(page: str, source_run_dir: Path, old_observation_sidecar_dir: Path | None = None) -> list[dict[str, Any]]:
    if old_observation_sidecar_dir is not None:
        direct_rows = _read_direct_observation_sidecars(old_observation_sidecar_dir / "sidecars" / page)
        if direct_rows:
            return direct_rows
    return read_rows_from_sidecars(source_run_dir / "sidecars" / page)


async def run_page(
    page: dict[str, Any],
    source_run_dir: Path,
    old_observation_sidecar_dir: Path | None,
    output_dir: Path,
    runner: VerbatimObservationRunner,
    reuse_sidecars: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    slice_dir = source_run_dir / "slices" / page_label
    out_sidecar_dir = output_dir / "observation_verbatim_sidecars" / page_label
    out_sidecar_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(slice_dir.glob("block_*_col_observation.png"), key=_block_sort_key)

    async def process_image(image_path: Path) -> dict[str, Any]:
        block_id = image_path.stem.rsplit("_col_observation", 1)[0]
        existing = out_sidecar_dir / f"{block_id}_observation_verbatim_v2.json"
        if reuse_sidecars and existing.exists():
            data = read_json(existing)
            if isinstance(data, dict):
                return data
        rel_image = str(image_path.relative_to(source_run_dir))
        raw_lines, final_text, needs_review, reason, raw_response, error = await runner.extract(image_path)
        return build_verbatim_sidecar(
            block_id=block_id,
            raw_lines=raw_lines,
            final_text=final_text,
            needs_review=needs_review,
            reason=reason,
            raw_response=raw_response,
            image_path=rel_image,
            error=error,
        )

    sidecars = await asyncio.gather(*(process_image(image_path) for image_path in image_paths))
    for sidecar in sidecars:
        (out_sidecar_dir / f"{sidecar['block_id']}_observation_verbatim_v2.json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    old_col_blocks = by_block(load_old_col_rows(page_label, source_run_dir, old_observation_sidecar_dir))
    verbatim_blocks = by_block(sidecars)
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(old_col_blocks) | set(verbatim_blocks)
            if block_id.startswith("block_")
        },
        key=lambda block_id: _block_sort_key(Path(block_id)),
    )
    rows: list[dict[str, Any]] = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        old_col_row = old_col_blocks.get(block_id, {})
        verbatim_row = verbatim_blocks.get(block_id, {})
        rows.append(
            build_verbatim_row(
                page=page_label,
                block_id=block_id,
                gold=gold_row.get(OBS_FIELD),
                main_value=main_row.get(OBS_FIELD),
                old_col_value=old_col_row.get(OBS_FIELD),
                verbatim_value=verbatim_row.get("final_text"),
                raw_lines=_as_raw_lines(verbatim_row.get("raw_lines")),
                needs_review=bool(verbatim_row.get("needs_review", False)),
                reason=str(verbatim_row.get("reason") or ""),
                image_path=str(verbatim_row.get("_image_path") or ""),
            )
        )
    after_hash = sha256_file(main_path)
    return rows, list(sidecars), {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "source_observation_images": len(image_paths),
        "verbatim_sidecars": len(sidecars),
    }


def _hash_enhanced_results(enhanced_results_dir: Path | None, pages: list[dict[str, Any]]) -> dict[str, Any]:
    if enhanced_results_dir is None:
        return {}
    result: dict[str, Any] = {}
    for page in pages:
        page_label = str(page["page"])
        path = enhanced_results_dir / page_label / "result_enhanced.json"
        if not path.exists():
            result[page_label] = {"path": str(path), "exists": False}
            continue
        before = sha256_file(path)
        after = sha256_file(path)
        result[page_label] = {"path": str(path), "exists": True, "before": before, "after": after, "unchanged": before == after}
    return result


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    pages = load_pages(Path(args.pages_json))
    source_run_dir = Path(args.source_run_dir)
    old_observation_sidecar_dir = Path(args.old_observation_sidecar_dir) if args.old_observation_sidecar_dir else None
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = VerbatimObservationRunner(cfg)
    start = time.time()
    all_rows: list[dict[str, Any]] = []
    sidecars_by_page: dict[str, list[dict[str, Any]]] = {}
    hashes: dict[str, Any] = {}
    for page in pages:
        rows, sidecars, page_hash = await run_page(
            page=page,
            source_run_dir=source_run_dir,
            old_observation_sidecar_dir=old_observation_sidecar_dir,
            output_dir=output_dir,
            runner=runner,
            reuse_sidecars=bool(args.reuse_sidecars),
        )
        page_label = str(page["page"])
        all_rows.extend(rows)
        sidecars_by_page[page_label] = sidecars
        hashes[page_label] = page_hash
    summary = summarize_verbatim_rows(all_rows)
    enhanced_results_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "source_run_dir": str(source_run_dir),
        "old_observation_sidecar_dir": str(old_observation_sidecar_dir) if old_observation_sidecar_dir else "",
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "model_calls": sum(len(items) for items in sidecars_by_page.values()) if not args.reuse_sidecars else 0,
        "main_result_hashes": hashes,
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_results_dir, pages),
    }
    write_verbatim_report(output_dir, all_rows, summary, sidecars_by_page, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run observation strict verbatim sidecar experiment.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--old-observation-sidecar-dir", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reuse-sidecars", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
