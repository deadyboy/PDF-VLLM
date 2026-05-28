from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import PipelineConfig, load_config
from .target_column_iv_rawlines import (
    IV_FIELD,
    IvRawlinesRunner,
    _as_raw_lines,
    read_iv_rawlines_sidecars,
    raw_lines_tail_kind,
)
from .target_column_vlm import (
    classify_diff,
    is_correct,
    read_json,
    read_rows,
    sha256_file,
    by_block,
)


IV_CROP_VARIANT = "clean_2x"


def clean2x_image_name(block_id: str) -> str:
    return f"{block_id}_col_iv_drug_clean_2x.png"


def build_clean2x_row(
    page: str,
    block_id: str,
    gold: Any,
    main_actual: Any,
    old_crop_actual: Any,
    clean2x_actual: Any,
    clean2x_raw_lines: list[str],
    clean2x_needs_review: bool,
    clean2x_reason: str,
    old_crop_raw_lines: list[str] | None = None,
) -> dict[str, Any]:
    main_diff = classify_diff(gold, main_actual)
    old_diff = classify_diff(gold, old_crop_actual)
    clean_diff = classify_diff(gold, clean2x_actual)
    old_raw_lines = old_crop_raw_lines or []
    return {
        "page": page,
        "block_id": block_id,
        "gold": gold,
        "main_actual": main_actual,
        "iv_v2_rawlines_old_crop": old_crop_actual,
        "iv_v2_rawlines_clean_2x": clean2x_actual,
        "main_eval_kind": main_diff["kind"],
        "old_crop_eval_kind": old_diff["kind"],
        "clean_2x_eval_kind": clean_diff["kind"],
        "old_crop_raw_lines": old_raw_lines,
        "clean_2x_raw_lines": clean2x_raw_lines,
        "clean_2x_needs_review": clean2x_needs_review,
        "clean_2x_reason": clean2x_reason or "",
        "old_crop_tail_kind": raw_lines_tail_kind(gold, old_crop_actual, old_raw_lines),
        "clean_2x_tail_kind": raw_lines_tail_kind(gold, clean2x_actual, clean2x_raw_lines),
    }


def _empty_metric_row() -> dict[str, int]:
    return {"old_crop": 0, "clean_2x": 0}


def summarize_clean2x_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {
        "col_correct": _empty_metric_row(),
        "main_wrong_col_correct": _empty_metric_row(),
        "main_correct_col_wrong": _empty_metric_row(),
        "both_wrong": _empty_metric_row(),
        "col_overfill": _empty_metric_row(),
        "col_missing": _empty_metric_row(),
        "raw_lines_contains_tail_but_final_wrong": _empty_metric_row(),
        "raw_lines_missing_tail": _empty_metric_row(),
        "char_level_mismatch": _empty_metric_row(),
    }
    for row in rows:
        main_ok = is_correct(row["main_eval_kind"])
        for label, key, tail_key in (
            ("old_crop", "old_crop_eval_kind", "old_crop_tail_kind"),
            ("clean_2x", "clean_2x_eval_kind", "clean_2x_tail_kind"),
        ):
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
            if kind == "substantive_mismatch":
                summary["char_level_mismatch"][label] += 1
            tail_kind = row.get(tail_key)
            if tail_kind in ("raw_lines_contains_tail_but_final_wrong", "raw_lines_missing_tail"):
                summary[tail_kind][label] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_clean2x_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, int]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Target Column IV Rawlines Clean2x Report",
        "",
        "## Summary",
        "",
        "| metric | old_crop | clean_2x |",
        "| --- | ---: | ---: |",
    ]
    for metric, values in summary.items():
        lines.append(f"| {metric} | {values['old_crop']} | {values['clean_2x']} |")
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_actual | iv_v2_rawlines_old_crop | iv_v2_rawlines_clean_2x | main_eval_kind | old_crop_eval_kind | clean_2x_eval_kind | old_crop_raw_lines | clean_2x_raw_lines | clean_2x_needs_review | clean_2x_reason | old_crop_tail_kind | clean_2x_tail_kind |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        old_lines = json.dumps(row.get("old_crop_raw_lines", []), ensure_ascii=False)
        clean_lines = json.dumps(row.get("clean_2x_raw_lines", []), ensure_ascii=False)
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_actual'])} | {_md_value(row['iv_v2_rawlines_old_crop'])} | "
            f"{_md_value(row['iv_v2_rawlines_clean_2x'])} | {row['main_eval_kind']} | "
            f"{row['old_crop_eval_kind']} | {row['clean_2x_eval_kind']} | "
            f"{_md_value(old_lines)} | {_md_value(clean_lines)} | {row['clean_2x_needs_review']} | "
            f"{_md_value(row['clean_2x_reason'])} | {row['old_crop_tail_kind']} | {row['clean_2x_tail_kind']} |"
        )
    (output_dir / "target_column_iv_rawlines_clean2x_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    payload = {"metadata": metadata or {}, "summary": summary, "rows": rows}
    (output_dir / "target_column_iv_rawlines_clean2x_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def run_crop_worker(cfg: PipelineConfig, image_path: Path, crop_dir: Path, reuse_crops: bool = False) -> None:
    if reuse_crops and crop_dir.exists() and list(crop_dir.glob("block_*_col_iv_drug_clean_2x.png")):
        return
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(project_root)
        if not existing_pythonpath
        else f"{project_root}{os.pathsep}{existing_pythonpath}"
    )
    result = subprocess.run(
        [str(cfg.ocr_python), "-m", "icu_vllm.iv_clean2x_crop_worker", "--img", str(image_path), "--out", str(crop_dir)],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if crop_dir.exists():
        (crop_dir / "_crop_stdout.txt").write_text(result.stdout, encoding="utf-8")
        (crop_dir / "_crop_stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"clean_2x crop worker failed for {image_path}: {result.stderr}")


def _block_sort_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.name.split("_")[1]), path.name
    except Exception:
        return 999999, path.name


async def run_page(
    page: dict[str, Any],
    cfg: PipelineConfig,
    old_iv_rawlines_run_dir: Path,
    output_dir: Path,
    runner: IvRawlinesRunner,
    reuse_crops: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    image_path = Path(page["image"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    crop_dir = output_dir / "crops" / page_label
    sidecar_dir = output_dir / "sidecars" / page_label
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    run_crop_worker(cfg, image_path, crop_dir, reuse_crops=reuse_crops)

    async def process_image(path: Path) -> None:
        block_id = path.stem.rsplit("_col_iv_drug_clean_2x", 1)[0]
        raw_lines, final_value, needs_review, reason, raw, error = await runner.extract(path)
        payload = {
            "block_id": block_id,
            "field": IV_FIELD,
            "crop_variant": IV_CROP_VARIANT,
            "raw_lines": raw_lines,
            "final_value": final_value,
            "needs_review": bool(needs_review),
            "reason": reason or "",
            "_raw_response": raw,
            "_image_path": str(path.relative_to(output_dir)),
        }
        if error:
            payload["_error"] = error
        (sidecar_dir / f"{block_id}_col_iv_drug_clean_2x_rawlines.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    images = sorted(crop_dir.glob("block_*_col_iv_drug_clean_2x.png"), key=_block_sort_key)
    await asyncio.gather(*(process_image(path) for path in images))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    old_blocks = by_block(read_iv_rawlines_sidecars(old_iv_rawlines_run_dir / "sidecars" / page_label))
    clean_blocks = by_block(read_clean2x_sidecars(sidecar_dir))
    block_ids = sorted(
        {block_id for block_id in set(gold_blocks) | set(main_blocks) | set(old_blocks) | set(clean_blocks) if block_id.startswith("block_")}
    )
    rows = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        old_row = old_blocks.get(block_id, {})
        clean_row = clean_blocks.get(block_id, {})
        rows.append(build_clean2x_row(
            page=page_label,
            block_id=block_id,
            gold=gold_row.get(IV_FIELD),
            main_actual=main_row.get(IV_FIELD),
            old_crop_actual=old_row.get("final_value"),
            clean2x_actual=clean_row.get("final_value"),
            clean2x_raw_lines=_as_raw_lines(clean_row.get("raw_lines")),
            clean2x_needs_review=bool(clean_row.get("needs_review", False)),
            clean2x_reason=str(clean_row.get("reason") or ""),
            old_crop_raw_lines=_as_raw_lines(old_row.get("raw_lines")),
        ))
    after_hash = sha256_file(main_path)
    return rows, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "clean_2x_images": len(images),
        "clean_2x_sidecars": len(list(sidecar_dir.glob("block_*_col_iv_drug_clean_2x_rawlines.json"))),
    }


def read_clean2x_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_col_iv_drug_clean_2x_rawlines.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(Path(args.pages_json))
    old_run_dir = Path(args.old_iv_rawlines_run_dir)
    runner = IvRawlinesRunner(cfg)
    start = time.time()
    rows: list[dict[str, Any]] = []
    hashes: dict[str, Any] = {}
    for page in pages:
        page_rows, page_hash = await run_page(
            page,
            cfg,
            old_run_dir,
            output_dir,
            runner,
            reuse_crops=bool(args.reuse_crops),
        )
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hash
    summary = summarize_clean2x_rows(rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "old_iv_rawlines_run_dir": str(old_run_dir),
        "crop_variant": IV_CROP_VARIANT,
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
    }
    write_clean2x_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run clean 2x IV crop ablation with the raw-lines prompt.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--old-iv-rawlines-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reuse-crops", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
