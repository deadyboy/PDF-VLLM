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
from .iv_eval import classify_iv_diff, is_report_correct
from .json_utils import normalize_nulls
from .prompts import PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE
from .target_column_iv_clean2x import read_clean2x_sidecars
from .target_column_iv_rawlines import IV_FIELD, _as_raw_lines, parse_iv_rawlines_response, raw_lines_tail_kind
from .target_column_iv_v3_unit import read_v3_unit_sidecars
from .target_column_vlm import read_json, read_rows, sha256_file, by_block


PROMPT_VARIANT = "v4_preserve_case"
METHODS = ("v2_clean2x", "v3_unit", "v4_preserve_case")
SUMMARY_METRICS = (
    "report_correct",
    "unit_case_equal",
    "manufacturer_punctuation_equal",
    "gold_needs_check",
    "true_char_mismatch",
    "main_wrong_method_correct",
    "main_correct_method_wrong",
    "both_wrong",
    "col_overfill",
    "col_missing",
    "raw_lines_missing_tail",
    "needs_review_true",
    "correct_but_needs_review",
)


def build_v4_preserve_case_sidecar(
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


def build_v4_preserve_case_row(
    page: str,
    block_id: str,
    gold: Any,
    main_actual: Any,
    v2_actual: Any,
    v3_actual: Any,
    v4_actual: Any,
    v2_raw_lines: list[str],
    v3_raw_lines: list[str],
    v4_raw_lines: list[str],
    v2_needs_review: bool,
    v3_needs_review: bool,
    v4_needs_review: bool,
    v2_reason: str = "",
    v3_reason: str = "",
    v4_reason: str = "",
) -> dict[str, Any]:
    main_diff = classify_iv_diff(gold, main_actual)
    v2_diff = classify_iv_diff(gold, v2_actual)
    v3_diff = classify_iv_diff(gold, v3_actual)
    v4_diff = classify_iv_diff(gold, v4_actual)
    return {
        "page": page,
        "block_id": block_id,
        "gold": gold,
        "main_actual": main_actual,
        "iv_v2_clean2x": v2_actual,
        "iv_v3_unit": v3_actual,
        "iv_v4_preserve_case": v4_actual,
        "main_eval_kind": main_diff["kind"],
        "v2_clean2x_eval_kind": v2_diff["kind"],
        "v3_unit_eval_kind": v3_diff["kind"],
        "v4_preserve_case_eval_kind": v4_diff["kind"],
        "v2_clean2x_raw_lines": v2_raw_lines,
        "v3_unit_raw_lines": v3_raw_lines,
        "v4_preserve_case_raw_lines": v4_raw_lines,
        "v2_clean2x_needs_review": bool(v2_needs_review),
        "v3_unit_needs_review": bool(v3_needs_review),
        "v4_preserve_case_needs_review": bool(v4_needs_review),
        "v2_clean2x_reason": v2_reason or "",
        "v3_unit_reason": v3_reason or "",
        "v4_preserve_case_reason": v4_reason or "",
        "v2_clean2x_tail_kind": raw_lines_tail_kind(gold, v2_actual, v2_raw_lines),
        "v3_unit_tail_kind": raw_lines_tail_kind(gold, v3_actual, v3_raw_lines),
        "v4_preserve_case_tail_kind": raw_lines_tail_kind(gold, v4_actual, v4_raw_lines),
    }


def _empty_method_counts() -> dict[str, int]:
    return {method: 0 for method in METHODS}


def summarize_v4_preserve_case_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {metric: _empty_method_counts() for metric in SUMMARY_METRICS}
    for row in rows:
        main_ok = is_report_correct(row["main_eval_kind"])
        for method in METHODS:
            eval_key = f"{method}_eval_kind"
            tail_key = f"{method}_tail_kind"
            review_key = f"{method}_needs_review"
            kind = row[eval_key]
            method_ok = is_report_correct(kind)
            if method_ok:
                summary["report_correct"][method] += 1
            if kind in {"unit_case_equal", "manufacturer_punctuation_equal", "gold_needs_check", "true_char_mismatch"}:
                summary[kind][method] += 1
            if not main_ok and method_ok:
                summary["main_wrong_method_correct"][method] += 1
            elif main_ok and not method_ok:
                summary["main_correct_method_wrong"][method] += 1
            elif not main_ok and not method_ok:
                summary["both_wrong"][method] += 1
            if kind == "overfill":
                summary["col_overfill"][method] += 1
            if kind == "missing":
                summary["col_missing"][method] += 1
            if row.get(tail_key) == "raw_lines_missing_tail":
                summary["raw_lines_missing_tail"][method] += 1
            needs_review = bool(row.get(review_key, False))
            if needs_review:
                summary["needs_review_true"][method] += 1
            if method_ok and needs_review:
                summary["correct_but_needs_review"][method] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_v4_preserve_case_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, int]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Target Column IV V4 Preserve-Case Report",
        "",
        "## Summary",
        "",
        "| metric | v2_clean2x | v3_unit | v4_preserve_case |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in SUMMARY_METRICS:
        item = summary[metric]
        lines.append(f"| {metric} | {item['v2_clean2x']} | {item['v3_unit']} | {item['v4_preserve_case']} |")
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_actual | iv_v2_clean2x | iv_v3_unit | iv_v4_preserve_case | main_eval_kind | v2_clean2x_eval_kind | v3_unit_eval_kind | v4_preserve_case_eval_kind | v2_needs_review | v3_needs_review | v4_needs_review | v2_tail_kind | v3_tail_kind | v4_tail_kind |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_actual'])} | {_md_value(row['iv_v2_clean2x'])} | "
            f"{_md_value(row['iv_v3_unit'])} | {_md_value(row['iv_v4_preserve_case'])} | "
            f"{row['main_eval_kind']} | {row['v2_clean2x_eval_kind']} | "
            f"{row['v3_unit_eval_kind']} | {row['v4_preserve_case_eval_kind']} | "
            f"{row['v2_clean2x_needs_review']} | {row['v3_unit_needs_review']} | "
            f"{row['v4_preserve_case_needs_review']} | {row['v2_clean2x_tail_kind']} | "
            f"{row['v3_unit_tail_kind']} | {row['v4_preserve_case_tail_kind']} |"
        )
    payload = {"metadata": metadata or {}, "summary": summary, "rows": rows}
    (output_dir / "target_column_iv_v4_preserve_case_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    (output_dir / "target_column_iv_v4_preserve_case_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_gold_corrections(output_dir, rows)


def write_gold_corrections(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    seen = set()
    correction_rows = []
    for row in rows:
        for method in METHODS:
            if row.get(f"{method}_eval_kind") != "gold_needs_check":
                continue
            key = (row["page"], row["block_id"], row.get("gold"), row.get(f"iv_{method}"))
            if key in seen:
                continue
            seen.add(key)
            correction_rows.append({
                "page": row["page"],
                "block_id": row["block_id"],
                "field": IV_FIELD,
                "kind": "gold_needs_check",
                "gold": row.get("gold"),
                "candidate": row.get(f"iv_{method}"),
                "source_method": method,
                "note": "疑似 gold 中容量单位把字母 l 写成数字 1；仅供人工复核，不自动修改 gold。",
            })
    path = output_dir / "gold_corrections.jsonl"
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in correction_rows),
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


class IvV4PreserveCaseRunner:
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
                            {"type": "text", "text": PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE},
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


def read_v4_preserve_case_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_col_iv_drug_v4_preserve_case.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_page(
    page: dict[str, Any],
    clean2x_run_dir: Path,
    v3_unit_run_dir: Path,
    output_dir: Path,
    runner: IvV4PreserveCaseRunner,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    crop_dir = clean2x_run_dir / "crops" / page_label
    v2_sidecar_dir = clean2x_run_dir / "sidecars" / page_label
    v3_sidecar_dir = v3_unit_run_dir / "sidecars" / page_label
    out_sidecar_dir = output_dir / "sidecars" / page_label
    out_sidecar_dir.mkdir(parents=True, exist_ok=True)
    images = sorted(crop_dir.glob("block_*_col_iv_drug_clean_2x.png"), key=_block_sort_key)

    async def process_image(path: Path) -> None:
        block_id = path.stem.rsplit("_col_iv_drug_clean_2x", 1)[0]
        raw_lines, final_value, needs_review, reason, raw, error = await runner.extract(path)
        payload = build_v4_preserve_case_sidecar(
            block_id=block_id,
            raw_lines=raw_lines,
            final_value=final_value,
            needs_review=needs_review,
            reason=reason,
            raw_response=raw,
            image_path=str(path.relative_to(clean2x_run_dir)),
            error=error,
        )
        (out_sidecar_dir / f"{block_id}_col_iv_drug_v4_preserve_case.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    await asyncio.gather(*(process_image(path) for path in images))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    v2_blocks = by_block(read_clean2x_sidecars(v2_sidecar_dir))
    v3_blocks = by_block(read_v3_unit_sidecars(v3_sidecar_dir))
    v4_blocks = by_block(read_v4_preserve_case_sidecars(out_sidecar_dir))
    block_ids = sorted(
        {
            block_id
            for block_id in set(gold_blocks) | set(main_blocks) | set(v2_blocks) | set(v3_blocks) | set(v4_blocks)
            if block_id.startswith("block_")
        }
    )
    rows = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        v2_row = v2_blocks.get(block_id, {})
        v3_row = v3_blocks.get(block_id, {})
        v4_row = v4_blocks.get(block_id, {})
        rows.append(
            build_v4_preserve_case_row(
                page=page_label,
                block_id=block_id,
                gold=gold_row.get(IV_FIELD),
                main_actual=main_row.get(IV_FIELD),
                v2_actual=v2_row.get("final_value"),
                v3_actual=v3_row.get("final_value"),
                v4_actual=v4_row.get("final_value"),
                v2_raw_lines=_as_raw_lines(v2_row.get("raw_lines")),
                v3_raw_lines=_as_raw_lines(v3_row.get("raw_lines")),
                v4_raw_lines=_as_raw_lines(v4_row.get("raw_lines")),
                v2_needs_review=bool(v2_row.get("needs_review", False)),
                v3_needs_review=bool(v3_row.get("needs_review", False)),
                v4_needs_review=bool(v4_row.get("needs_review", False)),
                v2_reason=str(v2_row.get("reason") or ""),
                v3_reason=str(v3_row.get("reason") or ""),
                v4_reason=str(v4_row.get("reason") or ""),
            )
        )
    after_hash = sha256_file(main_path)
    return rows, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "clean_2x_images": len(images),
        "v4_sidecars": len(list(out_sidecar_dir.glob("block_*_col_iv_drug_v4_preserve_case.json"))),
    }


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    clean2x_run_dir = Path(args.clean2x_run_dir)
    v3_unit_run_dir = Path(args.v3_unit_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(Path(args.pages_json))
    runner = IvV4PreserveCaseRunner(cfg)
    start = time.time()
    rows: list[dict[str, Any]] = []
    hashes: dict[str, Any] = {}
    for page in pages:
        page_rows, page_hash = await run_page(page, clean2x_run_dir, v3_unit_run_dir, output_dir, runner)
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hash
    summary = summarize_v4_preserve_case_rows(rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "clean2x_run_dir": str(clean2x_run_dir),
        "v3_unit_run_dir": str(v3_unit_run_dir),
        "prompt_variant": PROMPT_VARIANT,
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
    }
    write_v4_preserve_case_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IV v4 preserve-case prompt experiment on clean_2x crops.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--clean2x-run-dir", required=True)
    parser.add_argument("--v3-unit-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
