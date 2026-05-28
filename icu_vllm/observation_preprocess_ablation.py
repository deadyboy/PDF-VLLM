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
from .image_preprocess import VARIANT_FILENAMES, write_observation_preprocess_variants
from .json_utils import normalize_nulls, parse_model_json
from .observation_eval import classify_observation_diff
from .prompts import PROMPT_COL_OBSERVATION
from .target_column_observation_compare import OBS_FIELD, _block_sort_key
from .target_column_vlm import by_block, read_json, read_rows, sha256_file


VARIANTS = tuple(VARIANT_FILENAMES)
SUMMARY_METRICS = (
    "correct",
    "canonical_only",
    "punctuation_only",
    "rewrite_or_paraphrase",
    "missing",
    "overfill",
    "char_level_mismatch",
    "text_equivalent_minor",
    "gold_needs_check",
)


def _metric_for_kind(kind: str) -> str:
    if kind == "exact_equal":
        return "correct"
    if kind == "canonical_equal":
        return "canonical_only"
    if kind == "missing_text":
        return "missing"
    if kind == "extra_text":
        return "overfill"
    if kind in SUMMARY_METRICS:
        return kind
    return "rewrite_or_paraphrase"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def parse_observation_response(raw: str) -> tuple[Any, str | None]:
    try:
        data = normalize_nulls(parse_model_json(raw))
    except Exception as exc:
        return None, str(exc)
    return data.get(OBS_FIELD), None


def build_variant_sidecar(
    block_id: str,
    variant: str,
    value: Any,
    raw_response: str,
    image_path: str,
    error: str | None = None,
) -> dict[str, Any]:
    payload = {
        "block_id": block_id,
        "variant": variant,
        "field": OBS_FIELD,
        OBS_FIELD: normalize_nulls({OBS_FIELD: value}).get(OBS_FIELD),
        "_raw_response": raw_response,
        "_image_path": image_path,
    }
    if error:
        payload["_error"] = error
    return payload


def build_ablation_row(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    variant: str,
    variant_value: Any,
) -> dict[str, Any]:
    diff = classify_observation_diff(gold, variant_value)
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "variant": variant,
        "variant_value": variant_value,
        "eval_kind": diff["kind"],
        "eval_metric": _metric_for_kind(diff["kind"]),
        "variant_norm": diff["actual_norm"],
        "brief_diff": diff["brief_diff"],
    }


def summarize_ablation_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"variants": {variant: {metric: 0 for metric in SUMMARY_METRICS} for variant in VARIANTS}}
    for row in rows:
        variant = row["variant"]
        if variant not in summary["variants"]:
            continue
        metric = row["eval_metric"]
        summary["variants"][variant][metric] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_ablation_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    sidecars: dict[str, dict[str, list[dict[str, Any]]]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar_root = output_dir / "observation_preprocess_sidecars"
    for variant, pages in sidecars.items():
        for page, page_sidecars in pages.items():
            page_dir = sidecar_root / variant / page
            page_dir.mkdir(parents=True, exist_ok=True)
            for sidecar in page_sidecars:
                path = page_dir / f"{sidecar['block_id']}_obs_{variant}.json"
                path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Observation Preprocess Ablation Report",
        "",
        "说明：本实验只改变 observation column 图像输入，使用原 PROMPT_COL_OBSERVATION，不覆盖任何结果字段。",
        "",
        "## Summary",
        "",
        "| variant | correct | canonical_only | punctuation_only | rewrite_or_paraphrase | missing | overfill | char_level_mismatch | text_equivalent_minor | gold_needs_check |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in VARIANTS:
        item = summary["variants"][variant]
        lines.append(
            f"| {variant} | {item['correct']} | {item['canonical_only']} | {item['punctuation_only']} | "
            f"{item['rewrite_or_paraphrase']} | {item['missing']} | {item['overfill']} | "
            f"{item['char_level_mismatch']} | {item['text_equivalent_minor']} | {item['gold_needs_check']} |"
        )
    lines.extend(
        [
            "",
            "## Details",
            "",
            "| page | block_id | gold | main_value | variant | variant_value | eval_kind |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_value'])} | {row['variant']} | "
            f"{_md_value(row['variant_value'])} | {row['eval_kind']} |"
        )
    (output_dir / "observation_preprocess_ablation_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    (output_dir / "observation_preprocess_ablation_summary.json").write_text(
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


class ObservationPreprocessRunner:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(image_path: Path) -> str:
        return base64.b64encode(image_path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[Any, str, str | None]:
        if not image_path.exists():
            return None, "", f"missing image: {image_path}"
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
                                {"type": "text", "text": PROMPT_COL_OBSERVATION},
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
            return None, "", str(exc)
        value, parse_error = parse_observation_response(raw)
        return value, raw, parse_error


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _variant_image_path(preprocess_dir: Path, page: str, block_id: str, variant: str) -> Path:
    return preprocess_dir / page / VARIANT_FILENAMES[variant].format(block_id=block_id)


def _sidecar_path(output_dir: Path, variant: str, page: str, block_id: str) -> Path:
    return output_dir / "observation_preprocess_sidecars" / variant / page / f"{block_id}_obs_{variant}.json"


def read_variant_sidecar(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = read_json(path)
    return data if isinstance(data, dict) else None


async def run_page(
    page: dict[str, Any],
    source_run_dir: Path,
    output_dir: Path,
    runner: ObservationPreprocessRunner,
    reuse_sidecars: bool,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, list[dict[str, Any]]]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    raw_slice_dir = source_run_dir / "slices" / page_label
    preprocess_root = output_dir / "observation_preprocess_images"
    preprocess_dir = preprocess_root / page_label
    preprocess_dir.mkdir(parents=True, exist_ok=True)
    raw_images = sorted(raw_slice_dir.glob("block_*_col_observation.png"), key=_block_sort_key)

    block_ids = []
    for raw_image in raw_images:
        block_id = raw_image.stem.rsplit("_col_observation", 1)[0]
        block_ids.append(block_id)
        write_observation_preprocess_variants(raw_image, preprocess_dir, block_id)

    sidecars: dict[str, dict[str, list[dict[str, Any]]]] = {variant: {page_label: []} for variant in VARIANTS}

    async def process_variant(block_id: str, variant: str) -> dict[str, Any]:
        existing_path = _sidecar_path(output_dir, variant, page_label, block_id)
        if reuse_sidecars:
            existing = read_variant_sidecar(existing_path)
            if existing is not None:
                return existing
        image_path = _variant_image_path(preprocess_root, page_label, block_id, variant)
        rel_image = str(image_path.relative_to(output_dir))
        value, raw, error = await runner.extract(image_path)
        return build_variant_sidecar(block_id, variant, value, raw, rel_image, error)

    tasks = [(block_id, variant) for block_id in block_ids for variant in VARIANTS]
    results = await asyncio.gather(*(process_variant(block_id, variant) for block_id, variant in tasks))
    for (block_id, variant), sidecar in zip(tasks, results):
        sidecars[variant][page_label].append(sidecar)

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    rows = []
    for block_id in block_ids:
        gold = gold_blocks.get(block_id, {}).get(OBS_FIELD)
        main_value = main_blocks.get(block_id, {}).get(OBS_FIELD)
        for variant in VARIANTS:
            variant_sidecar = next(
                (item for item in sidecars[variant][page_label] if item.get("block_id") == block_id),
                {},
            )
            rows.append(
                build_ablation_row(
                    page=page_label,
                    block_id=block_id,
                    gold=gold,
                    main_value=main_value,
                    variant=variant,
                    variant_value=variant_sidecar.get(OBS_FIELD),
                )
            )
    after_hash = sha256_file(main_path)
    return rows, sidecars, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "raw_observation_images": len(raw_images),
        "variant_images": len(block_ids) * len(VARIANTS),
    }


def _merge_sidecars(dest: dict[str, dict[str, list[dict[str, Any]]]], src: dict[str, dict[str, list[dict[str, Any]]]]) -> None:
    for variant, pages in src.items():
        dest.setdefault(variant, {})
        for page, rows in pages.items():
            dest[variant].setdefault(page, [])
            dest[variant][page].extend(rows)


def _hash_enhanced_results(enhanced_results_dir: Path | None, pages: list[dict[str, Any]]) -> dict[str, Any]:
    if enhanced_results_dir is None:
        return {}
    result = {}
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
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = ObservationPreprocessRunner(cfg)
    start = time.time()
    all_rows: list[dict[str, Any]] = []
    all_sidecars: dict[str, dict[str, list[dict[str, Any]]]] = {variant: {} for variant in VARIANTS}
    main_hashes = {}
    for page in pages:
        rows, sidecars, page_hash = await run_page(page, source_run_dir, output_dir, runner, bool(args.reuse_sidecars))
        all_rows.extend(rows)
        _merge_sidecars(all_sidecars, sidecars)
        main_hashes[str(page["page"])] = page_hash
    summary = summarize_ablation_rows(all_rows)
    enhanced_results_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    model_calls = 0 if args.reuse_sidecars else sum(len(page_rows) for pages_by_variant in all_sidecars.values() for page_rows in pages_by_variant.values())
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "source_run_dir": str(source_run_dir),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "model_calls": model_calls,
        "prompt": "PROMPT_COL_OBSERVATION",
        "main_result_hashes": main_hashes,
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_results_dir, pages),
    }
    write_ablation_report(output_dir, all_rows, summary, all_sidecars, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run observation image-preprocess ablation without changing results.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reuse-sidecars", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
