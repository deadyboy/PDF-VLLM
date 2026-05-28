from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np

from .config import PipelineConfig, load_config
from .json_utils import parse_model_json


OBS_FIELD = "病情观察及处理"
PROMPT_OBSERVATION_HEADER_ROW_TRANSCRIBE = """
这是一张“病情观察及处理”单列的单行切片。
上方是表头，下方只有一行患者记录。

请只转录表头下方这一行的可见文字。
不要把表头文字作为结果。
不要根据上下文补写。
不要总结、不要改写、不要润色。
不要合并其他行。
不要主动添加标点或分号。
如果这一行没有文字，输出 JSON null。
如果某个字看不清，按最接近图像的字符输出，并设置 needs_review=true。

仅输出 JSON：
{
  "row_text": "... 或 null",
  "needs_review": false,
  "reason": ""
}
""".strip()

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
SOURCES = ("qwen_header_row", "ocr_header_row")
KIND_LABELS = {
    "exact_equal": "完全一致",
    "canonical_equal": "规范化一致",
    "punctuation_only": "仅标点差异",
    "text_equivalent_minor": "轻微等价差异",
    "rewrite_or_paraphrase": "改写/概括",
    "missing_text": "漏识别",
    "extra_text": "过填",
    "char_level_mismatch": "字符级错误",
    "gold_needs_check": "金标准需复核",
}


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def _sort_block_key(block_id: str) -> tuple[int, str]:
    try:
        return int(block_id.split("_")[1]), block_id
    except Exception:
        return 999999, block_id


def _sort_row_id(row_id: str) -> tuple[int, str]:
    try:
        return int(row_id), row_id
    except Exception:
        return 999999, row_id


def detect_horizontal_table_lines(image: np.ndarray, min_coverage: float = 0.45) -> list[int]:
    image = _ensure_bgr(image)
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _threshold, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(24, int(w * 0.35)), 1))
    horizontal = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel, iterations=1)
    projection = np.count_nonzero(horizontal, axis=1)
    active = projection >= int(w * min_coverage)
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for y, flag in enumerate(active):
        if flag and start is None:
            start = y
        elif not flag and start is not None:
            spans.append((start, y))
            start = None
    if start is not None:
        spans.append((start, h))
    return [int((y1 + y2 - 1) // 2) for y1, y2 in spans]


def _choose_header_bottom(lines: Sequence[int], image_height: int) -> int:
    usable = [int(y) for y in lines if 5 < y < image_height - 5]
    if len(usable) < 2:
        return min(image_height // 2, 120)
    top = usable[0]
    candidates = [y for y in usable[1:] if y - top >= 45]
    return candidates[0] if candidates else usable[1]


def _row_has_ink(row: np.ndarray, min_dark_pixels: int = 18) -> bool:
    row = _ensure_bgr(row)
    gray = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
    _threshold, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = inv.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(16, int(w * 0.35)), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, int(h * 0.6))))
    horizontal = cv2.morphologyEx(inv, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    vertical = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    text_mask = cv2.bitwise_and(inv, cv2.bitwise_not(cv2.bitwise_or(horizontal, vertical)))
    if text_mask.shape[0] > 8 and text_mask.shape[1] > 8:
        text_mask = text_mask[4:-4, 4:-4]
    return int(np.count_nonzero(text_mask)) >= min_dark_pixels


def _stack_header_and_row(header: np.ndarray, row: np.ndarray, separator_height: int = 4) -> np.ndarray:
    width = max(header.shape[1], row.shape[1])
    parts = []
    for part in (header, row):
        if part.shape[1] == width:
            parts.append(part)
            continue
        canvas = np.full((part.shape[0], width, 3), 255, dtype=np.uint8)
        canvas[:, : part.shape[1]] = part
        parts.append(canvas)
    sep = np.full((separator_height, width, 3), 255, dtype=np.uint8)
    return np.vstack([parts[0], sep, parts[1]])


def crop_header_row_images(
    *,
    image_path: str | Path,
    output_dir: str | Path,
    page: str,
    block_id: str,
    padding_y: int = 2,
) -> dict[str, Any]:
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"cannot read image: {image_path}")
    image = _ensure_bgr(image)
    h, _w = image.shape[:2]
    lines = detect_horizontal_table_lines(image)
    header_bottom = _choose_header_bottom(lines, h)
    header_top = max(0, min(lines[0] - padding_y, header_bottom - 1)) if lines else 0
    header = image[header_top : min(h, header_bottom + padding_y)]
    data_lines = [y for y in lines if y >= header_bottom]
    if not data_lines or data_lines[0] != header_bottom:
        data_lines = [header_bottom] + data_lines
    data_lines = sorted(set(int(y) for y in data_lines if 0 <= y <= h))
    if data_lines[-1] < h - 4:
        data_lines.append(h - 1)

    case_dir = output_dir / "header_row_images" / page / block_id
    case_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    separator_height = 4
    data_start_y_in_image = int(header.shape[0] + separator_height)
    for idx, (y1, y2) in enumerate(zip(data_lines, data_lines[1:])):
        crop_y1 = max(0, y1 - padding_y)
        crop_y2 = min(h, y2 + padding_y)
        row_crop = image[crop_y1:crop_y2]
        if not _row_has_ink(row_crop):
            continue
        row_id = f"{len(rows):02d}"
        combined = _stack_header_and_row(header, row_crop, separator_height=separator_height)
        image_name = f"{block_id}_obs_header_row_{row_id}.png"
        cv2.imwrite(str(case_dir / image_name), combined)
        rows.append({
            "row_id": row_id,
            "source_y1": int(y1),
            "source_y2": int(y2),
            "header_height": int(header.shape[0]),
            "separator_height": separator_height,
            "data_start_y_in_image": data_start_y_in_image,
            "image_path": str((case_dir / image_name).relative_to(output_dir)),
        })

    manifest = {
        "page": page,
        "block_id": block_id,
        "source_image": str(image_path),
        "horizontal_lines": [int(y) for y in lines],
        "header_top_y": int(header_top),
        "header_bottom_y": int(header_bottom),
        "row_count": len(rows),
        "rows": rows,
    }
    manifest_path = case_dir / f"{block_id}_obs_header_row_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.relative_to(output_dir))
    return manifest


def _ocr_bbox_center(bbox: Any) -> tuple[float, float]:
    points = bbox if isinstance(bbox, list) else []
    xs = [float(point[0]) for point in points if isinstance(point, (list, tuple)) and len(point) >= 2]
    ys = [float(point[1]) for point in points if isinstance(point, (list, tuple)) and len(point) >= 2]
    if not xs or not ys:
        return 0.0, 0.0
    return sum(xs) / len(xs), sum(ys) / len(ys)


def normalize_paddle_ocr_items(result: Any) -> list[dict[str, Any]]:
    page_items = result
    if isinstance(result, list) and len(result) == 1 and (result[0] is None or isinstance(result[0], list)):
        page_items = result[0] or []
    items: list[dict[str, Any]] = []
    if not isinstance(page_items, list):
        return items
    for raw_item in page_items:
        if not isinstance(raw_item, (list, tuple)) or len(raw_item) < 2:
            continue
        bbox = raw_item[0]
        text_info = raw_item[1]
        if not isinstance(text_info, (list, tuple)) or not text_info:
            continue
        text = str(text_info[0]).strip()
        if not text:
            continue
        score = float(text_info[1]) if len(text_info) > 1 else None
        center_x, center_y = _ocr_bbox_center(bbox)
        items.append({
            "text": text,
            "bbox": bbox,
            "score": score,
            "center_x": center_x,
            "center_y": center_y,
        })
    return sorted(items, key=lambda item: (float(item["center_y"]), float(item["center_x"])))


def filter_ocr_items_below_header(items: Sequence[dict[str, Any]], data_start_y: float) -> list[dict[str, Any]]:
    return [dict(item) for item in items if float(item.get("center_y", 0.0)) >= data_start_y]


def combine_ocr_items_text(items: Sequence[dict[str, Any]]) -> str | None:
    text = "".join(str(item.get("text", "")).strip() for item in items).strip()
    return text or None


def parse_row_response(raw: str) -> dict[str, Any]:
    data = parse_model_json(raw)
    text = data.get("row_text") if isinstance(data, dict) else None
    if isinstance(text, str):
        value: str | None = text.strip() or None
        if value and value.lower() in {"null", "none"}:
            value = None
    else:
        value = None
    return {
        "row_text": value,
        "needs_review": bool(data.get("needs_review", False)) if isinstance(data, dict) else True,
        "reason": str(data.get("reason", "")) if isinstance(data, dict) else "",
    }


def combine_row_texts(rows: dict[str, Any]) -> str | None:
    parts = []
    for _row_id, value in sorted(rows.items(), key=lambda item: _sort_row_id(item[0])):
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return "".join(parts) if parts else None


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


def build_header_row_probe_row(
    *,
    page: str,
    block_id: str,
    gold: Any,
    old_col_value: Any,
    qwen_value: Any,
    ocr_value: Any,
) -> dict[str, Any]:
    from .observation_eval import classify_observation_diff

    qwen_diff = classify_observation_diff(gold, qwen_value)
    ocr_diff = classify_observation_diff(gold, ocr_value)
    old_col_diff = classify_observation_diff(gold, old_col_value)
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "old_col_value": old_col_value,
        "qwen_header_row_value": qwen_value,
        "ocr_header_row_value": ocr_value,
        "old_col_kind": old_col_diff["kind"],
        "qwen_kind": qwen_diff["kind"],
        "qwen_metric": _metric_for_kind(qwen_diff["kind"]),
        "qwen_brief_diff": qwen_diff["brief_diff"],
        "ocr_kind": ocr_diff["kind"],
        "ocr_metric": _metric_for_kind(ocr_diff["kind"]),
        "ocr_brief_diff": ocr_diff["brief_diff"],
    }


def summarize_header_row_probe_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = {source: {metric: 0 for metric in SUMMARY_METRICS} for source in SOURCES}
    for row in rows:
        qwen_metric = row.get("qwen_metric")
        ocr_metric = row.get("ocr_metric")
        if qwen_metric in SUMMARY_METRICS:
            source_counts["qwen_header_row"][qwen_metric] += 1
        if ocr_metric in SUMMARY_METRICS:
            source_counts["ocr_header_row"][ocr_metric] += 1
    return {"sources": list(SOURCES), "source_counts": source_counts, "case_count": len(rows)}


def _md(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def _kind_label(kind: str) -> str:
    return KIND_LABELS.get(kind, kind)


def write_report(
    output_dir: Path,
    *,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    sidecars: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar_dir = output_dir / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for sidecar in sidecars:
        path = sidecar_dir / f"{sidecar['page']}__{sidecar['block_id']}_header_row_probe.json"
        path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 病情观察 Header + 单行切片识别实验",
        "",
        "说明：每张小图都包含表头和一条数据行；本实验只比较 Qwen3-32B 单行识别与 PaddleOCR，不跑 Qwen-R，不覆盖任何结果。",
        "",
        "## 汇总",
        "",
        "| 来源 | 完全正确 | 规范化一致 | 仅标点差异 | 改写/概括 | 漏识别 | 过填 | 字符级错误 | 轻微等价差异 | 金标准需复核 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for source in SOURCES:
        counts = summary["source_counts"][source]
        label = "Qwen3-32B 表头+单行" if source == "qwen_header_row" else "PaddleOCR 表头+单行"
        lines.append(
            f"| {label} | {counts['correct']} | {counts['canonical_only']} | {counts['punctuation_only']} | "
            f"{counts['rewrite_or_paraphrase']} | {counts['missing']} | {counts['overfill']} | "
            f"{counts['char_level_mismatch']} | {counts['text_equivalent_minor']} | {counts['gold_needs_check']} |"
        )
    lines.extend([
        "",
        "## 明细",
        "",
        "| 页面 | block | gold | 旧单列结果 | Qwen表头+单行拼接 | Qwen评估 | OCR表头+单行拼接 | OCR评估 |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {_md(row['gold'])} | {_md(row['old_col_value'])} | "
            f"{_md(row['qwen_header_row_value'])} | {_kind_label(row['qwen_kind'])} | "
            f"{_md(row['ocr_header_row_value'])} | {_kind_label(row['ocr_kind'])} |"
        )
    (output_dir / "observation_header_row_probe_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_header_row_probe_summary.json").write_text(
        json.dumps({"metadata": metadata, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _load_pages(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
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


class QwenHeaderRowRunner:
    def __init__(self, cfg: PipelineConfig):
        from openai import AsyncOpenAI

        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[dict[str, Any], str, str]:
        kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            kwargs["extra_body"] = {"mm_processor_kwargs": self.cfg.mm_processor_kwargs}
        raw = ""
        try:
            image_b64 = self.encode_image_base64(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_OBSERVATION_HEADER_ROW_TRANSCRIBE},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=1024,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **kwargs,
                )
            raw = response.choices[0].message.content or ""
            return parse_row_response(raw), raw, ""
        except Exception as exc:
            return {"row_text": None, "needs_review": True, "reason": str(exc)}, raw, repr(exc)


async def _run_qwen_for_case(manifest: dict[str, Any], output_dir: Path, runner: QwenHeaderRowRunner) -> dict[str, Any]:
    rows = {}
    raw_responses = {}
    errors = {}
    for row in manifest["rows"]:
        image_path = output_dir / row["image_path"]
        parsed, raw, error = await runner.extract(image_path)
        rows[row["row_id"]] = parsed.get("row_text")
        raw_responses[row["row_id"]] = raw
        if error:
            errors[row["row_id"]] = error
    return {
        "rows": rows,
        "final_value": combine_row_texts(rows),
        "raw_responses": raw_responses,
        "errors": errors,
    }


async def run_qwen_stage(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    output_dir = Path(args.output_dir)
    runner = QwenHeaderRowRunner(cfg)
    sidecars = []
    for manifest_path in sorted((output_dir / "header_row_images").glob("*/*/*_manifest.json")):
        manifest = read_json(manifest_path)
        qwen = await _run_qwen_for_case(manifest, output_dir, runner)
        sidecar_path = output_dir / "sidecars" / f"{manifest['page']}__{manifest['block_id']}_header_row_probe.json"
        sidecar = read_json(sidecar_path) if sidecar_path.exists() else {"page": manifest["page"], "block_id": manifest["block_id"]}
        sidecar["qwen_header_row"] = qwen
        sidecars.append(sidecar)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    return None


def run_ocr_stage(args: argparse.Namespace) -> None:
    from paddleocr import PaddleOCR

    output_dir = Path(args.output_dir)
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
    for manifest_path in sorted((output_dir / "header_row_images").glob("*/*/*_manifest.json")):
        manifest = read_json(manifest_path)
        rows: dict[str, Any] = {}
        raw_items_by_row: dict[str, Any] = {}
        data_items_by_row: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for row in manifest["rows"]:
            row_id = str(row["row_id"])
            image_path = output_dir / row["image_path"]
            try:
                raw_result = ocr.ocr(str(image_path), cls=True)
                raw_items = normalize_paddle_ocr_items(raw_result)
                data_items = filter_ocr_items_below_header(raw_items, float(row.get("data_start_y_in_image", 0)))
                rows[row_id] = combine_ocr_items_text(data_items)
                raw_items_by_row[row_id] = raw_items
                data_items_by_row[row_id] = data_items
            except Exception as exc:
                rows[row_id] = None
                raw_items_by_row[row_id] = []
                data_items_by_row[row_id] = []
                errors[row_id] = repr(exc)

        sidecar_path = output_dir / "sidecars" / f"{manifest['page']}__{manifest['block_id']}_header_row_probe.json"
        sidecar = read_json(sidecar_path) if sidecar_path.exists() else {"page": manifest["page"], "block_id": manifest["block_id"]}
        sidecar["ocr_header_row"] = {
            "rows": rows,
            "final_value": combine_row_texts(rows),
            "raw_items": raw_items_by_row,
            "data_items": data_items_by_row,
            "errors": errors,
        }
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")


def run_crop_stage(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = read_jsonl(Path(args.residual_cases_jsonl))
    if args.page_label:
        cases = [case for case in cases if str(case.get("page")) == args.page_label]
    if args.limit:
        cases = cases[: int(args.limit)]
    sidecars = []
    for case in cases:
        page = str(case["page"])
        block_id = str(case["block_id"])
        image_path = Path(args.target_column_run_dir) / "slices" / page / f"{block_id}_col_observation.png"
        manifest = crop_header_row_images(image_path=image_path, output_dir=output_dir, page=page, block_id=block_id)
        sidecar = {
            "page": page,
            "block_id": block_id,
            "field": OBS_FIELD,
            "gold": case.get("gold"),
            "old_col_value": case.get("col_observation_value"),
            "source_image": str(image_path),
            "manifest_path": manifest["manifest_path"],
            "header_row_manifest": manifest,
        }
        sidecars.append(sidecar)
    sidecar_dir = output_dir / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for sidecar in sidecars:
        (sidecar_dir / f"{sidecar['page']}__{sidecar['block_id']}_header_row_probe.json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def finalize_report(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    sidecars = []
    rows = []
    for path in sorted((output_dir / "sidecars").glob("*_header_row_probe.json")):
        sidecar = read_json(path)
        qwen_value = sidecar.get("qwen_header_row", {}).get("final_value")
        ocr_value = sidecar.get("ocr_header_row", {}).get("final_value")
        rows.append(
            build_header_row_probe_row(
                page=sidecar["page"],
                block_id=sidecar["block_id"],
                gold=sidecar.get("gold"),
                old_col_value=sidecar.get("old_col_value"),
                qwen_value=qwen_value,
                ocr_value=ocr_value,
            )
        )
        sidecars.append(sidecar)
    summary = summarize_header_row_probe_rows(rows)
    pages = _load_pages(Path(args.pages_json)) if args.pages_json else []
    enhanced_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    metadata = {
        "target_column_run_dir": str(args.target_column_run_dir),
        "residual_cases_jsonl": str(args.residual_cases_jsonl),
        "prompt": "PROMPT_OBSERVATION_HEADER_ROW_TRANSCRIBE",
        "case_count": len(rows),
        "main_result_hashes": _hash_main_results(pages),
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_dir, pages),
    }
    write_report(output_dir, rows=rows, summary=summary, sidecars=sidecars, metadata=metadata)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Header + single table-row observation transcription probe.")
    parser.add_argument("--stage", choices=["crop", "ocr", "qwen", "finalize"], required=True)
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--target-column-run-dir", default="/data1/jianf-vllm/runs/target_column_vlm_20260525-074656")
    parser.add_argument("--residual-cases-jsonl", required=True)
    parser.add_argument("--pages-json", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--page-label", default="")
    parser.add_argument("--limit", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    start = time.time()
    if args.stage == "crop":
        run_crop_stage(args)
    elif args.stage == "ocr":
        run_ocr_stage(args)
    elif args.stage == "qwen":
        asyncio.run(run_qwen_stage(args))
    elif args.stage == "finalize":
        finalize_report(args)
    print(f"{args.stage} done in {time.time() - start:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
