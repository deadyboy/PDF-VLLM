from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from openai import AsyncOpenAI

from .config import PipelineConfig, load_config
from .json_utils import parse_model_json
from .observation_eval import classify_observation_diff
from .prompts import PROMPT_OBSERVATION_LINE_TRANSCRIBE
from .target_column_observation_compare import OBS_FIELD
from .target_column_vlm import read_json, sha256_file


LINE_PROBE_SOURCES = ("main", "old_col", "line_probe_A", "line_probe_B")
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


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def _sort_line_id(line_id: str) -> tuple[int, str]:
    try:
        return int(line_id), line_id
    except Exception:
        return 999999, line_id


def _sort_block_key(value: str | Path) -> tuple[int, str]:
    name = Path(value).name if isinstance(value, Path) else str(value)
    try:
        return int(name.split("_")[1]), name
    except Exception:
        return 999999, name


def detect_text_line_boxes(
    image: np.ndarray,
    data_top_y: int = 0,
    padding_y: int = 6,
    min_height: int = 4,
    merge_gap: int = 2,
) -> list[dict[str, Any]]:
    image = _ensure_bgr(image)
    h, w = image.shape[:2]
    data_top = max(0, min(int(data_top_y), h - 1))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _threshold, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(24, w // 3), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(24, h // 3)))
    horizontal = cv2.morphologyEx(inv, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    vertical = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    text_mask = cv2.bitwise_and(inv, cv2.bitwise_not(cv2.bitwise_or(horizontal, vertical)))
    text_mask[:data_top, :] = 0
    text_mask = cv2.dilate(text_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1)), iterations=1)

    projection = np.count_nonzero(text_mask, axis=1)
    threshold = max(1, int(w * 0.003))
    active = projection > threshold
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for y, is_active in enumerate(active):
        if is_active and start is None:
            start = y
        elif not is_active and start is not None:
            spans.append((start, y))
            start = None
    if start is not None:
        spans.append((start, h))

    merged: list[tuple[int, int]] = []
    for y1, y2 in spans:
        if y2 - y1 < min_height:
            continue
        if merged and y1 - merged[-1][1] <= merge_gap:
            merged[-1] = (merged[-1][0], y2)
        else:
            merged.append((y1, y2))

    boxes = []
    for idx, (y1, y2) in enumerate(merged, start=1):
        yy1 = max(data_top, y1 - padding_y)
        yy2 = min(h, y2 + padding_y)
        if yy2 <= yy1:
            continue
        boxes.append({
            "line_id": f"{idx:02d}",
            "x1": 0,
            "x2": int(w),
            "y1": int(yy1),
            "y2": int(yy2),
            "ink_y1": int(y1),
            "ink_y2": int(y2),
        })
    return boxes


def _numbered_line_image(crop: np.ndarray, line_id: str, label_width: int = 56) -> np.ndarray:
    crop = _ensure_bgr(crop)
    h, w = crop.shape[:2]
    canvas = np.full((max(28, h), w + label_width + 8, 3), 255, dtype=np.uint8)
    y = (canvas.shape[0] - h) // 2
    canvas[y:y + h, label_width + 8:label_width + 8 + w] = crop
    cv2.putText(canvas, line_id, (8, min(canvas.shape[0] - 8, 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 80), 2, cv2.LINE_AA)
    cv2.line(canvas, (label_width, 0), (label_width, canvas.shape[0] - 1), (210, 210, 210), 1)
    return canvas


def build_line_contact_sheet(crops: list[np.ndarray], line_ids: list[str]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    if not crops:
        return np.full((64, 240, 3), 255, dtype=np.uint8), []
    numbered = [_numbered_line_image(crop, line_id) for crop, line_id in zip(crops, line_ids)]
    width = max(img.shape[1] for img in numbered)
    y = 12
    rows = []
    placements = []
    for line_id, img in zip(line_ids, numbered):
        row = np.full((img.shape[0] + 10, width, 3), 255, dtype=np.uint8)
        row[5:5 + img.shape[0], :img.shape[1]] = img
        rows.append(row)
        placements.append({
            "line_id": line_id,
            "sheet_y1": int(y + 5),
            "sheet_y2": int(y + 5 + img.shape[0]),
            "sheet_x1": 0,
            "sheet_x2": int(img.shape[1]),
        })
        y += row.shape[0]
    return np.vstack(rows), placements


def parse_line_transcription_response(raw: str) -> tuple[dict[str, Any], str | None]:
    try:
        data = parse_model_json(raw)
    except Exception as exc:
        return {"lines": {}, "uncertain_lines": [], "needs_review": True}, str(exc)
    lines = data.get("lines") if isinstance(data, dict) else {}
    normalized: dict[str, str] = {}
    if isinstance(lines, dict):
        for key, value in lines.items():
            key_text = str(key).zfill(2) if str(key).isdigit() else str(key)
            if value is None:
                normalized[key_text] = ""
            else:
                normalized[key_text] = str(value).strip()
    uncertain = data.get("uncertain_lines", []) if isinstance(data, dict) else []
    if not isinstance(uncertain, list):
        uncertain = [uncertain]
    return {
        "lines": dict(sorted(normalized.items(), key=lambda item: _sort_line_id(item[0]))),
        "uncertain_lines": [str(item).zfill(2) if str(item).isdigit() else str(item) for item in uncertain],
        "needs_review": bool(data.get("needs_review", False)) if isinstance(data, dict) else True,
    }, None


def combine_line_texts(lines: dict[str, Any]) -> Any:
    ordered = [str(value).strip() for _key, value in sorted(lines.items(), key=lambda item: _sort_line_id(item[0]))]
    text = "".join(part for part in ordered if part)
    return text if text else None


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


def build_line_probe_row(
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    old_col_value: Any,
    line_probe_a_value: Any,
    line_probe_b_value: Any,
) -> dict[str, Any]:
    values = {
        "main": main_value,
        "old_col": old_col_value,
        "line_probe_A": line_probe_a_value,
        "line_probe_B": line_probe_b_value,
    }
    row = {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "old_col_value": old_col_value,
        "line_probe_A_value": line_probe_a_value,
        "line_probe_B_value": line_probe_b_value,
    }
    for source, value in values.items():
        diff = classify_observation_diff(gold, value)
        row[f"{source}_kind"] = diff["kind"]
        row[f"{source}_metric"] = _metric_for_kind(diff["kind"])
        row[f"{source}_brief_diff"] = diff["brief_diff"]
    return row


def summarize_line_probe_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = {source: {metric: 0 for metric in SUMMARY_METRICS} for source in LINE_PROBE_SOURCES}
    for row in rows:
        for source in LINE_PROBE_SOURCES:
            metric = row.get(f"{source}_metric")
            if metric in SUMMARY_METRICS:
                source_counts[source][metric] += 1
    return {"sources": list(LINE_PROBE_SOURCES), "source_counts": source_counts, "case_count": len(rows)}


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_line_probe_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    sidecars: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar_dir = output_dir / "observation_line_probe_sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for sidecar in sidecars:
        path = sidecar_dir / f"{sidecar['page']}__{sidecar['block_id']}_line_probe.json"
        path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Observation Line-Level Transcription Probe",
        "",
        "说明：本实验只处理 observation residual casebook 中的 residual cases，不覆盖任何结果字段。",
        "",
        "## Summary",
        "",
        "| source | correct | canonical_only | punctuation_only | rewrite_or_paraphrase | missing | overfill | char_level_mismatch | text_equivalent_minor | gold_needs_check |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for source in LINE_PROBE_SOURCES:
        item = summary["source_counts"][source]
        lines.append(
            f"| {source} | {item['correct']} | {item['canonical_only']} | {item['punctuation_only']} | "
            f"{item['rewrite_or_paraphrase']} | {item['missing']} | {item['overfill']} | "
            f"{item['char_level_mismatch']} | {item['text_equivalent_minor']} | {item['gold_needs_check']} |"
        )
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | gold | main_value | old_col_value | line_probe_A_value | line_probe_B_value | main_kind | old_col_kind | line_probe_A_kind | line_probe_B_kind |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
            f"{_md_value(row['main_value'])} | {_md_value(row['old_col_value'])} | "
            f"{_md_value(row['line_probe_A_value'])} | {_md_value(row['line_probe_B_value'])} | "
            f"{row['main_kind']} | {row['old_col_kind']} | {row['line_probe_A_kind']} | {row['line_probe_B_kind']} |"
        )
    (output_dir / "observation_line_probe_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_line_probe_summary.json").write_text(
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            data = json.loads(line)
            if isinstance(data, dict):
                rows.append(data)
    return rows


def _true_clean_paths(true_clean_run_dir: Path, page: str, block_id: str) -> tuple[Path, Path]:
    crop_dir = true_clean_run_dir / "observation_true_clean_crops" / page
    return (
        crop_dir / f"{block_id}_obs_true_clean_native.png",
        crop_dir / f"{block_id}_obs_true_clean_manifest.json",
    )


def _raw_col_path(raw_col_run_dir: Path, page: str, block_id: str) -> Path:
    return raw_col_run_dir / "slices" / page / f"{block_id}_col_observation.png"


def _data_top_from_manifest(manifest_path: Path) -> int:
    if not manifest_path.exists():
        return 0
    data = read_json(manifest_path)
    if isinstance(data, dict):
        return int(data.get("header_bottom_y", 0) or 0)
    return 0


def _write_line_images_for_case(
    case: dict[str, Any],
    true_clean_run_dir: Path,
    raw_col_run_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    page = str(case["page"])
    block_id = str(case["block_id"])
    true_clean_image, true_clean_manifest = _true_clean_paths(true_clean_run_dir, page, block_id)
    source_image = true_clean_image if true_clean_image.exists() else _raw_col_path(raw_col_run_dir, page, block_id)
    source_stage = "true_clean_native" if source_image == true_clean_image else "raw_col_fallback"
    data_top_y = _data_top_from_manifest(true_clean_manifest) if source_stage == "true_clean_native" else 0

    image = cv2.imread(str(source_image))
    if image is None:
        raise RuntimeError(f"OpenCV cannot read observation source image: {source_image}")
    boxes = detect_text_line_boxes(image, data_top_y=data_top_y)
    case_dir = output_dir / "observation_line_probe_lines" / page / block_id
    case_dir.mkdir(parents=True, exist_ok=True)

    line_entries = []
    crops = []
    for zero_idx, box in enumerate(boxes):
        crop = image[box["y1"]:box["y2"], box["x1"]:box["x2"]]
        numbered = _numbered_line_image(crop, box["line_id"])
        name = f"{block_id}_obs_line_{zero_idx:02d}.png"
        cv2.imwrite(str(case_dir / name), numbered)
        crops.append(crop)
        line_entries.append({**box, "image": str((case_dir / name).relative_to(output_dir))})

    contact_sheet, placements = build_line_contact_sheet(crops, [entry["line_id"] for entry in line_entries])
    contact_name = f"{block_id}_obs_lines_contact_sheet.png"
    cv2.imwrite(str(case_dir / contact_name), contact_sheet)

    overlay = image.copy()
    for entry in line_entries:
        cv2.rectangle(overlay, (entry["x1"], entry["y1"]), (entry["x2"] - 1, entry["y2"] - 1), (0, 0, 255), 2)
        cv2.putText(overlay, entry["line_id"], (entry["x1"] + 4, max(18, entry["y1"] - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 180), 2, cv2.LINE_AA)
    overlay_name = f"{block_id}_obs_lines_overlay.png"
    cv2.imwrite(str(case_dir / overlay_name), overlay)

    manifest = {
        "page": page,
        "block_id": block_id,
        "source_image": str(source_image),
        "source_stage": source_stage,
        "data_top_y": int(data_top_y),
        "line_count": len(line_entries),
        "lines": line_entries,
        "contact_sheet": str((case_dir / contact_name).relative_to(output_dir)),
        "contact_sheet_placements": placements,
        "overlay": str((case_dir / overlay_name).relative_to(output_dir)),
    }
    manifest_path = case_dir / f"{block_id}_obs_line_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest"] = str(manifest_path.relative_to(output_dir))
    return manifest


class ObservationLineProbeRunner:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(image_path: Path) -> str:
        return base64.b64encode(image_path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[dict[str, Any], str, str | None]:
        request_kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            request_kwargs["extra_body"] = {"mm_processor_kwargs": self.cfg.mm_processor_kwargs}
        raw = ""
        try:
            image_b64 = self.encode_image_base64(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_OBSERVATION_LINE_TRANSCRIBE},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            raw = response.choices[0].message.content or ""
        except Exception as exc:
            return {"lines": {}, "uncertain_lines": [], "needs_review": True}, raw, str(exc)
        parsed, parse_error = parse_line_transcription_response(raw)
        return parsed, raw, parse_error


async def _run_case(
    case: dict[str, Any],
    line_manifest: dict[str, Any],
    output_dir: Path,
    runner: ObservationLineProbeRunner,
    reuse_sidecars: bool = False,
) -> dict[str, Any]:
    sidecar_path = output_dir / "observation_line_probe_sidecars" / f"{case['page']}__{case['block_id']}_line_probe.json"
    if reuse_sidecars and sidecar_path.exists():
        return read_json(sidecar_path)

    line_results: dict[str, str] = {}
    raw_by_line: dict[str, str] = {}
    errors: dict[str, str] = {}
    for line in line_manifest["lines"]:
        image_path = output_dir / line["image"]
        parsed, raw, error = await runner.extract(image_path)
        raw_by_line[line["line_id"]] = raw
        if error:
            errors[line["line_id"]] = error
        if line["line_id"] in parsed["lines"]:
            line_results[line["line_id"]] = parsed["lines"][line["line_id"]]
        elif parsed["lines"]:
            line_results[line["line_id"]] = next(iter(parsed["lines"].values()))
        else:
            line_results[line["line_id"]] = ""

    contact_path = output_dir / line_manifest["contact_sheet"]
    contact_parsed, contact_raw, contact_error = await runner.extract(contact_path)
    sidecar = {
        "page": case["page"],
        "block_id": case["block_id"],
        "field": OBS_FIELD,
        "gold": case.get("gold"),
        "main_value": case.get("main_value"),
        "old_col_value": case.get("col_observation_value"),
        "line_manifest": line_manifest.get("manifest", ""),
        "source_image": line_manifest.get("source_image", ""),
        "source_stage": line_manifest.get("source_stage", ""),
        "line_count": line_manifest.get("line_count", 0),
        "line_probe_A": {
            "lines": dict(sorted(line_results.items(), key=lambda item: _sort_line_id(item[0]))),
            "final_value": combine_line_texts(line_results),
            "raw_responses": raw_by_line,
            "errors": errors,
        },
        "line_probe_B": {
            "lines": contact_parsed["lines"],
            "final_value": combine_line_texts(contact_parsed["lines"]),
            "uncertain_lines": contact_parsed["uncertain_lines"],
            "needs_review": contact_parsed["needs_review"],
            "_raw_response": contact_raw,
            "_error": contact_error or "",
        },
    }
    return sidecar


def _load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _hash_main_results(pages: list[dict[str, Any]]) -> dict[str, Any]:
    hashes = {}
    for page in pages:
        page_label = str(page["page"])
        path = Path(page["main_result_json"])
        before = sha256_file(path)
        after = sha256_file(path)
        hashes[page_label] = {"path": str(path), "before": before, "after": after, "unchanged": before == after}
    return hashes


def _hash_enhanced_results(enhanced_results_dir: Path | None, pages: list[dict[str, Any]]) -> dict[str, Any]:
    if enhanced_results_dir is None:
        return {}
    hashes = {}
    for page in pages:
        page_label = str(page["page"])
        path = enhanced_results_dir / page_label / "result_enhanced.json"
        if not path.exists():
            hashes[page_label] = {"path": str(path), "exists": False}
            continue
        before = sha256_file(path)
        after = sha256_file(path)
        hashes[page_label] = {"path": str(path), "exists": True, "before": before, "after": after, "unchanged": before == after}
    return hashes


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = read_jsonl(Path(args.residual_cases_jsonl))
    pages = _load_pages(Path(args.pages_json))
    runner = ObservationLineProbeRunner(cfg)
    start = time.time()

    manifests = [
        _write_line_images_for_case(case, Path(args.true_clean_run_dir), Path(args.raw_col_run_dir), output_dir)
        for case in cases
    ]
    sidecars = await asyncio.gather(*(
        _run_case(case, manifest, output_dir, runner, reuse_sidecars=bool(args.reuse_sidecars))
        for case, manifest in zip(cases, manifests)
    ))

    rows = [
        build_line_probe_row(
            page=str(sidecar["page"]),
            block_id=str(sidecar["block_id"]),
            gold=sidecar.get("gold"),
            main_value=sidecar.get("main_value"),
            old_col_value=sidecar.get("old_col_value"),
            line_probe_a_value=sidecar.get("line_probe_A", {}).get("final_value"),
            line_probe_b_value=sidecar.get("line_probe_B", {}).get("final_value"),
        )
        for sidecar in sidecars
    ]
    summary = summarize_line_probe_rows(rows)
    enhanced_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    line_call_count = sum(int(manifest.get("line_count", 0)) for manifest in manifests)
    metadata = {
        "config": str(args.config),
        "residual_cases_jsonl": str(args.residual_cases_jsonl),
        "pages_json": str(args.pages_json),
        "true_clean_run_dir": str(args.true_clean_run_dir),
        "raw_col_run_dir": str(args.raw_col_run_dir),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "prompt": "PROMPT_OBSERVATION_LINE_TRANSCRIBE",
        "case_count": len(cases),
        "model_calls": 0 if args.reuse_sidecars else line_call_count + len(cases),
        "line_image_calls": line_call_count,
        "contact_sheet_calls": len(cases),
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": _hash_main_results(pages),
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_dir, pages),
    }
    write_line_probe_report(output_dir, rows, summary, sidecars, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run observation residual line-level transcription probe.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--residual-cases-jsonl", required=True)
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--true-clean-run-dir", required=True)
    parser.add_argument("--raw-col-run-dir", required=True)
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reuse-sidecars", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
