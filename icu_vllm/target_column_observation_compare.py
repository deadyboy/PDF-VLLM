from __future__ import annotations

import argparse
import asyncio
import base64
import difflib
import json
import re
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import PipelineConfig, load_config
from .json_utils import normalize_nulls, parse_model_json
from .prompts import PROMPT_COL_OBSERVATION_DIRECT_V2, PROMPT_COL_OBSERVATION_RAWLINES_V1
from .target_column_vlm import (
    by_block,
    classify_diff,
    is_correct,
    normalize_text_for_eval,
    read_json,
    read_rows,
    read_rows_from_sidecars,
    sha256_file,
)


OBS_FIELD = "病情观察及处理"
METHODS = ("main_actual", "old_col", "direct_v2", "rawlines_final")
EVAL_KEYS = {
    "main_actual": "main_eval",
    "old_col": "old_col_eval",
    "direct_v2": "direct_v2_eval",
    "rawlines_final": "rawlines_eval",
}
METRIC_KEYS = {
    "main_actual": "main_metrics",
    "old_col": "old_col_metrics",
    "direct_v2": "direct_v2_metrics",
    "rawlines_final": "rawlines_metrics",
}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _normalize_field_value(value: Any) -> Any:
    return normalize_nulls({OBS_FIELD: value}).get(OBS_FIELD)


def _as_raw_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (0 if left_char == right_char else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _brief_diff(gold_norm: str, actual_norm: str, limit: int = 80) -> str:
    parts: list[str] = []
    matcher = difflib.SequenceMatcher(a=gold_norm, b=actual_norm)
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


def _numeric_token_diff(gold_norm: str, actual_norm: str) -> str:
    pattern = re.compile(r"-?\d+(?:\.\d+)?")
    gold_tokens = pattern.findall(gold_norm)
    actual_tokens = pattern.findall(actual_norm)
    if gold_tokens == actual_tokens:
        return ""
    gold_only = list(gold_tokens)
    actual_only = list(actual_tokens)
    for token in gold_tokens:
        if token in actual_only:
            actual_only.remove(token)
            gold_only.remove(token)
    return f"gold_only={gold_only}; actual_only={actual_only}"


def observation_text_metrics(gold: Any, actual: Any) -> dict[str, Any]:
    gold_norm = normalize_text_for_eval(gold) or ""
    actual_norm = normalize_text_for_eval(actual) or ""
    distance = _levenshtein(gold_norm, actual_norm)
    denominator = max(len(gold_norm), len(actual_norm), 1)
    return {
        "strict_equal": gold == actual,
        "canonical_equal": is_correct(classify_diff(gold, actual)["kind"]),
        "edit_distance": distance,
        "normalized_edit_distance": round(distance / denominator, 6),
        "gold_len": len(gold_norm),
        "actual_len": len(actual_norm),
        "missing_or_extra_chars": _brief_diff(gold_norm, actual_norm),
        "numeric_token_diff": _numeric_token_diff(gold_norm, actual_norm),
    }


def build_rawlines_sidecar(
    block_id: str,
    raw_lines: list[str],
    final_value: Any,
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
        "final_value": _normalize_field_value(final_value),
        "needs_review": bool(needs_review),
        "reason": reason or "",
        "_raw_response": raw_response,
        "_image_path": image_path,
    }
    if error:
        payload["_error"] = error
    return payload


def build_direct_sidecar(
    block_id: str,
    value: Any,
    raw_response: str,
    image_path: str,
    error: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_field_value(value)
    payload = {
        "block_id": block_id,
        "field": OBS_FIELD,
        OBS_FIELD: normalized,
        "value": normalized,
        "_raw_response": raw_response,
        "_image_path": image_path,
    }
    if error:
        payload["_error"] = error
    return payload


def parse_direct_response(raw: str) -> tuple[Any, str | None]:
    try:
        data = normalize_nulls(parse_model_json(raw))
    except Exception as exc:
        return None, str(exc)
    return data.get(OBS_FIELD), None


def parse_rawlines_response(raw: str) -> tuple[list[str], Any, bool, str, str | None]:
    try:
        data = parse_model_json(raw)
    except Exception as exc:
        return [], None, True, "parse_error", str(exc)
    raw_lines = _as_raw_lines(data.get("raw_lines"))
    final_value = _normalize_field_value(data.get("final_value"))
    needs_review = bool(data.get("needs_review", False))
    reason = str(data.get("reason") or "")
    return raw_lines, final_value, needs_review, reason, None


def build_observation_row(
    page: str,
    block_id: str,
    gold: Any,
    main_actual: Any,
    old_col: Any,
    direct_v2: Any,
    rawlines_final: Any,
    rawlines: list[str],
    rawlines_needs_review: bool,
    rawlines_reason: str,
) -> dict[str, Any]:
    main_diff = classify_diff(gold, main_actual)
    old_diff = classify_diff(gold, old_col)
    direct_diff = classify_diff(gold, direct_v2)
    rawlines_diff = classify_diff(gold, rawlines_final)
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_actual": main_actual,
        "old_col": old_col,
        "direct_v2": direct_v2,
        "rawlines_final": rawlines_final,
        "main_eval": main_diff["kind"],
        "old_col_eval": old_diff["kind"],
        "direct_v2_eval": direct_diff["kind"],
        "rawlines_eval": rawlines_diff["kind"],
        "main_metrics": observation_text_metrics(gold, main_actual),
        "old_col_metrics": observation_text_metrics(gold, old_col),
        "direct_v2_metrics": observation_text_metrics(gold, direct_v2),
        "rawlines_metrics": observation_text_metrics(gold, rawlines_final),
        "rawlines": rawlines,
        "rawlines_needs_review": bool(rawlines_needs_review),
        "rawlines_reason": rawlines_reason or "",
    }


def _empty_method_summary() -> dict[str, Any]:
    return {
        "strict_correct": 0,
        "canonical_correct": 0,
        "avg_normalized_edit_distance": 0.0,
        "main_wrong_method_correct": 0,
        "main_correct_method_wrong": 0,
        "missing": 0,
        "overfill": 0,
    }


def summarize_observation_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary = {method: _empty_method_summary() for method in METHODS}
    distance_totals = {method: 0.0 for method in METHODS}
    for row in rows:
        main_ok = is_correct(row["main_eval"])
        for method in METHODS:
            kind_key = EVAL_KEYS[method]
            metrics_key = METRIC_KEYS[method]
            kind = row[kind_key]
            method_ok = is_correct(kind)
            metrics = row[metrics_key]
            if metrics["strict_equal"]:
                summary[method]["strict_correct"] += 1
            if method_ok:
                summary[method]["canonical_correct"] += 1
            if method != "main_actual" and not main_ok and method_ok:
                summary[method]["main_wrong_method_correct"] += 1
            if method != "main_actual" and main_ok and not method_ok:
                summary[method]["main_correct_method_wrong"] += 1
            if kind == "missing":
                summary[method]["missing"] += 1
            if kind == "overfill":
                summary[method]["overfill"] += 1
            distance_totals[method] += float(metrics["normalized_edit_distance"])
    count = max(len(rows), 1)
    for method in METHODS:
        summary[method]["avg_normalized_edit_distance"] = round(distance_totals[method] / count, 6)
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_observation_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Observation Direct vs Rawlines Report",
        "",
        "## Summary",
        "",
        "| method | strict_correct | canonical_correct | avg_normalized_edit_distance | main_wrong_method_correct | main_correct_method_wrong | missing | overfill |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method in METHODS:
        item = summary[method]
        lines.append(
            f"| {method} | {item['strict_correct']} | {item['canonical_correct']} | "
            f"{item['avg_normalized_edit_distance']} | {item['main_wrong_method_correct']} | "
            f"{item['main_correct_method_wrong']} | {item['missing']} | {item['overfill']} |"
        )
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_actual | old_col | direct_v2 | rawlines_final | main_eval | old_col_eval | direct_v2_eval | rawlines_eval |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_actual'])} | {_md_value(row['old_col'])} | "
            f"{_md_value(row['direct_v2'])} | {_md_value(row['rawlines_final'])} | "
            f"{row['main_eval']} | {row['old_col_eval']} | {row['direct_v2_eval']} | "
            f"{row['rawlines_eval']} |"
        )
    lines.extend([
        "",
        "## Observation Metrics",
        "",
        "| page | block_id | method | strict_equal | canonical_equal | edit_distance | normalized_edit_distance | gold_len | actual_len | missing_or_extra_chars | numeric_token_diff |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ])
    for row in rows:
        for method in METHODS:
            metrics_key = METRIC_KEYS[method]
            metrics = row[metrics_key]
            lines.append(
                f"| {row['page']} | {row['block_id']} | {method} | "
                f"{metrics['strict_equal']} | {metrics['canonical_equal']} | "
                f"{metrics['edit_distance']} | {metrics['normalized_edit_distance']} | "
                f"{metrics['gold_len']} | {metrics['actual_len']} | "
                f"{_md_value(metrics['missing_or_extra_chars'])} | "
                f"{_md_value(metrics['numeric_token_diff'])} |"
            )
    payload = {"metadata": metadata or {}, "summary": summary, "rows": rows}
    (output_dir / "observation_direct_vs_rawlines_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    (output_dir / "observation_direct_vs_rawlines_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _block_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"block_(\d+)", path.name)
    return (int(match.group(1)) if match else 999999, path.name)


class ObservationCompareRunner:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(
            base_url=cfg.vllm_base_url,
            api_key=cfg.vllm_api_key,
            timeout=cfg.timeout_seconds,
        )
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(img_path: Path) -> str:
        return base64.b64encode(img_path.read_bytes()).decode("utf-8")

    async def _chat(self, image_path: Path, prompt: str) -> tuple[str, str | None]:
        if not image_path.exists():
            return "", f"missing image: {image_path}"
        request_kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            request_kwargs["extra_body"] = {
                "mm_processor_kwargs": self.cfg.mm_processor_kwargs,
            }
        try:
            img_b64 = self.encode_image_base64(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            return response.choices[0].message.content or "", None
        except Exception as exc:
            return "", str(exc)

    async def extract_direct(self, image_path: Path) -> tuple[Any, str, str | None]:
        raw, error = await self._chat(image_path, PROMPT_COL_OBSERVATION_DIRECT_V2)
        if error:
            return None, raw, error
        value, parse_error = parse_direct_response(raw)
        return value, raw, parse_error

    async def extract_rawlines(self, image_path: Path) -> tuple[list[str], Any, bool, str, str, str | None]:
        raw, error = await self._chat(image_path, PROMPT_COL_OBSERVATION_RAWLINES_V1)
        if error:
            return [], None, True, "request_error", raw, error
        raw_lines, final_value, needs_review, reason, parse_error = parse_rawlines_response(raw)
        return raw_lines, final_value, needs_review, reason, raw, parse_error


def read_direct_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_observation_direct_v2.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def read_rawlines_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_observation_rawlines_v1.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_page(
    page: dict[str, Any],
    source_run_dir: Path,
    output_dir: Path,
    runner: ObservationCompareRunner,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    slice_dir = source_run_dir / "slices" / page_label
    old_sidecar_dir = source_run_dir / "sidecars" / page_label
    out_sidecar_dir = output_dir / "sidecars" / page_label
    out_sidecar_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(slice_dir.glob("block_*_col_observation.png"), key=_block_sort_key)

    async def process_image(image_path: Path) -> None:
        block_id = image_path.stem.rsplit("_col_observation", 1)[0]
        rel_image = str(image_path.relative_to(source_run_dir))
        direct_task = runner.extract_direct(image_path)
        rawlines_task = runner.extract_rawlines(image_path)
        (direct_value, direct_raw, direct_error), (
            raw_lines,
            final_value,
            needs_review,
            reason,
            rawlines_raw,
            rawlines_error,
        ) = await asyncio.gather(direct_task, rawlines_task)
        direct_payload = build_direct_sidecar(
            block_id=block_id,
            value=direct_value,
            raw_response=direct_raw,
            image_path=rel_image,
            error=direct_error,
        )
        rawlines_payload = build_rawlines_sidecar(
            block_id=block_id,
            raw_lines=raw_lines,
            final_value=final_value,
            needs_review=needs_review,
            reason=reason,
            raw_response=rawlines_raw,
            image_path=rel_image,
            error=rawlines_error,
        )
        (out_sidecar_dir / f"{block_id}_observation_direct_v2.json").write_text(
            json.dumps(direct_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_sidecar_dir / f"{block_id}_observation_rawlines_v1.json").write_text(
            json.dumps(rawlines_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    await asyncio.gather(*(process_image(path) for path in image_paths))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    old_col_blocks = by_block(read_rows_from_sidecars(old_sidecar_dir))
    direct_blocks = by_block(read_direct_sidecars(out_sidecar_dir))
    rawlines_blocks = by_block(read_rawlines_sidecars(out_sidecar_dir))
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(old_col_blocks) | set(direct_blocks) | set(rawlines_blocks)
            if block_id.startswith("block_")
        }
    )
    rows = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        old_row = old_col_blocks.get(block_id, {})
        direct_row = direct_blocks.get(block_id, {})
        rawlines_row = rawlines_blocks.get(block_id, {})
        rows.append(
            build_observation_row(
                page=page_label,
                block_id=block_id,
                gold=gold_row.get(OBS_FIELD),
                main_actual=main_row.get(OBS_FIELD),
                old_col=old_row.get(OBS_FIELD),
                direct_v2=direct_row.get(OBS_FIELD),
                rawlines_final=rawlines_row.get("final_value"),
                rawlines=_as_raw_lines(rawlines_row.get("raw_lines")),
                rawlines_needs_review=bool(rawlines_row.get("needs_review", False)),
                rawlines_reason=str(rawlines_row.get("reason") or ""),
            )
        )
    after_hash = sha256_file(main_path)
    return rows, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "source_observation_images": len(image_paths),
        "direct_sidecars": len(list(out_sidecar_dir.glob("block_*_observation_direct_v2.json"))),
        "rawlines_sidecars": len(list(out_sidecar_dir.glob("block_*_observation_rawlines_v1.json"))),
    }


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    source_run_dir = Path(args.source_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(Path(args.pages_json))
    runner = ObservationCompareRunner(cfg)
    start = time.time()
    rows: list[dict[str, Any]] = []
    hashes: dict[str, Any] = {}
    for page in pages:
        page_rows, page_hashes = await run_page(page, source_run_dir, output_dir, runner)
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hashes
    summary = summarize_observation_rows(rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "source_run_dir": str(source_run_dir),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
    }
    write_observation_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare observation-column direct and raw-lines VLM prompts.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
