from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from . import prompts
from .config import PipelineConfig, load_config
from .json_utils import normalize_nulls, parse_model_json


TARGET_FIELDS = ("入量_静脉用药", "管路护理", "病情观察及处理")

FIELD_IMAGE_SLUGS = {
    "入量_静脉用药": "iv_drug",
    "管路护理": "tube_care",
    "病情观察及处理": "observation",
}

FIELD_PROMPTS = {
    "入量_静脉用药": prompts.PROMPT_COL_IV_DRUG,
    "管路护理": prompts.PROMPT_COL_TUBE_CARE,
    "病情观察及处理": prompts.PROMPT_COL_OBSERVATION,
}

CORRECT_KINDS = {"equal", "canonical_equal"}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def normalize_text_for_eval(value: Any) -> str | None:
    if not _has_value(value):
        return None
    text = str(value)
    replacements = {
        "：": ":",
        "，": ",",
        "；": ";",
        "（": "(",
        "）": ")",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = text.replace(" ", "")
    return text


def classify_diff(gold: Any, actual: Any) -> dict[str, Any]:
    gold_norm = normalize_text_for_eval(gold)
    actual_norm = normalize_text_for_eval(actual)
    if gold == actual:
        kind = "equal"
    elif gold_norm == actual_norm and gold_norm is not None:
        kind = "canonical_equal"
    elif gold_norm is not None and actual_norm is None:
        kind = "missing"
    elif gold_norm is None and actual_norm is not None:
        kind = "overfill"
    elif (
        gold_norm is not None
        and actual_norm is not None
        and gold_norm.replace(";", "") == actual_norm.replace(";", "")
    ):
        kind = "separator_error"
    else:
        kind = "substantive_mismatch"
    return {
        "kind": kind,
        "gold": gold,
        "actual": actual,
        "gold_norm": gold_norm,
        "actual_norm": actual_norm,
    }


def is_correct(kind: str) -> bool:
    return kind in CORRECT_KINDS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        rows = data.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        return [data]
    return []


def by_block(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        block_id = str(row.get("_block_id") or row.get("block_id") or f"idx_{idx}")
        result[block_id] = row
    return result


def build_sidecar_payload(
    block_id: str,
    values: dict[str, Any],
    raw_responses: dict[str, str],
    image_paths: dict[str, str],
    errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"block_id": block_id}
    for field in TARGET_FIELDS:
        payload[field] = normalize_nulls({field: values.get(field)}).get(field)
    payload["_raw_responses"] = {field: raw_responses.get(field, "") for field in TARGET_FIELDS}
    payload["_image_paths"] = {field: image_paths.get(field, "") for field in TARGET_FIELDS}
    if errors:
        payload["_errors"] = errors
    return payload


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {
        field: {
            "main_correct": 0,
            "col_correct": 0,
            "main_wrong_col_correct": 0,
            "main_correct_col_wrong": 0,
            "both_wrong": 0,
            "col_overfill": 0,
            "col_missing": 0,
        }
        for field in TARGET_FIELDS
    }
    for row in rows:
        field = row["field"]
        if field not in summary:
            continue
        main_kind = row["main_eval_kind"]
        col_kind = row["col_vlm_eval_kind"]
        main_ok = is_correct(main_kind)
        col_ok = is_correct(col_kind)
        if main_ok:
            summary[field]["main_correct"] += 1
        if col_ok:
            summary[field]["col_correct"] += 1
        if not main_ok and col_ok:
            summary[field]["main_wrong_col_correct"] += 1
        elif main_ok and not col_ok:
            summary[field]["main_correct_col_wrong"] += 1
        elif not main_ok and not col_ok:
            summary[field]["both_wrong"] += 1
        if col_kind == "overfill":
            summary[field]["col_overfill"] += 1
        if col_kind == "missing":
            summary[field]["col_missing"] += 1
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    text = str(value).replace("\n", "<br>")
    return text.replace("|", "\\|")


def write_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, dict[str, int]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Target Column VLM Report",
        "",
        "## Summary",
        "",
        "| field | main_correct | col_correct | main_wrong_col_correct | main_correct_col_wrong | both_wrong | col_overfill | col_missing |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field in TARGET_FIELDS:
        item = summary[field]
        lines.append(
            f"| {field} | {item['main_correct']} | {item['col_correct']} | "
            f"{item['main_wrong_col_correct']} | {item['main_correct_col_wrong']} | "
            f"{item['both_wrong']} | {item['col_overfill']} | {item['col_missing']} |"
        )
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | field | gold | main_actual | col_vlm_actual | main_eval_kind | col_vlm_eval_kind |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {row['field']} | "
            f"{_md_value(row['gold'])} | {_md_value(row['main_actual'])} | "
            f"{_md_value(row['col_vlm_actual'])} | {row['main_eval_kind']} | "
            f"{row['col_vlm_eval_kind']} |"
        )
    (output_dir / "target_column_vlm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "metadata": metadata or {},
        "summary": summary,
        "rows": rows,
    }
    (output_dir / "target_column_vlm_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    normalized = []
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError(f"page item must be an object: {page!r}")
        normalized.append({
            "page": str(page["page"]),
            "image": str(page["image"]),
            "gold_json": str(page["gold_json"]),
            "main_result_json": str(page["main_result_json"]),
        })
    return normalized


def run_cutter(cfg: PipelineConfig, image_path: Path, output_dir: Path, reuse_slices: bool = False) -> None:
    if reuse_slices and output_dir.exists() and list(output_dir.glob("block_*_col_iv_drug.png")):
        return
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
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
        [str(cfg.ocr_python), "-m", "icu_vllm.cutter_worker_jin", "--img", str(image_path), "--out", str(output_dir)],
        env=env,
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    (output_dir / "_cutter_stdout.txt").write_text(result.stdout, encoding="utf-8")
    (output_dir / "_cutter_stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"target-column cutter failed for {image_path}: {result.stderr}")


class TargetColumnVlmRunner:
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

    async def extract_field(self, image_path: Path, field: str) -> tuple[Any, str, str | None]:
        if not image_path.exists():
            return None, "", f"missing image: {image_path.name}"
        img_b64 = self.encode_image_base64(image_path)
        request_kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            request_kwargs["extra_body"] = {
                "mm_processor_kwargs": self.cfg.mm_processor_kwargs,
            }
        raw = ""
        try:
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": FIELD_PROMPTS[field]},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            raw = response.choices[0].message.content or ""
            data = normalize_nulls(parse_model_json(raw))
            return data.get(field), raw, None
        except Exception as exc:
            return None, raw, str(exc)


def _sort_block_prefix(path: Path) -> tuple[int, str]:
    match = re.search(r"block_(\d+)", path.name)
    return (int(match.group(1)) if match else 999999, path.name)


async def run_page(
    page: dict[str, Any],
    cfg: PipelineConfig,
    runner: TargetColumnVlmRunner,
    output_dir: Path,
    reuse_slices: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    page_label = page["page"]
    image_path = Path(page["image"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)

    slice_dir = output_dir / "slices" / page_label
    sidecar_dir = output_dir / "sidecars" / page_label
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    run_cutter(cfg, image_path, slice_dir, reuse_slices=reuse_slices)

    first_images = sorted(slice_dir.glob("block_*_col_iv_drug.png"), key=_sort_block_prefix)

    async def process_block(first_image: Path) -> None:
        block_id = first_image.stem.rsplit("_col_iv_drug", 1)[0]
        values: dict[str, Any] = {}
        raw_responses: dict[str, str] = {}
        image_paths: dict[str, str] = {}
        errors: dict[str, str] = {}
        tasks = []
        for field in TARGET_FIELDS:
            image_name = f"{block_id}_col_{FIELD_IMAGE_SLUGS[field]}.png"
            image_paths[field] = image_name
            tasks.append((field, slice_dir / image_name))
        results = await asyncio.gather(*(runner.extract_field(path, field) for field, path in tasks))
        for (field, _path), (value, raw, error) in zip(tasks, results):
            values[field] = value
            raw_responses[field] = raw
            if error:
                errors[field] = error
        payload = build_sidecar_payload(block_id, values, raw_responses, image_paths, errors or None)
        (sidecar_dir / f"{block_id}_col_vlm.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    await asyncio.gather(*(process_block(path) for path in first_images))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    sidecar_blocks = by_block(read_rows_from_sidecars(sidecar_dir))
    block_ids = sorted(
        {block_id for block_id in set(gold_blocks) | set(main_blocks) | set(sidecar_blocks) if block_id.startswith("block_")}
    )
    rows: list[dict[str, Any]] = []
    for block_id in block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        sidecar_row = sidecar_blocks.get(block_id, {})
        for field in TARGET_FIELDS:
            main_diff = classify_diff(gold_row.get(field), main_row.get(field))
            col_diff = classify_diff(gold_row.get(field), sidecar_row.get(field))
            rows.append({
                "page": page_label,
                "block_id": block_id,
                "field": field,
                "gold": gold_row.get(field),
                "main_actual": main_row.get(field),
                "col_vlm_actual": sidecar_row.get(field),
                "main_eval_kind": main_diff["kind"],
                "col_vlm_eval_kind": col_diff["kind"],
            })
    after_hash = sha256_file(main_path)
    return rows, {
        "before": before_hash,
        "after": after_hash,
        "unchanged": str(before_hash == after_hash),
        "path": str(main_path),
    }


def read_rows_from_sidecars(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_col_vlm.json"), key=_sort_block_prefix):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    pages = load_pages(Path(args.pages_json))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = TargetColumnVlmRunner(cfg)
    all_rows: list[dict[str, Any]] = []
    hashes: dict[str, dict[str, str]] = {}
    start = time.time()
    for page in pages:
        page_rows, page_hash = await run_page(
            page,
            cfg,
            runner,
            output_dir,
            reuse_slices=bool(args.reuse_slices),
        )
        all_rows.extend(page_rows)
        hashes[page["page"]] = page_hash
    summary = summarize_rows(all_rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
    }
    write_report(output_dir, all_rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run experimental single-column VLM extraction for Jin high-risk fields.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reuse-slices", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
