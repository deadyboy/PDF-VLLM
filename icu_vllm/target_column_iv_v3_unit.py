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
from .json_utils import normalize_nulls
from .prompts import PROMPT_COL_IV_DRUG_V3_UNIT_AWARE
from .target_column_iv_clean2x import read_clean2x_sidecars
from .target_column_iv_rawlines import IV_FIELD, _as_raw_lines, parse_iv_rawlines_response, raw_lines_tail_kind
from .target_column_vlm import classify_diff, is_correct, read_json, read_rows, sha256_file, by_block


PROMPT_VARIANT = "v3_unit_aware"


def build_v3_unit_sidecar(
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
        "prompt_variant": PROMPT_VARIANT,
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


def build_v3_unit_row(
    page: str,
    block_id: str,
    gold: Any,
    main_actual: Any,
    v2_actual: Any,
    v3_actual: Any,
    v2_raw_lines: list[str],
    v3_raw_lines: list[str],
    v2_needs_review: bool,
    v3_needs_review: bool,
    v2_reason: str = "",
    v3_reason: str = "",
) -> dict[str, Any]:
    main_diff = classify_diff(gold, main_actual)
    v2_diff = classify_diff(gold, v2_actual)
    v3_diff = classify_diff(gold, v3_actual)
    return {
        "page": page,
        "block_id": block_id,
        "gold": gold,
        "main_actual": main_actual,
        "iv_v2_clean2x": v2_actual,
        "iv_v3_unit": v3_actual,
        "main_eval_kind": main_diff["kind"],
        "v2_clean2x_eval_kind": v2_diff["kind"],
        "v3_unit_eval_kind": v3_diff["kind"],
        "v2_clean2x_raw_lines": v2_raw_lines,
        "v3_unit_raw_lines": v3_raw_lines,
        "v2_clean2x_needs_review": bool(v2_needs_review),
        "v3_unit_needs_review": bool(v3_needs_review),
        "v2_clean2x_reason": v2_reason or "",
        "v3_unit_reason": v3_reason or "",
        "v2_clean2x_tail_kind": raw_lines_tail_kind(gold, v2_actual, v2_raw_lines),
        "v3_unit_tail_kind": raw_lines_tail_kind(gold, v3_actual, v3_raw_lines),
    }


def _empty_metric_row() -> dict[str, int]:
    return {"v2_clean2x": 0, "v3_unit": 0}


def summarize_v3_unit_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {
        "col_correct": _empty_metric_row(),
        "main_wrong_col_correct": _empty_metric_row(),
        "main_correct_col_wrong": _empty_metric_row(),
        "both_wrong": _empty_metric_row(),
        "col_overfill": _empty_metric_row(),
        "col_missing": _empty_metric_row(),
        "raw_lines_missing_tail": _empty_metric_row(),
        "char_level_mismatch": _empty_metric_row(),
        "needs_review_true": _empty_metric_row(),
        "correct_but_needs_review": _empty_metric_row(),
    }
    for row in rows:
        main_ok = is_correct(row["main_eval_kind"])
        for label, eval_key, tail_key, review_key in (
            ("v2_clean2x", "v2_clean2x_eval_kind", "v2_clean2x_tail_kind", "v2_clean2x_needs_review"),
            ("v3_unit", "v3_unit_eval_kind", "v3_unit_tail_kind", "v3_unit_needs_review"),
        ):
            kind = row[eval_key]
            col_ok = is_correct(kind)
            needs_review = bool(row.get(review_key, False))
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
            if row.get(tail_key) == "raw_lines_missing_tail":
                summary["raw_lines_missing_tail"][label] += 1
            if kind == "substantive_mismatch":
                summary["char_level_mismatch"][label] += 1
            if needs_review:
                summary["needs_review_true"][label] += 1
            if col_ok and needs_review:
                summary["correct_but_needs_review"][label] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_v3_unit_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, int]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Target Column IV V3 Unit-Aware Report",
        "",
        "## Summary",
        "",
        "| metric | v2_clean2x | v3_unit |",
        "| --- | ---: | ---: |",
    ]
    for metric, values in summary.items():
        lines.append(f"| {metric} | {values['v2_clean2x']} | {values['v3_unit']} |")
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_actual | iv_v2_clean2x | iv_v3_unit | main_eval_kind | v2_clean2x_eval_kind | v3_unit_eval_kind | v2_raw_lines | v3_raw_lines | v2_needs_review | v3_needs_review | v2_reason | v3_reason | v2_tail_kind | v3_tail_kind |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        v2_lines = json.dumps(row.get("v2_clean2x_raw_lines", []), ensure_ascii=False)
        v3_lines = json.dumps(row.get("v3_unit_raw_lines", []), ensure_ascii=False)
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_actual'])} | {_md_value(row['iv_v2_clean2x'])} | "
            f"{_md_value(row['iv_v3_unit'])} | {row['main_eval_kind']} | "
            f"{row['v2_clean2x_eval_kind']} | {row['v3_unit_eval_kind']} | "
            f"{_md_value(v2_lines)} | {_md_value(v3_lines)} | "
            f"{row['v2_clean2x_needs_review']} | {row['v3_unit_needs_review']} | "
            f"{_md_value(row['v2_clean2x_reason'])} | {_md_value(row['v3_unit_reason'])} | "
            f"{row['v2_clean2x_tail_kind']} | {row['v3_unit_tail_kind']} |"
        )
    (output_dir / "target_column_iv_v3_unit_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    payload = {"metadata": metadata or {}, "summary": summary, "rows": rows}
    (output_dir / "target_column_iv_v3_unit_summary.json").write_text(
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
    try:
        return int(path.name.split("_")[1]), path.name
    except Exception:
        return 999999, path.name


class IvV3UnitRunner:
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
                            {"type": "text", "text": PROMPT_COL_IV_DRUG_V3_UNIT_AWARE},
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


def read_v3_unit_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_col_iv_drug_v3_unit.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_page(
    page: dict[str, Any],
    clean2x_run_dir: Path,
    output_dir: Path,
    runner: IvV3UnitRunner,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    crop_dir = clean2x_run_dir / "crops" / page_label
    v2_sidecar_dir = clean2x_run_dir / "sidecars" / page_label
    out_sidecar_dir = output_dir / "sidecars" / page_label
    out_sidecar_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(crop_dir.glob("block_*_col_iv_drug_clean_2x.png"), key=_block_sort_key)

    async def process_image(path: Path) -> None:
        block_id = path.stem.rsplit("_col_iv_drug_clean_2x", 1)[0]
        raw_lines, final_value, needs_review, reason, raw, error = await runner.extract(path)
        payload = build_v3_unit_sidecar(
            block_id=block_id,
            raw_lines=raw_lines,
            final_value=final_value,
            needs_review=needs_review,
            reason=reason,
            raw_response=raw,
            image_path=str(path.relative_to(clean2x_run_dir)),
            error=error,
        )
        (out_sidecar_dir / f"{block_id}_col_iv_drug_v3_unit.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    await asyncio.gather(*(process_image(path) for path in images))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    v2_blocks = by_block(read_clean2x_sidecars(v2_sidecar_dir))
    v3_blocks = by_block(read_v3_unit_sidecars(out_sidecar_dir))
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(v2_blocks) | set(v3_blocks)
            if block_id.startswith("block_")
        }
    )
    rows = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        v2_row = v2_blocks.get(block_id, {})
        v3_row = v3_blocks.get(block_id, {})
        rows.append(
            build_v3_unit_row(
                page=page_label,
                block_id=block_id,
                gold=gold_row.get(IV_FIELD),
                main_actual=main_row.get(IV_FIELD),
                v2_actual=v2_row.get("final_value"),
                v3_actual=v3_row.get("final_value"),
                v2_raw_lines=_as_raw_lines(v2_row.get("raw_lines")),
                v3_raw_lines=_as_raw_lines(v3_row.get("raw_lines")),
                v2_needs_review=bool(v2_row.get("needs_review", False)),
                v3_needs_review=bool(v3_row.get("needs_review", False)),
                v2_reason=str(v2_row.get("reason") or ""),
                v3_reason=str(v3_row.get("reason") or ""),
            )
        )
    after_hash = sha256_file(main_path)
    return rows, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "clean_2x_images": len(images),
        "v3_sidecars": len(list(out_sidecar_dir.glob("block_*_col_iv_drug_v3_unit.json"))),
    }


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    clean2x_run_dir = Path(args.clean2x_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(Path(args.pages_json))
    runner = IvV3UnitRunner(cfg)
    start = time.time()
    rows: list[dict[str, Any]] = []
    hashes: dict[str, Any] = {}
    for page in pages:
        page_rows, page_hash = await run_page(page, clean2x_run_dir, output_dir, runner)
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hash
    summary = summarize_v3_unit_rows(rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "clean2x_run_dir": str(clean2x_run_dir),
        "prompt_variant": PROMPT_VARIANT,
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
    }
    write_v3_unit_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IV v3 unit-aware prompt experiment on clean_2x crops.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--clean2x-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
