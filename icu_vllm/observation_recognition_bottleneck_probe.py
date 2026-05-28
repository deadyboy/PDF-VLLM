from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np

from .config import PipelineConfig, load_config
from .observation_header_row_probe import (
    combine_ocr_items_text,
    combine_row_texts,
    normalize_paddle_ocr_items,
    read_json,
    sha256_file,
)
from .observation_row_prompt_ablation import (
    PRECISION_TRANSCRIPTION_PROMPT,
    classify_raw_text_diff,
    parse_precise_transcription_response,
)


IMAGE_VARIANTS = (
    "row_only_original",
    "row_only_canvas_h48",
    "row_only_canvas_h64",
    "row_only_canvas_h96",
)
IMAGE_VARIANT_LABELS = {
    "row_only_original": "原始正文窄带",
    "row_only_canvas_h48": "固定文字高48",
    "row_only_canvas_h64": "固定文字高64",
    "row_only_canvas_h96": "固定文字高96",
}
OCR_MODES = ("det_rec", "rec_only")
METHOD_LABELS = {
    "PaddleOCR:det_rec": "PaddleOCR det+rec",
    "PaddleOCR:rec_only": "PaddleOCR rec-only",
    "Qwen3-32B:precise_transcription_prompt": "Qwen精密prompt",
}


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def snapshot_file_hash(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    before = sha256_file(path)
    after = sha256_file(path)
    return {"path": str(path), "before": before, "after": after, "unchanged": before == after}


def _text_mask_without_long_lines(image: np.ndarray) -> np.ndarray:
    image = _ensure_bgr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _threshold, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = inv.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(14, int(w * 0.35)), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, int(h * 0.65))))
    horizontal = cv2.morphologyEx(inv, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    vertical = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    return cv2.bitwise_and(inv, cv2.bitwise_not(cv2.bitwise_or(horizontal, vertical)))


def _find_text_bbox(image: np.ndarray) -> tuple[int, int, int, int] | None:
    mask = _text_mask_without_long_lines(image)
    points = cv2.findNonZero(mask)
    if points is None:
        return None
    x, y, w, h = cv2.boundingRect(points)
    if w <= 0 or h <= 0:
        return None
    return int(x), int(y), int(x + w), int(y + h)


def _paste_on_canvas(image: np.ndarray, padding: int = 14) -> np.ndarray:
    image = _ensure_bgr(image)
    h, w = image.shape[:2]
    canvas = np.full((h + padding * 2, w + padding * 2, 3), 255, dtype=np.uint8)
    canvas[padding : padding + h, padding : padding + w] = image
    return canvas


def create_normalized_canvas_variants(
    *,
    row_only_image_path: str | Path,
    output_dir: str | Path,
    page: str,
    block_id: str,
    row_id: str,
    target_text_heights: Sequence[int] = (48, 64, 96),
    canvas_padding_px: int = 14,
) -> dict[str, dict[str, Any]]:
    row_only_image_path = Path(row_only_image_path)
    output_dir = Path(output_dir)
    image = cv2.imread(str(row_only_image_path))
    if image is None:
        raise ValueError(f"cannot read image: {row_only_image_path}")
    image = _ensure_bgr(image)
    h, w = image.shape[:2]
    bbox = _find_text_bbox(image)
    if bbox is None:
        estimated_text_height = max(1, h)
        source = "fallback_full_crop_height"
    else:
        _x1, y1, _x2, y2 = bbox
        estimated_text_height = max(1, int(y2 - y1))
        source = "text_bbox_height"
    case_dir = output_dir / "input_images" / page / block_id / f"row_{row_id}"
    case_dir.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict[str, Any]] = {}
    for target in target_text_heights:
        scale = float(target) / float(estimated_text_height)
        resized = cv2.resize(image, (max(1, int(round(w * scale))), max(1, int(round(h * scale)))), interpolation=cv2.INTER_CUBIC)
        canvas = _paste_on_canvas(resized, padding=int(canvas_padding_px))
        name = f"row_only_canvas_h{int(target)}"
        path = case_dir / f"{block_id}_row_{row_id}_{name}.png"
        cv2.imwrite(str(path), canvas)
        variants[name] = {
            "image_variant": name,
            "image_path": _relative(path, output_dir),
            "source": source,
            "target_text_height_px": int(target),
            "estimated_text_height_px": int(estimated_text_height),
            "scale": scale,
            "size": [int(canvas.shape[1]), int(canvas.shape[0])],
            "source_size": [int(w), int(h)],
        }
    return variants


def _box_points(box: Any) -> list[list[float]]:
    if isinstance(box, dict):
        box = box.get("bbox", [])
    if not isinstance(box, list):
        return []
    points = []
    for point in box:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            points.append([float(point[0]), float(point[1])])
    return points


def draw_detection_overlay(*, image_path: str | Path, boxes: Sequence[Any], output_path: str | Path) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"cannot read image: {image_path}")
    image = _ensure_bgr(image)
    for box in boxes:
        points = _box_points(box)
        if len(points) < 4:
            continue
        pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(image, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)


def build_ocr_record(
    *,
    page: str,
    block_id: str,
    row_id: str,
    image_variant: str,
    ocr_mode: str,
    text: Any,
    raw_output: Any,
    detected_box_count: int,
    confidence: float | None,
    parse_error: str,
) -> dict[str, Any]:
    return {
        "page": page,
        "block_id": block_id,
        "row_id": row_id,
        "image_variant": image_variant,
        "source": "PaddleOCR",
        "ocr_mode": ocr_mode,
        "method_id": f"PaddleOCR:{ocr_mode}",
        "text": text,
        "raw_output": raw_output,
        "detected_box_count": int(detected_box_count),
        "confidence": confidence,
        "parse_error": parse_error,
        "skipped": False,
    }


def build_rec_only_skip_record(
    *,
    page: str,
    block_id: str,
    row_id: str,
    image_variant: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "page": page,
        "block_id": block_id,
        "row_id": row_id,
        "image_variant": image_variant,
        "source": "PaddleOCR",
        "ocr_mode": "rec_only",
        "method_id": "PaddleOCR:rec_only",
        "text": None,
        "raw_output": None,
        "detected_box_count": 0,
        "confidence": None,
        "parse_error": "",
        "skipped": True,
        "skip_reason": reason,
    }


def build_vlm_record(
    *,
    page: str,
    block_id: str,
    row_id: str,
    image_variant: str,
    text: Any,
    raw_response: str,
    parsed: Any,
    parse_error: str,
) -> dict[str, Any]:
    return {
        "page": page,
        "block_id": block_id,
        "row_id": row_id,
        "image_variant": image_variant,
        "source": "Qwen3-32B",
        "prompt_name": "precise_transcription_prompt",
        "method_id": "Qwen3-32B:precise_transcription_prompt",
        "text": text,
        "raw_response": raw_response,
        "parsed": parsed,
        "parse_error": parse_error,
    }


def _parse_det_only_boxes(result: Any) -> list[Any]:
    if result is None:
        return []
    data = result
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        data = data[0]
    if not isinstance(data, list):
        return []
    boxes = []
    for item in data:
        if isinstance(item, dict) and "bbox" in item:
            boxes.append(item["bbox"])
        elif isinstance(item, list) and item and isinstance(item[0], (list, tuple)):
            # det-only returns boxes; det+rec items have [bbox, (text, score)].
            if len(item) >= 2 and isinstance(item[1], (list, tuple)) and item[1] and isinstance(item[1][0], str):
                boxes.append(item[0])
            else:
                boxes.append(item)
    return boxes


def _join_rec_only_text(result: Any) -> tuple[str | None, float | None, Any]:
    data = result
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        data = data[0]
    texts: list[str] = []
    scores: list[float] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (list, tuple)) and item:
                if isinstance(item[0], str):
                    texts.append(item[0])
                    if len(item) > 1:
                        scores.append(float(item[1]))
                elif len(item) >= 2 and isinstance(item[1], (list, tuple)) and item[1] and isinstance(item[1][0], str):
                    texts.append(item[1][0])
                    if len(item[1]) > 1:
                        scores.append(float(item[1][1]))
    text = "".join(t.strip() for t in texts).strip() or None
    confidence = round(sum(scores) / len(scores), 4) if scores else None
    return text, confidence, data


def _average_confidence(items: Sequence[dict[str, Any]]) -> float | None:
    scores = [float(item["score"]) for item in items if item.get("score") is not None]
    return round(sum(scores) / len(scores), 4) if scores else None


def _copy_row_only_original(
    *,
    source_run_dir: Path,
    source_info: dict[str, Any],
    output_dir: Path,
    page: str,
    block_id: str,
    row_id: str,
) -> dict[str, Any]:
    source_path = source_run_dir / source_info["image_path"]
    case_dir = output_dir / "input_images" / page / block_id / f"row_{row_id}"
    case_dir.mkdir(parents=True, exist_ok=True)
    dest = case_dir / f"{block_id}_row_{row_id}_row_only_original.png"
    shutil.copy2(source_path, dest)
    image = cv2.imread(str(dest))
    if image is None:
        raise ValueError(f"cannot read copied image: {dest}")
    return {
        "image_variant": "row_only_original",
        "image_path": _relative(dest, output_dir),
        "source": "previous_row_prompt_ablation_row_only_crop",
        "source_path": str(source_path),
        "size": [int(image.shape[1]), int(image.shape[0])],
    }


def _write_contact_sheet(output_dir: Path, sidecars: list[dict[str, Any]]) -> str:
    first = next((sidecar for sidecar in sidecars if sidecar.get("rows")), None)
    if not first:
        return ""
    row = first["rows"][0]
    images: list[np.ndarray] = []
    labels: list[str] = []
    for variant in IMAGE_VARIANTS:
        info = row["image_variants"].get(variant)
        if not info:
            continue
        image = cv2.imread(str(output_dir / info["image_path"]))
        if image is None:
            continue
        h, w = image.shape[:2]
        scale = min(1.0, 430 / max(w, 1))
        image = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
        images.append(image)
        labels.append(variant)
    if not images:
        return ""
    tile_w = max(image.shape[1] for image in images)
    tile_h = max(image.shape[0] for image in images) + 32
    sheet = np.full((tile_h, tile_w * len(images), 3), 255, dtype=np.uint8)
    for idx, image in enumerate(images):
        x = idx * tile_w
        cv2.putText(sheet, labels[idx], (x + 8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 1, cv2.LINE_AA)
        sheet[32 : 32 + image.shape[0], x : x + image.shape[1]] = image
    path = output_dir / "recognition_bottleneck_contact_sheet.png"
    cv2.imwrite(str(path), sheet)
    return _relative(path, output_dir)


def run_crop_stage(args: argparse.Namespace) -> None:
    source_run_dir = Path(args.source_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecars: list[dict[str, Any]] = []
    source_sidecars = sorted((source_run_dir / "sidecars").glob("*_row_prompt_ablation.json"))
    if args.limit:
        source_sidecars = source_sidecars[: int(args.limit)]
    for source_sidecar_path in source_sidecars:
        source_sidecar = read_json(source_sidecar_path)
        page = str(source_sidecar["page"])
        block_id = str(source_sidecar["block_id"])
        rows = []
        for source_row in source_sidecar.get("rows", []):
            row_id = str(source_row["row_id"])
            source_info = source_row["variants"]["row_only_crop"]
            original = _copy_row_only_original(
                source_run_dir=source_run_dir,
                source_info=source_info,
                output_dir=output_dir,
                page=page,
                block_id=block_id,
                row_id=row_id,
            )
            canvases = create_normalized_canvas_variants(
                row_only_image_path=output_dir / original["image_path"],
                output_dir=output_dir,
                page=page,
                block_id=block_id,
                row_id=row_id,
                target_text_heights=(48, 64, 96),
            )
            variants = {"row_only_original": original, **canvases}
            rows.append({"row_id": row_id, "source_row": source_row, "image_variants": variants})
        sidecar = {
            "page": page,
            "block_id": block_id,
            "field": source_sidecar.get("field", "病情观察及处理"),
            "gold": source_sidecar.get("gold"),
            "old_col_value": source_sidecar.get("old_col_value"),
            "source_sidecar": str(source_sidecar_path),
            "rows": rows,
            "ocr_records": [],
            "vlm_records": [],
            "det_observe_records": [],
            "high_dpi_status": {
                "status": "skipped",
                "reason": "previous row-only sidecars contain crop-image coordinates, not stable source PDF page rectangles; high DPI PDF row recrop was not attempted in this diagnostic run",
            },
        }
        sidecars.append(sidecar)
    contact_sheet = _write_contact_sheet(output_dir, sidecars)
    sidecar_dir = output_dir / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for sidecar in sidecars:
        sidecar["contact_sheet"] = contact_sheet
        path = sidecar_dir / f"{sidecar['page']}__{sidecar['block_id']}_recognition_bottleneck.json"
        path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")


def _sidecar_paths(output_dir: Path) -> list[Path]:
    return sorted((output_dir / "sidecars").glob("*_recognition_bottleneck.json"))


def _run_det_observe(ocr: Any, image_path: Path, output_dir: Path, info: dict[str, Any], sidecar: dict[str, Any], row_id: str) -> dict[str, Any]:
    page = sidecar["page"]
    block_id = sidecar["block_id"]
    variant = info["image_variant"]
    overlay_rel = f"ocr_detection_overlays/{page}/{block_id}/row_{row_id}_{variant}_det.png"
    overlay_path = output_dir / overlay_rel
    parse_error = ""
    try:
        det_result = ocr.ocr(str(image_path), det=True, rec=False, cls=False)
        boxes = _parse_det_only_boxes(det_result)
        raw_output = det_result
    except Exception as exc:
        boxes = []
        raw_output = None
        parse_error = repr(exc)
    try:
        draw_detection_overlay(image_path=image_path, boxes=boxes, output_path=overlay_path)
    except Exception as exc:
        parse_error = f"{parse_error}; overlay={exc!r}" if parse_error else f"overlay={exc!r}"
    return {
        "page": page,
        "block_id": block_id,
        "row_id": row_id,
        "image_variant": variant,
        "ocr_mode": "det_observe",
        "detected_box_count": len(boxes),
        "boxes": boxes,
        "raw_output": raw_output,
        "overlay_path": overlay_rel,
        "parse_error": parse_error,
        "skipped": False,
    }


def run_ocr_stage(args: argparse.Namespace) -> None:
    from paddleocr import PaddleOCR

    output_dir = Path(args.output_dir)
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
    rec_only_unavailable_reason = ""
    for path in _sidecar_paths(output_dir):
        sidecar = read_json(path)
        ocr_records = []
        det_observe_records = []
        for row in sidecar.get("rows", []):
            row_id = str(row["row_id"])
            for variant, info in row["image_variants"].items():
                image_path = output_dir / info["image_path"]
                det_observe_records.append(_run_det_observe(ocr, image_path, output_dir, info, sidecar, row_id))
                try:
                    raw_result = ocr.ocr(str(image_path), cls=True)
                    items = normalize_paddle_ocr_items(raw_result)
                    text = combine_ocr_items_text(items)
                    confidence = _average_confidence(items)
                    error = ""
                except Exception as exc:
                    raw_result = None
                    items = []
                    text = None
                    confidence = None
                    error = repr(exc)
                ocr_records.append(
                    build_ocr_record(
                        page=sidecar["page"],
                        block_id=sidecar["block_id"],
                        row_id=row_id,
                        image_variant=variant,
                        ocr_mode="det_rec",
                        text=text,
                        raw_output={"raw_result": raw_result, "items": items},
                        detected_box_count=len(items),
                        confidence=confidence,
                        parse_error=error,
                    )
                )
                if rec_only_unavailable_reason:
                    ocr_records.append(
                        build_rec_only_skip_record(
                            page=sidecar["page"],
                            block_id=sidecar["block_id"],
                            row_id=row_id,
                            image_variant=variant,
                            reason=rec_only_unavailable_reason,
                        )
                    )
                    continue
                try:
                    rec_result = ocr.ocr(str(image_path), det=False, rec=True, cls=False)
                    rec_text, rec_confidence, rec_raw = _join_rec_only_text(rec_result)
                    ocr_records.append(
                        build_ocr_record(
                            page=sidecar["page"],
                            block_id=sidecar["block_id"],
                            row_id=row_id,
                            image_variant=variant,
                            ocr_mode="rec_only",
                            text=rec_text,
                            raw_output={"raw_result": rec_raw},
                            detected_box_count=1 if rec_text else 0,
                            confidence=rec_confidence,
                            parse_error="",
                        )
                    )
                except Exception as exc:
                    rec_only_unavailable_reason = repr(exc)
                    ocr_records.append(
                        build_rec_only_skip_record(
                            page=sidecar["page"],
                            block_id=sidecar["block_id"],
                            row_id=row_id,
                            image_variant=variant,
                            reason=rec_only_unavailable_reason,
                        )
                    )
        sidecar["ocr_records"] = ocr_records
        sidecar["det_observe_records"] = det_observe_records
        path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")


class QwenRunner:
    def __init__(self, cfg: PipelineConfig):
        from openai import AsyncOpenAI

        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def _encode_image(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[dict[str, Any], str, str]:
        kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            kwargs["extra_body"] = {"mm_processor_kwargs": self.cfg.mm_processor_kwargs}
        raw = ""
        try:
            image_b64 = self._encode_image(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PRECISION_TRANSCRIPTION_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=1024,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **kwargs,
                )
            raw = response.choices[0].message.content or ""
            parsed = parse_precise_transcription_response(raw)
            return parsed, raw, parsed.get("parse_error", "")
        except Exception as exc:
            return {"transcription": None, "uncertain_spans": [], "visual_quality_note": "", "parse_error": repr(exc)}, raw, repr(exc)


async def _run_qwen_for_sidecar(output_dir: Path, path: Path, runner: QwenRunner) -> None:
    sidecar = read_json(path)
    tasks = []
    task_meta = []
    for row in sidecar.get("rows", []):
        row_id = str(row["row_id"])
        for variant, info in row["image_variants"].items():
            tasks.append(runner.extract(output_dir / info["image_path"]))
            task_meta.append((row_id, variant))
    results = await asyncio.gather(*tasks)
    records = []
    for (row_id, variant), (parsed, raw, error) in zip(task_meta, results):
        records.append(
            build_vlm_record(
                page=sidecar["page"],
                block_id=sidecar["block_id"],
                row_id=row_id,
                image_variant=variant,
                text=parsed.get("transcription") if isinstance(parsed, dict) else None,
                raw_response=raw,
                parsed=parsed,
                parse_error=error or "",
            )
        )
    sidecar["vlm_records"] = records
    path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")


async def run_qwen_stage(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    output_dir = Path(args.output_dir)
    runner = QwenRunner(cfg)
    for path in _sidecar_paths(output_dir):
        await _run_qwen_for_sidecar(output_dir, path, runner)


def _sort_row_id(row_id: str) -> tuple[int, str]:
    try:
        return int(row_id), row_id
    except Exception:
        return 999999, row_id


def _combine_texts(records: list[dict[str, Any]]) -> str | None:
    rows = {str(record["row_id"]): record.get("text") for record in records if not record.get("skipped")}
    return combine_row_texts(rows)


def _group_eval_records(sidecar: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in sidecar.get("ocr_records", []):
        if record.get("ocr_mode") in OCR_MODES:
            grouped[(record["image_variant"], record["method_id"])].append(record)
    for record in sidecar.get("vlm_records", []):
        grouped[(record["image_variant"], record["method_id"])].append(record)
    return grouped


def _case_rows(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = _group_eval_records(sidecar)
    rows = []
    method_ids = ("PaddleOCR:det_rec", "PaddleOCR:rec_only", "Qwen3-32B:precise_transcription_prompt")
    for variant in IMAGE_VARIANTS:
        for method_id in method_ids:
            records = grouped.get((variant, method_id), [])
            skipped = bool(records) and all(record.get("skipped") for record in records)
            value = None if skipped else _combine_texts(records)
            diff = classify_raw_text_diff(sidecar.get("gold"), value)
            rows.append({
                "case_id": f"{sidecar['page']}__{sidecar['block_id']}",
                "page": sidecar["page"],
                "block_id": sidecar["block_id"],
                "gold": sidecar.get("gold"),
                "image_variant": variant,
                "image_variant_label": IMAGE_VARIANT_LABELS.get(variant, variant),
                "method_id": method_id,
                "method_label": METHOD_LABELS.get(method_id, method_id),
                "recognized_text": value,
                "skipped": skipped,
                "skip_reason": records[0].get("skip_reason", "") if skipped and records else "",
                "row_record_count": len(records),
                **diff,
            })
    return rows


def _det_rows(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    det_observe_by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sidecar.get("det_observe_records", []):
        det_observe_by_variant[record["image_variant"]].append(record)
    det_rec_by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sidecar.get("ocr_records", []):
        if record.get("ocr_mode") == "det_rec":
            det_rec_by_variant[record["image_variant"]].append(record)
    for variant in IMAGE_VARIANTS:
        det_records = det_rec_by_variant.get(variant, [])
        det_observe_records = det_observe_by_variant.get(variant, [])
        rows.append({
            "case_id": f"{sidecar['page']}__{sidecar['block_id']}",
            "page": sidecar["page"],
            "block_id": sidecar["block_id"],
            "image_variant": variant,
            "image_variant_label": IMAGE_VARIANT_LABELS.get(variant, variant),
            "row_count": len(det_records),
            "detected_box_total": sum(int(record.get("detected_box_count", 0)) for record in det_records),
            "zero_box_rows": sum(1 for record in det_records if int(record.get("detected_box_count", 0)) == 0),
            "det_only_parse_errors": [record.get("parse_error") for record in det_observe_records if record.get("parse_error")],
        })
    return rows


def summarize_case_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["image_variant"], row["method_id"])
        item = summary.setdefault(
            key,
            {
                "image_variant": row["image_variant"],
                "image_variant_label": row["image_variant_label"],
                "method_id": row["method_id"],
                "method_label": row["method_label"],
                "case_count": 0,
                "完全一致": 0,
                "仅标点/空格差异": 0,
                "字符级错误": 0,
                "漏识别": 0,
                "过填": 0,
                "改写/概括": 0,
                "skipped": 0,
                "edit_distance_total": 0,
            },
        )
        item["case_count"] += 1
        if row.get("skipped"):
            item["skipped"] += 1
            continue
        item[row["error_type"]] += 1
        item["edit_distance_total"] += int(row["edit_distance"])
    values = []
    for item in summary.values():
        denom = max(1, item["case_count"] - item["skipped"])
        item["平均编辑距离"] = round(item["edit_distance_total"] / denom, 2)
        values.append(item)
    return {"by_variant_method": sorted(values, key=lambda item: (item["image_variant"], item["method_id"]))}


def summarize_det_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = summary.setdefault(
            row["image_variant"],
            {
                "image_variant": row["image_variant"],
                "image_variant_label": row["image_variant_label"],
                "case_count": 0,
                "row_count": 0,
                "detected_box_total": 0,
                "zero_box_rows": 0,
                "det_only_parse_error_count": 0,
            },
        )
        item["case_count"] += 1
        item["row_count"] += int(row["row_count"])
        item["detected_box_total"] += int(row["detected_box_total"])
        item["zero_box_rows"] += int(row["zero_box_rows"])
        item["det_only_parse_error_count"] += len(row.get("det_only_parse_errors", []))
    values = []
    for item in summary.values():
        item["avg_boxes_per_row"] = round(item["detected_box_total"] / max(1, item["row_count"]), 2)
        values.append(item)
    return sorted(values, key=lambda item: item["image_variant"])


def _load_pages(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not str(path):
        return []
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _hash_main_results(pages: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(page["page"]): snapshot_file_hash(Path(page["main_result_json"])) for page in pages}


def _hash_enhanced_results(enhanced_results_dir: Path | None, pages: list[dict[str, Any]]) -> dict[str, Any]:
    if enhanced_results_dir is None:
        return {}
    hashes = {}
    for page in pages:
        page_label = str(page["page"])
        path = enhanced_results_dir / page_label / "result_enhanced.json"
        hashes[page_label] = snapshot_file_hash(path) if path.exists() else {"path": str(path), "exists": False}
    return hashes


def _md(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def _summary_lookup(summary_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["image_variant"], row["method_id"]): row for row in summary_rows}


def derive_key_judgments(summary_rows: list[dict[str, Any]], det_summary: list[dict[str, Any]], high_dpi_status: dict[str, Any]) -> list[str]:
    lookup = _summary_lookup(summary_rows)
    det_lookup = {row["image_variant"]: row for row in det_summary}
    ocr_orig = lookup.get(("row_only_original", "PaddleOCR:det_rec"))
    rec_orig = lookup.get(("row_only_original", "PaddleOCR:rec_only"))
    ocr_h64 = lookup.get(("row_only_canvas_h64", "PaddleOCR:det_rec"))
    qwen_orig = lookup.get(("row_only_original", "Qwen3-32B:precise_transcription_prompt"))
    qwen_h96 = lookup.get(("row_only_canvas_h96", "Qwen3-32B:precise_transcription_prompt"))
    det_orig = det_lookup.get("row_only_original")
    return [
        f"- PaddleOCR 漏识别来源：原始 row-only det+rec 漏识别 {ocr_orig['漏识别'] if ocr_orig else 'NA'} 个；det+rec 原始 row-only 零检测行 {det_orig['zero_box_rows'] if det_orig else 'NA'} / {det_orig['row_count'] if det_orig else 'NA'}。如果 rec-only 明显优于 det+rec，则默认检测器是主要瓶颈；本轮 rec-only 统计为：{rec_orig if rec_orig else '不可用'}。",
        f"- 固定文字高度：PaddleOCR h64 det+rec 统计为 {ocr_h64 if ocr_h64 else '无'}；需要重点看它是否把原始 row-only 的漏识别降下来。",
        f"- Qwen/VLM 画布形态影响：原始 row-only 平均编辑距离 {qwen_orig['平均编辑距离'] if qwen_orig else 'NA'}，h96 平均编辑距离 {qwen_h96['平均编辑距离'] if qwen_h96 else 'NA'}。若只小幅波动，说明输入画布不是主要瓶颈。",
        f"- 高 DPI 重渲染：{high_dpi_status.get('status')}，原因：{high_dpi_status.get('reason')}",
        "- 是否接近当前路线物理上限：如果 h48/h64/h96 与原始 row-only 相比仍不能稳定减少字符级错误，则当前通用 OCR/VLM 路线已接近上限，后续更适合做人工复核辅助或专门的局部字符复核实验，而不是继续扩写 prompt。",
    ]


def write_report(
    output_dir: Path,
    *,
    case_rows: list[dict[str, Any]],
    det_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    det_summary: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = summary["by_variant_method"]
    high_dpi_status = metadata.get("high_dpi_status", {})
    lines = [
        "# 病情观察及处理：OCR/VLM 字符识别瓶颈定位实验",
        "",
        "## 实验目的",
        "",
        "定位当前字符级错误主要来自 OCR 检测、OCR 识别、图像文字高度、PDF 渲染细节，还是 Qwen/VLM 本身的字符辨认能力。本轮不做纠错，不覆盖主结果，不跑 Qwen-R。",
        "",
        "## 输入 case 数量",
        "",
        f"- residual case 数量：{metadata['case_count']}",
        f"- 行级样本数量：{metadata['row_count']}",
        f"- 图像版本：{', '.join(IMAGE_VARIANT_LABELS[v] for v in IMAGE_VARIANTS)}",
        "",
        "## 图像版本示例",
        "",
        f"![contact sheet]({metadata.get('contact_sheet', '')})",
        "",
        "## 总体统计表",
        "",
        "| 图像版本 | 识别方式 | case数 | 完全一致 | 仅标点/空格差异 | 字符级错误 | 漏识别 | 过填 | 改写/概括 | 跳过 | 平均编辑距离 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['image_variant_label']} | {row['method_label']} | {row['case_count']} | "
            f"{row['完全一致']} | {row['仅标点/空格差异']} | {row['字符级错误']} | "
            f"{row['漏识别']} | {row['过填']} | {row['改写/概括']} | {row['skipped']} | {row['平均编辑距离']} |"
        )
    lines.extend([
        "",
        "## PaddleOCR 检测观测",
        "",
        "| 图像版本 | case数 | 行数 | det+rec检测框总数 | det+rec零检测行 | 平均每行框数 | det-only错误数 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in det_summary:
        lines.append(
            f"| {row['image_variant_label']} | {row['case_count']} | {row['row_count']} | "
            f"{row['detected_box_total']} | {row['zero_box_rows']} | {row['avg_boxes_per_row']} | {row['det_only_parse_error_count']} |"
        )
    lines.extend([
        "",
        "## High DPI 重渲染",
        "",
        f"- 状态：{high_dpi_status.get('status')}",
        f"- 原因：{high_dpi_status.get('reason')}",
        "",
        "## 按 Case 详细 Diff",
        "",
        "| case_id | gold | 图像版本 | 识别方式 | 原始识别文本 | 编辑距离 | 评估 | diff |",
        "|---|---|---|---|---|---:|---|---|",
    ])
    for row in case_rows:
        lines.append(
            f"| {row['case_id']} | {_md(row['gold'])} | {row['image_variant_label']} | "
            f"{row['method_label']} | {_md(row['recognized_text'])} | {row['edit_distance']} | "
            f"{'跳过' if row.get('skipped') else row['error_type']} | {_md(row.get('skip_reason') or row['brief_diff'])} |"
        )
    lines.extend([
        "",
        "## 关键判断",
        "",
        *derive_key_judgments(summary_rows, det_summary, high_dpi_status),
        "",
        "## 下一步建议",
        "",
        "- 若 PaddleOCR rec-only 明显好于 det+rec，可考虑后续单独研究检测器替换或固定行框 rec-only，但本轮不实现。",
        "- 若固定文字高度 h64/h96 对 Qwen 只小幅改善，不建议继续扩写 prompt。",
        "- 若高 DPI 坐标链路后续能稳定建立，可以只把它作为人工复核辅助图来源验证，不直接覆盖结果。",
    ])
    (output_dir / "observation_recognition_bottleneck_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_recognition_bottleneck_summary.json").write_text(
        json.dumps(
            {
                "metadata": metadata,
                "summary": summary,
                "det_summary": det_summary,
                "rows": case_rows,
                "det_rows": det_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def finalize_report(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    sidecars = [read_json(path) for path in _sidecar_paths(output_dir)]
    case_rows: list[dict[str, Any]] = []
    det_rows: list[dict[str, Any]] = []
    for sidecar in sidecars:
        case_rows.extend(_case_rows(sidecar))
        det_rows.extend(_det_rows(sidecar))
    summary = summarize_case_rows(case_rows)
    det_summary = summarize_det_rows(det_rows)
    pages = _load_pages(Path(args.pages_json)) if args.pages_json else []
    enhanced_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    row_count = sum(len(sidecar.get("rows", [])) for sidecar in sidecars)
    high_dpi_status = next((sidecar.get("high_dpi_status", {}) for sidecar in sidecars if sidecar.get("high_dpi_status")), {})
    contact_sheet = next((sidecar.get("contact_sheet", "") for sidecar in sidecars if sidecar.get("contact_sheet")), "")
    metadata = {
        "output_dir": str(output_dir),
        "source_run_dir": str(args.source_run_dir),
        "case_count": len(sidecars),
        "row_count": row_count,
        "contact_sheet": contact_sheet,
        "model_name": load_config(Path(args.config)).model_name if args.config else "qwen3vl-32b",
        "high_dpi_status": high_dpi_status,
        "main_result_hashes": _hash_main_results(pages),
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_dir, pages),
    }
    write_report(output_dir, case_rows=case_rows, det_rows=det_rows, summary=summary, det_summary=det_summary, metadata=metadata)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observation OCR/VLM character recognition bottleneck probe.")
    parser.add_argument("--stage", choices=["crop", "ocr", "qwen", "finalize"], required=True)
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--pages-json", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
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
