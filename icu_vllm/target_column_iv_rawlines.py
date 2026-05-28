from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import PipelineConfig, load_config
from .json_utils import normalize_nulls, parse_model_json
from .prompts import PROMPT_COL_IV_DRUG_V2_RAWLINES
from .target_column_vlm import (
    classify_diff,
    is_correct,
    normalize_text_for_eval,
    read_json,
    read_rows,
    read_rows_from_sidecars,
    sha256_file,
    by_block,
)


IV_FIELD = "入量_静脉用药"


def build_iv_rawlines_sidecar(
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
        "field": IV_FIELD,
        "raw_lines": raw_lines,
        "final_value": normalize_nulls({IV_FIELD: final_value}).get(IV_FIELD),
        "needs_review": bool(needs_review),
        "reason": reason or "",
        "_raw_response": raw_response,
        "_image_path": image_path,
    }
    if error:
        payload["_error"] = error
    return payload


def _as_raw_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def parse_iv_rawlines_response(raw: str) -> tuple[list[str], Any, bool, str, str | None]:
    try:
        data = parse_model_json(raw)
    except Exception as exc:
        return [], None, True, "parse_error", str(exc)
    raw_lines = _as_raw_lines(data.get("raw_lines"))
    final_value = normalize_nulls({IV_FIELD: data.get("final_value")}).get(IV_FIELD)
    needs_review = bool(data.get("needs_review", False))
    reason = str(data.get("reason") or "")
    return raw_lines, final_value, needs_review, reason, None


def raw_lines_tail_kind(gold: Any, final_value: Any, raw_lines: list[str]) -> str:
    if is_correct(classify_diff(gold, final_value)["kind"]):
        return "none"
    gold_norm = normalize_text_for_eval(gold)
    if gold_norm is None:
        return "none"
    raw_norm = normalize_text_for_eval("".join(raw_lines))
    if raw_norm is None:
        return "raw_lines_missing_tail"
    gold_flat = gold_norm.replace(";", "")
    raw_flat = raw_norm.replace(";", "")
    if raw_flat == gold_flat:
        return "raw_lines_contains_tail_but_final_wrong"
    return "raw_lines_missing_tail"


def _empty_metric_row() -> dict[str, int]:
    return {"old_col": 0, "iv_v2_rawlines": 0}


def summarize_iv_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {
        "col_correct": _empty_metric_row(),
        "main_wrong_col_correct": _empty_metric_row(),
        "main_correct_col_wrong": _empty_metric_row(),
        "both_wrong": _empty_metric_row(),
        "col_overfill": _empty_metric_row(),
        "col_missing": _empty_metric_row(),
        "raw_lines_contains_tail_but_final_wrong": _empty_metric_row(),
        "raw_lines_missing_tail": _empty_metric_row(),
    }
    for row in rows:
        main_ok = is_correct(row["main_eval_kind"])
        for label, key in (("old_col", "old_col_eval_kind"), ("iv_v2_rawlines", "iv_v2_eval_kind")):
            kind = row[key]
            col_ok = is_correct(kind)
            if col_ok:
                summary["col_correct"][label] += 1
            if not main_ok and col_ok:
                summary["main_wrong_col_correct"][label] += 1
            elif main_ok and not col_ok:
                summary["main_correct_col_wrong"][label] += 1
            elif not main_ok and not col_ok:
                summary["both_wrong"][label] += 1
            if kind == "overfill":
                summary["col_overfill"][label] += 1
            if kind == "missing":
                summary["col_missing"][label] += 1
        tail_kind = row.get("iv_v2_tail_kind")
        if tail_kind in ("raw_lines_contains_tail_but_final_wrong", "raw_lines_missing_tail"):
            summary[tail_kind]["iv_v2_rawlines"] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_iv_rawlines_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, int]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Target Column IV Rawlines Report",
        "",
        "## Summary",
        "",
        "| metric | old_col | iv_v2_rawlines |",
        "| --- | ---: | ---: |",
    ]
    for metric, values in summary.items():
        lines.append(f"| {metric} | {values['old_col']} | {values['iv_v2_rawlines']} |")
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_actual | col_vlm_old | col_vlm_iv_v2_rawlines | main_eval_kind | old_col_eval_kind | iv_v2_eval_kind | raw_lines | needs_review | reason | iv_v2_tail_kind |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        raw_lines = json.dumps(row.get("raw_lines", []), ensure_ascii=False)
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_actual'])} | {_md_value(row['col_vlm_old'])} | "
            f"{_md_value(row['col_vlm_iv_v2_rawlines'])} | {row['main_eval_kind']} | "
            f"{row['old_col_eval_kind']} | {row['iv_v2_eval_kind']} | "
            f"{_md_value(raw_lines)} | {row['needs_review']} | {_md_value(row['reason'])} | "
            f"{row['iv_v2_tail_kind']} |"
        )
    (output_dir / "target_column_iv_rawlines_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    payload = {"metadata": metadata or {}, "summary": summary, "rows": rows}
    (output_dir / "target_column_iv_rawlines_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


class IvRawlinesRunner:
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

    async def extract(self, image_path: Path) -> tuple[list[str], Any, bool, str, str, str | None]:
        if not image_path.exists():
            return [], None, True, "missing_image", "", f"missing image: {image_path}"
        request_kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            request_kwargs["extra_body"] = {
                "mm_processor_kwargs": self.cfg.mm_processor_kwargs,
            }
        raw = ""
        try:
            img_b64 = self.encode_image_base64(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_COL_IV_DRUG_V2_RAWLINES},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            raw = response.choices[0].message.content or ""
            raw_lines, final_value, needs_review, reason, error = parse_iv_rawlines_response(raw)
            return raw_lines, final_value, needs_review, reason, raw, error
        except Exception as exc:
            return [], None, True, "request_error", raw, str(exc)


def _block_sort_key(path: Path) -> tuple[int, str]:
    name = path.name
    try:
        return int(name.split("_")[1]), name
    except Exception:
        return 999999, name


async def run_page(
    page: dict[str, Any],
    source_run_dir: Path,
    output_dir: Path,
    runner: IvRawlinesRunner,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    slice_dir = source_run_dir / "slices" / page_label
    old_sidecar_dir = source_run_dir / "sidecars" / page_label
    out_sidecar_dir = output_dir / "sidecars" / page_label
    out_sidecar_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(slice_dir.glob("block_*_col_iv_drug.png"), key=_block_sort_key)

    async def process_image(image_path: Path) -> None:
        block_id = image_path.stem.rsplit("_col_iv_drug", 1)[0]
        raw_lines, final_value, needs_review, reason, raw, error = await runner.extract(image_path)
        payload = build_iv_rawlines_sidecar(
            block_id=block_id,
            raw_lines=raw_lines,
            final_value=final_value,
            needs_review=needs_review,
            reason=reason,
            raw_response=raw,
            image_path=str(image_path.relative_to(source_run_dir)),
            error=error,
        )
        (out_sidecar_dir / f"{block_id}_col_iv_drug_v2_rawlines.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    await asyncio.gather(*(process_image(path) for path in image_paths))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    old_col_blocks = by_block(read_rows_from_sidecars(old_sidecar_dir))
    new_blocks = by_block(read_iv_rawlines_sidecars(out_sidecar_dir))
    block_ids = sorted(
        {block_id for block_id in set(gold_blocks) | set(main_blocks) | set(old_col_blocks) | set(new_blocks) if block_id.startswith("block_")}
    )
    rows = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        old_row = old_col_blocks.get(block_id, {})
        new_row = new_blocks.get(block_id, {})
        gold = gold_row.get(IV_FIELD)
        main_actual = main_row.get(IV_FIELD)
        old_actual = old_row.get(IV_FIELD)
        new_actual = new_row.get("final_value")
        main_diff = classify_diff(gold, main_actual)
        old_diff = classify_diff(gold, old_actual)
        new_diff = classify_diff(gold, new_actual)
        raw_lines = _as_raw_lines(new_row.get("raw_lines"))
        rows.append({
            "page": page_label,
            "block_id": block_id,
            "gold": gold,
            "main_actual": main_actual,
            "col_vlm_old": old_actual,
            "col_vlm_iv_v2_rawlines": new_actual,
            "main_eval_kind": main_diff["kind"],
            "old_col_eval_kind": old_diff["kind"],
            "iv_v2_eval_kind": new_diff["kind"],
            "raw_lines": raw_lines,
            "needs_review": bool(new_row.get("needs_review", False)),
            "reason": str(new_row.get("reason") or ""),
            "iv_v2_tail_kind": raw_lines_tail_kind(gold, new_actual, raw_lines),
        })
    after_hash = sha256_file(main_path)
    return rows, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "source_iv_images": len(image_paths),
        "new_sidecars": len(list(out_sidecar_dir.glob("block_*_col_iv_drug_v2_rawlines.json"))),
    }


def read_iv_rawlines_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_col_iv_drug_v2_rawlines.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    source_run_dir = Path(args.source_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(Path(args.pages_json))
    runner = IvRawlinesRunner(cfg)
    start = time.time()
    rows: list[dict[str, Any]] = []
    hashes: dict[str, Any] = {}
    for page in pages:
        page_rows, page_hashes = await run_page(page, source_run_dir, output_dir, runner)
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hashes
    summary = summarize_iv_rows(rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "source_run_dir": str(source_run_dir),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
    }
    write_iv_rawlines_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IV-drug single-column raw-lines prompt experiment.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
