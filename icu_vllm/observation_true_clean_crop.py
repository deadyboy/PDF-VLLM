from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import PipelineConfig, load_config
from .json_utils import normalize_nulls, parse_model_json
from .observation_eval import classify_observation_diff
from .prompts import PROMPT_COL_OBSERVATION
from .target_column_observation_compare import OBS_FIELD
from .target_column_vlm import by_block, read_json, read_rows, sha256_file


SOURCE_STAGE = "clean_final_block_before_redline_before_optimize"
TRUE_CLEAN_VARIANTS = (
    "obs_true_clean_native",
    "obs_true_clean_2x",
    "obs_true_clean_3x",
)
REPORT_VARIANTS = ("raw_col",) + TRUE_CLEAN_VARIANTS
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


def true_clean_image_name(block_id: str, variant: str) -> str:
    if variant not in TRUE_CLEAN_VARIANTS:
        raise ValueError(f"unknown true clean variant: {variant}")
    suffix = variant.replace("obs_true_clean_", "obs_true_clean_")
    return f"{block_id}_{suffix}.png"


def _to_hw(size: tuple[int, int] | list[int]) -> list[int]:
    return [int(size[0]), int(size[1])]


def build_true_clean_manifest(
    source_image: str,
    page: str,
    block_id: str,
    final_block_shape: tuple[int, int] | list[int],
    crop_box: tuple[int, int, int, int],
    padding: int,
    native_size: tuple[int, int] | list[int],
    variants: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    x1, x2, y1, y2 = crop_box
    normalized_variants: dict[str, dict[str, Any]] = {}
    for variant, item in variants.items():
        before = _to_hw(item.get("size_before") or item.get("variant_size_before_llm_optimize"))
        after = _to_hw(item.get("size_after") or item.get("variant_size_after_llm_optimize"))
        used_optimize = bool(item.get("used_optimize", item.get("used_optimize_image_for_llm", False)))
        normalized_variants[variant] = {
            "path": item.get("path", ""),
            "variant_size_before_llm_optimize": before,
            "variant_size_after_llm_optimize": after,
            "used_optimize_image_for_llm": used_optimize,
            "was_downscaled_before_model": before != after,
        }
        if "scale" in item:
            normalized_variants[variant]["scale"] = int(item["scale"])
    native_variant = normalized_variants["obs_true_clean_native"]
    return {
        "source_image": source_image,
        "page": page,
        "block_id": block_id,
        "source_stage": SOURCE_STAGE,
        "final_block_shape": _to_hw(final_block_shape),
        "crop_x1": int(x1),
        "crop_x2": int(x2),
        "crop_y1": int(y1),
        "crop_y2": int(y2),
        "padding": int(padding),
        "native_size": _to_hw(native_size),
        "variant_size_before_llm_optimize": native_variant["variant_size_before_llm_optimize"],
        "variant_size_after_llm_optimize": native_variant["variant_size_after_llm_optimize"],
        "used_optimize_image_for_llm": native_variant["used_optimize_image_for_llm"],
        "was_downscaled_before_model": native_variant["was_downscaled_before_model"],
        "variants": normalized_variants,
    }


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


def build_true_clean_row(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    raw_col_value: Any,
    true_clean_values: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "raw_col_value": raw_col_value,
    }
    raw_diff = classify_observation_diff(gold, raw_col_value)
    row["raw_col_eval_kind"] = raw_diff["kind"]
    row["raw_col_eval_metric"] = _metric_for_kind(raw_diff["kind"])
    for variant in TRUE_CLEAN_VARIANTS:
        value = true_clean_values.get(variant)
        diff = classify_observation_diff(gold, value)
        row[variant] = value
        row[f"{variant}_eval_kind"] = diff["kind"]
        row[f"{variant}_eval_metric"] = _metric_for_kind(diff["kind"])
    return row


def summarize_true_clean_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"variants": {variant: {metric: 0 for metric in SUMMARY_METRICS} for variant in REPORT_VARIANTS}}
    for row in rows:
        for variant in REPORT_VARIANTS:
            metric = row.get(f"{variant}_eval_metric")
            if metric in SUMMARY_METRICS:
                summary["variants"][variant][metric] += 1
    return summary


def _ratio_ok(size: list[int], native: list[int], scale: int, tolerance: float = 0.03) -> bool:
    expected_h = max(1, native[0] * scale)
    expected_w = max(1, native[1] * scale)
    return (
        abs(size[0] - expected_h) <= max(1.0, expected_h * tolerance)
        and abs(size[1] - expected_w) <= max(1.0, expected_w * tolerance)
    )


def summarize_true_clean_sanity(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    sanity = {
        "total_manifests": len(manifests),
        "two_x_size_ok": 0,
        "three_x_size_ok": 0,
        "source_stage_ok": 0,
        "downscaled_before_model": 0,
        "used_optimize_image_for_llm": 0,
        "bad_size_examples": [],
        "bad_source_stage_examples": [],
        "downscaled_examples": [],
    }
    for manifest in manifests:
        block_ref = f"{manifest.get('page')}:{manifest.get('block_id')}"
        native = manifest.get("native_size") or [0, 0]
        variants = manifest.get("variants", {})
        if manifest.get("source_stage") == SOURCE_STAGE:
            sanity["source_stage_ok"] += 1
        elif len(sanity["bad_source_stage_examples"]) < 10:
            sanity["bad_source_stage_examples"].append(block_ref)

        two_size = variants.get("obs_true_clean_2x", {}).get("variant_size_before_llm_optimize") or [0, 0]
        three_size = variants.get("obs_true_clean_3x", {}).get("variant_size_before_llm_optimize") or [0, 0]
        if _ratio_ok(two_size, native, 2):
            sanity["two_x_size_ok"] += 1
        elif len(sanity["bad_size_examples"]) < 10:
            sanity["bad_size_examples"].append({"block": block_ref, "variant": "obs_true_clean_2x", "native": native, "size": two_size})
        if _ratio_ok(three_size, native, 3):
            sanity["three_x_size_ok"] += 1
        elif len(sanity["bad_size_examples"]) < 10:
            sanity["bad_size_examples"].append({"block": block_ref, "variant": "obs_true_clean_3x", "native": native, "size": three_size})

        for variant, item in variants.items():
            if item.get("used_optimize_image_for_llm"):
                sanity["used_optimize_image_for_llm"] += 1
            if item.get("was_downscaled_before_model"):
                sanity["downscaled_before_model"] += 1
                if len(sanity["downscaled_examples"]) < 10:
                    sanity["downscaled_examples"].append({
                        "block": block_ref,
                        "variant": variant,
                        "before": item.get("variant_size_before_llm_optimize"),
                        "after": item.get("variant_size_after_llm_optimize"),
                    })
    return sanity


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_true_clean_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    sanity: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Observation True Clean Crop Ablation Report",
        "",
        "说明：本实验从原始输入图重新走金主任 cutter 的时间锚点和表头拼接逻辑，使用画红线前、optimize 前的 clean_final_block 裁出病情观察列。",
        "",
        f"source_stage: `{SOURCE_STAGE}`",
        "",
        "## Summary",
        "",
        "| variant | correct | canonical_only | punctuation_only | rewrite_or_paraphrase | missing | overfill | char_level_mismatch | text_equivalent_minor | gold_needs_check |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in REPORT_VARIANTS:
        item = summary["variants"][variant]
        lines.append(
            f"| {variant} | {item['correct']} | {item['canonical_only']} | {item['punctuation_only']} | "
            f"{item['rewrite_or_paraphrase']} | {item['missing']} | {item['overfill']} | "
            f"{item['char_level_mismatch']} | {item['text_equivalent_minor']} | {item['gold_needs_check']} |"
        )
    lines.extend([
        "",
        "## Sanity Check",
        "",
        f"- total_manifests: {sanity.get('total_manifests', 0)}",
        f"- 2x 尺寸约等于 native 两倍: {sanity.get('two_x_size_ok', 0)}/{sanity.get('total_manifests', 0)}",
        f"- 3x 尺寸约等于 native 三倍: {sanity.get('three_x_size_ok', 0)}/{sanity.get('total_manifests', 0)}",
        f"- source_stage 正确: {sanity.get('source_stage_ok', 0)}/{sanity.get('total_manifests', 0)}",
        f"- repo 侧送模型前 downscale: {sanity.get('downscaled_before_model', 0)}",
        f"- repo 侧使用 optimize_image_for_llm: {sanity.get('used_optimize_image_for_llm', 0)}",
        "",
        "注：本脚本没有在送入 OpenAI/vLLM API 前调用 optimize_image_for_llm，也没有 repo 侧 resize/pad/downscale；vLLM/Qwen processor 内部视觉 token resize 不会从 OpenAI API 返回，无法在本脚本内直接观测。",
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_value | raw_col_value | true_clean_native | true_clean_2x | true_clean_3x | raw_col_eval_kind | native_eval_kind | true_clean_2x_eval_kind | true_clean_3x_eval_kind |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | {_md_value(row['main_value'])} | "
            f"{_md_value(row['raw_col_value'])} | {_md_value(row['obs_true_clean_native'])} | "
            f"{_md_value(row['obs_true_clean_2x'])} | {_md_value(row['obs_true_clean_3x'])} | "
            f"{row['raw_col_eval_kind']} | {row['obs_true_clean_native_eval_kind']} | "
            f"{row['obs_true_clean_2x_eval_kind']} | {row['obs_true_clean_3x_eval_kind']} |"
        )
    (output_dir / "observation_true_clean_crop_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_true_clean_crop_summary.json").write_text(
        json.dumps(
            {
                "metadata": metadata or {},
                "summary": summary,
                "sanity": sanity,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def parse_observation_response(raw: str) -> tuple[Any, str | None]:
    try:
        data = normalize_nulls(parse_model_json(raw))
    except Exception as exc:
        return None, str(exc)
    return data.get(OBS_FIELD), None


def build_sidecar(
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


class ObservationTrueCleanRunner:
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
        raw = ""
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
            return None, raw, str(exc)
        value, parse_error = parse_observation_response(raw)
        return value, raw, parse_error


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def run_crop_worker(
    cfg: PipelineConfig,
    image_path: Path,
    crop_dir: Path,
    page_label: str,
    reuse_crops: bool = False,
    padding: int = 12,
) -> None:
    if reuse_crops and crop_dir.exists() and list(crop_dir.glob("block_*_obs_true_clean_native.png")):
        return
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(project_root) if not existing_pythonpath else f"{project_root}{os.pathsep}{existing_pythonpath}"
    result = subprocess.run(
        [
            str(cfg.ocr_python),
            "-m",
            "icu_vllm.observation_true_clean_crop_worker",
            "--img",
            str(image_path),
            "--out",
            str(crop_dir),
            "--page",
            page_label,
            "--padding",
            str(padding),
        ],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if crop_dir.exists():
        (crop_dir / "_crop_stdout.txt").write_text(result.stdout, encoding="utf-8")
        (crop_dir / "_crop_stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"true-clean observation crop worker failed for {image_path}: {result.stderr}")


def _block_sort_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.name.split("_")[1]), path.name
    except Exception:
        return 999999, path.name


def _sidecar_path(output_dir: Path, variant: str, page: str, block_id: str) -> Path:
    return output_dir / "observation_true_clean_sidecars" / variant / page / f"{block_id}_obs_{variant}.json"


def _read_sidecar(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = read_json(path)
    return data if isinstance(data, dict) else None


def _read_true_clean_sidecars(output_dir: Path, variant: str, page: str) -> dict[str, dict[str, Any]]:
    sidecar_dir = output_dir / "observation_true_clean_sidecars" / variant / page
    rows = {}
    for path in sorted(sidecar_dir.glob(f"block_*_obs_{variant}.json"), key=_block_sort_key):
        data = _read_sidecar(path)
        if data:
            rows[str(data.get("block_id"))] = data
    return rows


def read_raw_col_values(raw_col_run_dir: Path, page: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    target_sidecar_dir = raw_col_run_dir / "sidecars" / page
    if target_sidecar_dir.exists():
        for path in sorted(target_sidecar_dir.glob("block_*_col_vlm.json"), key=_block_sort_key):
            data = read_json(path)
            if isinstance(data, dict):
                values[str(data.get("block_id"))] = data.get(OBS_FIELD)
        return values
    preprocess_dir = raw_col_run_dir / "observation_preprocess_sidecars" / "raw_col" / page
    if preprocess_dir.exists():
        for path in sorted(preprocess_dir.glob("block_*_obs_raw_col.json"), key=_block_sort_key):
            data = read_json(path)
            if isinstance(data, dict):
                values[str(data.get("block_id"))] = data.get(OBS_FIELD)
    return values


def _load_manifests(crop_dir: Path) -> list[dict[str, Any]]:
    manifests = []
    for path in sorted(crop_dir.glob("block_*_obs_true_clean_manifest.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            manifests.append(data)
    return manifests


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


async def run_page(
    page: dict[str, Any],
    cfg: PipelineConfig,
    raw_col_run_dir: Path,
    output_dir: Path,
    runner: ObservationTrueCleanRunner,
    reuse_crops: bool = False,
    reuse_sidecars: bool = False,
    padding: int = 12,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], int]:
    page_label = str(page["page"])
    image_path = Path(page["image"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)

    crop_dir = output_dir / "observation_true_clean_crops" / page_label
    run_crop_worker(cfg, image_path, crop_dir, page_label, reuse_crops=reuse_crops, padding=padding)
    manifests = _load_manifests(crop_dir)

    block_ids = [path.stem.rsplit("_obs_true_clean_native", 1)[0] for path in sorted(crop_dir.glob("block_*_obs_true_clean_native.png"), key=_block_sort_key)]
    model_calls = 0

    async def process_variant(block_id: str, variant: str) -> dict[str, Any]:
        existing_path = _sidecar_path(output_dir, variant, page_label, block_id)
        if reuse_sidecars:
            existing = _read_sidecar(existing_path)
            if existing is not None:
                return existing
        image_path_for_variant = crop_dir / true_clean_image_name(block_id, variant)
        rel_image = str(image_path_for_variant.relative_to(output_dir))
        value, raw, error = await runner.extract(image_path_for_variant)
        return build_sidecar(block_id, variant, value, raw, rel_image, error)

    tasks = [(block_id, variant) for block_id in block_ids for variant in TRUE_CLEAN_VARIANTS]
    sidecar_results = []
    for block_id, variant in tasks:
        existing = _read_sidecar(_sidecar_path(output_dir, variant, page_label, block_id)) if reuse_sidecars else None
        if existing is None:
            model_calls += 1
    sidecar_results = await asyncio.gather(*(process_variant(block_id, variant) for block_id, variant in tasks))
    for (_, variant), sidecar in zip(tasks, sidecar_results):
        sidecar_path = _sidecar_path(output_dir, variant, page_label, str(sidecar["block_id"]))
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    raw_col_values = read_raw_col_values(raw_col_run_dir, page_label)
    sidecar_by_variant = {
        variant: _read_true_clean_sidecars(output_dir, variant, page_label)
        for variant in TRUE_CLEAN_VARIANTS
    }
    row_block_ids = sorted(
        {block_id for block_id in set(block_ids) | set(gold_blocks) | set(main_blocks) | set(raw_col_values) if block_id.startswith("block_")}
    )
    rows = []
    for block_id in row_block_ids:
        true_values = {
            variant: sidecar_by_variant.get(variant, {}).get(block_id, {}).get(OBS_FIELD)
            for variant in TRUE_CLEAN_VARIANTS
        }
        rows.append(
            build_true_clean_row(
                page=page_label,
                block_id=block_id,
                gold=gold_blocks.get(block_id, {}).get(OBS_FIELD),
                main_value=main_blocks.get(block_id, {}).get(OBS_FIELD),
                raw_col_value=raw_col_values.get(block_id),
                true_clean_values=true_values,
            )
        )
    after_hash = sha256_file(main_path)
    return rows, manifests, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "true_clean_blocks": len(block_ids),
        "true_clean_sidecars": len(sidecar_results),
    }, model_calls


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    pages = load_pages(Path(args.pages_json))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = ObservationTrueCleanRunner(cfg)
    start = time.time()
    all_rows: list[dict[str, Any]] = []
    all_manifests: list[dict[str, Any]] = []
    main_hashes = {}
    model_calls = 0
    raw_col_run_dir = Path(args.raw_col_run_dir)
    for page in pages:
        page_rows, manifests, page_hash, page_calls = await run_page(
            page,
            cfg,
            raw_col_run_dir,
            output_dir,
            runner,
            reuse_crops=bool(args.reuse_crops),
            reuse_sidecars=bool(args.reuse_sidecars),
            padding=int(args.padding),
        )
        all_rows.extend(page_rows)
        all_manifests.extend(manifests)
        main_hashes[str(page["page"])] = page_hash
        model_calls += page_calls
    summary = summarize_true_clean_rows(all_rows)
    sanity = summarize_true_clean_sanity(all_manifests)
    enhanced_results_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "raw_col_run_dir": str(raw_col_run_dir),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "prompt": "PROMPT_COL_OBSERVATION",
        "elapsed_seconds": round(time.time() - start, 3),
        "model_calls": model_calls,
        "padding": int(args.padding),
        "main_result_hashes": main_hashes,
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_results_dir, pages),
        "processor_resize_observable_from_api": False,
    }
    write_true_clean_report(output_dir, all_rows, summary, sanity, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run true clean/native observation crop ablation without changing results.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--raw-col-run-dir", required=True)
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--padding", type=int, default=12)
    parser.add_argument("--reuse-crops", action="store_true")
    parser.add_argument("--reuse-sidecars", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
