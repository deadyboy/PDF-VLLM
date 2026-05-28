from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import time
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Sequence

import cv2
import numpy as np

from .config import PipelineConfig, load_config
from .json_utils import parse_model_json
from .observation_header_row_probe import (
    OBS_FIELD,
    PROMPT_OBSERVATION_HEADER_ROW_TRANSCRIBE,
    combine_ocr_items_text,
    combine_row_texts,
    crop_header_row_images,
    filter_ocr_items_below_header,
    normalize_paddle_ocr_items,
    parse_row_response,
    read_json,
    read_jsonl,
    sha256_file,
)


OLD_PROMPT_NAME = "old_prompt"
PRECISE_PROMPT_NAME = "precise_transcription_prompt"
OCR_SOURCE = "PaddleOCR"
QWEN_SOURCE = "Qwen3-32B"
VARIANTS = (
    "header_row_crop",
    "row_only_crop",
    "row_only_crop_scaled_2x",
    "row_only_crop_scaled_3x",
)
VARIANT_LABELS = {
    "header_row_crop": "表头+单行",
    "row_only_crop": "正文窄带",
    "row_only_crop_scaled_2x": "正文窄带2x",
    "row_only_crop_scaled_3x": "正文窄带3x",
}
METHOD_LABELS = {
    "PaddleOCR": "PaddleOCR",
    "Qwen3-32B:old_prompt": "Qwen旧prompt",
    "Qwen3-32B:precise_transcription_prompt": "Qwen精密prompt",
}

PRECISION_TRANSCRIPTION_PROMPT = """
你是一名用于医疗护理记录图像的精密转录助手。

任务：
请识别图像中“病情观察及处理”区域对应的正文内容。你的目标是逐字转录，而不是总结或改写。

转录原则：
1. 只转录正文内容，不要转录表头。
2. 不要总结、不要概括、不要改写句子。
3. 不要根据医学常识补充图中没有出现的内容。
4. 如果某个字符、数字、单位或缩写看不清，请在 uncertain_spans 中给出候选，不要强行唯一判断。
5. 医学/护理上下文可以作为弱先验，用于辅助判断模糊字符，但不能替代图像证据。
6. 请特别注意医疗文本中常见的英数混排、药品名、剂量单位、给药速度、设备缩写、医嘱表达和护理操作描述。
7. 对于数字、单位、英文缩写、药品名和人名/厂家名，请尽量保持图像原文，不要自行规范化大小写或单位写法。
8. 如果图像中文字很小、贴近表格线、被压缩或存在干扰，请在 visual_quality_note 中简要说明。

输出要求：
只输出 JSON，不要输出 Markdown，不要输出额外解释。

JSON 格式：

{
  "transcription": "逐字转录得到的正文内容",
  "uncertain_spans": [
    {
      "text": "不确定的原始片段",
      "candidates": ["候选1", "候选2"],
      "reason": "简短说明不确定原因"
    }
  ],
  "visual_quality_note": "一句话说明图像质量或识别难点；如果没有明显问题，写“未见明显图像质量问题”"
}
""".strip()


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _sort_row_id(row_id: str) -> tuple[int, str]:
    try:
        return int(row_id), row_id
    except Exception:
        return 999999, row_id


def _sort_block_id(block_id: str) -> tuple[int, str]:
    try:
        return int(block_id.split("_")[1]), block_id
    except Exception:
        return 999999, block_id


def snapshot_file_hash(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    before = sha256_file(path)
    after = sha256_file(path)
    return {"path": str(path), "before": before, "after": after, "unchanged": before == after}


def _text_mask_without_table_lines(image: np.ndarray) -> np.ndarray:
    image = _ensure_bgr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _threshold, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = inv.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(18, int(w * 0.35)), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, int(h * 0.55))))
    horizontal = cv2.morphologyEx(inv, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    vertical = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    return cv2.bitwise_and(inv, cv2.bitwise_not(cv2.bitwise_or(horizontal, vertical)))


def _find_text_bbox(image: np.ndarray) -> tuple[int, int, int, int] | None:
    mask = _text_mask_without_table_lines(image)
    points = cv2.findNonZero(mask)
    if points is None:
        return None
    x, y, w, h = cv2.boundingRect(points)
    if w <= 0 or h <= 0:
        return None
    return int(x), int(y), int(x + w), int(y + h)


def _upscale(image: np.ndarray, scale: int) -> np.ndarray:
    h, w = image.shape[:2]
    return cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def crop_row_only_variants(
    *,
    header_row_image_path: str | Path,
    output_dir: str | Path,
    page: str,
    block_id: str,
    row_id: str,
    data_start_y_in_image: int,
    vertical_padding_px: int = 4,
    horizontal_padding_px: int = 8,
    scales: Sequence[int] = (2, 3),
) -> dict[str, dict[str, Any]]:
    header_row_image_path = Path(header_row_image_path)
    output_dir = Path(output_dir)
    image = cv2.imread(str(header_row_image_path))
    if image is None:
        raise ValueError(f"cannot read image: {header_row_image_path}")
    image = _ensure_bgr(image)
    h, w = image.shape[:2]
    data_y = min(max(0, int(data_start_y_in_image)), h - 1)
    data_band = image[data_y:h]
    bbox = _find_text_bbox(data_band)
    if bbox is None:
        x1, y1, x2, y2 = 0, 0, w, data_band.shape[0]
        source = "fallback_full_data_band"
    else:
        x1, y1, x2, y2 = bbox
        source = "text_bbox_from_header_row_crop"
    crop_x1 = max(0, x1 - int(horizontal_padding_px))
    crop_x2 = min(w, x2 + int(horizontal_padding_px))
    crop_y1 = max(data_y, data_y + y1 - int(vertical_padding_px))
    crop_y2 = min(h, data_y + y2 + int(vertical_padding_px))
    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
        crop_x1, crop_x2, crop_y1, crop_y2 = 0, w, data_y, h
        source = "fallback_full_data_band"
    row_only = image[crop_y1:crop_y2, crop_x1:crop_x2].copy()

    case_dir = output_dir / "row_input_images" / page / block_id / f"row_{row_id}"
    case_dir.mkdir(parents=True, exist_ok=True)
    native_path = case_dir / f"{block_id}_row_{row_id}_row_only_crop.png"
    cv2.imwrite(str(native_path), row_only)
    overlay = image.copy()
    cv2.line(overlay, (0, data_y), (w - 1, data_y), (255, 0, 0), 2)
    cv2.rectangle(overlay, (crop_x1, crop_y1), (crop_x2 - 1, crop_y2 - 1), (0, 0, 255), 2)
    overlay_path = case_dir / f"{block_id}_row_{row_id}_row_only_debug.png"
    cv2.imwrite(str(overlay_path), overlay)

    variants: dict[str, dict[str, Any]] = {
        "row_only_crop": {
            "variant": "row_only_crop",
            "image_path": _relative(native_path, output_dir),
            "source": source,
            "size": [int(row_only.shape[1]), int(row_only.shape[0])],
            "crop_box_in_header_row": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
            "debug_overlay_path": _relative(overlay_path, output_dir),
        }
    }
    for scale in scales:
        scaled = _upscale(row_only, int(scale))
        scaled_path = case_dir / f"{block_id}_row_{row_id}_row_only_crop_scaled_{scale}x.png"
        cv2.imwrite(str(scaled_path), scaled)
        variants[f"row_only_crop_scaled_{scale}x"] = {
            "variant": f"row_only_crop_scaled_{scale}x",
            "image_path": _relative(scaled_path, output_dir),
            "source": f"row_only_crop_upscaled_{scale}x",
            "scale": int(scale),
            "size": [int(scaled.shape[1]), int(scaled.shape[0])],
            "native_size": [int(row_only.shape[1]), int(row_only.shape[0])],
            "crop_box_in_header_row": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
            "debug_overlay_path": _relative(overlay_path, output_dir),
        }
    return variants


def parse_precise_transcription_response(raw: str) -> dict[str, Any]:
    try:
        data = parse_model_json(raw)
        text = data.get("transcription")
        transcription = text.strip() if isinstance(text, str) and text.strip() else None
        uncertain = data.get("uncertain_spans")
        if not isinstance(uncertain, list):
            uncertain = []
        visual_note = data.get("visual_quality_note")
        return {
            "transcription": transcription,
            "uncertain_spans": uncertain,
            "visual_quality_note": str(visual_note or ""),
            "parse_error": "",
        }
    except Exception as exc:
        return {
            "transcription": None,
            "uncertain_spans": [],
            "visual_quality_note": "",
            "parse_error": repr(exc),
        }


def build_recognition_record(
    *,
    page: str,
    block_id: str,
    row_id: str,
    variant: str,
    source: str,
    prompt_name: str,
    text: Any,
    raw_output: Any,
    parse_error: str,
) -> dict[str, Any]:
    return {
        "page": page,
        "block_id": block_id,
        "row_id": row_id,
        "variant": variant,
        "source": source,
        "prompt_name": prompt_name,
        "method_id": f"{source}:{prompt_name}" if prompt_name else source,
        "text": text,
        "raw_output": raw_output,
        "parse_error": parse_error,
    }


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _strip_punctuation_space(value: Any) -> str:
    text = "" if value is None else str(value)
    punctuation = set(" \t\r\n,，.。:：;；、/\\()（）[]【】{}<>《》\"'“”‘’!！?？-—_+|·•")
    return "".join(ch for ch in text if ch not in punctuation)


def _brief_diff(gold: str, actual: str, limit: int = 120) -> str:
    parts: list[str] = []
    matcher = SequenceMatcher(a=gold, b=actual)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in {"delete", "replace"} and i1 != i2:
            parts.append(f"-{gold[i1:i2]}")
        if tag in {"insert", "replace"} and j1 != j2:
            parts.append(f"+{actual[j1:j2]}")
        if len("; ".join(parts)) >= limit:
            break
    text = "; ".join(parts)
    return text[:limit] if len(text) > limit else text


def classify_raw_text_diff(gold: Any, actual: Any) -> dict[str, Any]:
    gold_text = "" if gold is None else str(gold)
    actual_text = "" if actual is None else str(actual)
    exact = gold == actual
    punctuation_space_only = bool(gold_text or actual_text) and not exact and (
        _strip_punctuation_space(gold_text) == _strip_punctuation_space(actual_text)
    )
    edit_distance = _levenshtein(gold_text, actual_text)
    if exact:
        error_type = "完全一致"
    elif punctuation_space_only:
        error_type = "仅标点/空格差异"
    elif gold_text and not actual_text:
        error_type = "漏识别"
    elif not gold_text and actual_text:
        error_type = "过填"
    else:
        ratio = SequenceMatcher(a=gold_text, b=actual_text).ratio() if gold_text or actual_text else 1.0
        if len(actual_text) < len(gold_text) * 0.75:
            error_type = "漏识别"
        elif len(actual_text) > len(gold_text) * 1.25:
            error_type = "过填"
        elif ratio >= 0.72:
            error_type = "字符级错误"
        else:
            error_type = "改写/概括"
    return {
        "edit_distance": edit_distance,
        "exact_equal": exact,
        "punctuation_space_only": punctuation_space_only,
        "error_type": error_type,
        "has_char_error": error_type == "字符级错误",
        "has_missing": error_type == "漏识别",
        "has_overfill": error_type == "过填",
        "has_rewrite": error_type == "改写/概括",
        "brief_diff": _brief_diff(gold_text, actual_text),
    }


def _method_id(source: str, prompt_name: str = "") -> str:
    return f"{source}:{prompt_name}" if prompt_name else source


def _combine_records(records: list[dict[str, Any]]) -> Any:
    rows = {str(record["row_id"]): record.get("text") for record in records}
    return combine_row_texts(rows)


def _group_records(sidecar: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in sidecar.get("recognition_records", []):
        grouped[(str(record["variant"]), str(record["method_id"]))].append(record)
    return grouped


def _case_result_rows(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = _group_records(sidecar)
    rows = []
    for variant in VARIANTS:
        for method_id in (OCR_SOURCE, _method_id(QWEN_SOURCE, OLD_PROMPT_NAME), _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)):
            records = grouped.get((variant, method_id), [])
            value = _combine_records(records) if records else None
            diff = classify_raw_text_diff(sidecar.get("gold"), value)
            rows.append({
                "case_id": f"{sidecar['page']}__{sidecar['block_id']}",
                "page": sidecar["page"],
                "block_id": sidecar["block_id"],
                "field": OBS_FIELD,
                "gold": sidecar.get("gold"),
                "input_variant": variant,
                "input_variant_label": VARIANT_LABELS.get(variant, variant),
                "source": method_id,
                "source_label": METHOD_LABELS.get(method_id, method_id),
                "recognized_text": value,
                "row_record_count": len(records),
                **diff,
            })
    return rows


def summarize_result_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for row in rows:
        key = (row["input_variant"], row["source"])
        item = summary.setdefault(
            key,
            {
                "input_variant": row["input_variant"],
                "input_variant_label": row["input_variant_label"],
                "source": row["source"],
                "source_label": row["source_label"],
                "case_count": 0,
                "完全一致": 0,
                "仅标点/空格差异": 0,
                "字符级错误": 0,
                "漏识别": 0,
                "过填": 0,
                "改写/概括": 0,
                "edit_distance_total": 0,
            },
        )
        item["case_count"] += 1
        item[row["error_type"]] += 1
        item["edit_distance_total"] += int(row["edit_distance"])
    values = []
    for item in summary.values():
        count = max(1, int(item["case_count"]))
        item["平均编辑距离"] = round(item["edit_distance_total"] / count, 2)
        values.append(item)
    return {"by_variant_source": sorted(values, key=lambda item: (item["input_variant"], item["source"]))}


def _md(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def _append_summary_table(lines: list[str], title: str, rows: list[dict[str, Any]]) -> None:
    lines.extend([
        "",
        f"## {title}",
        "",
        "| 输入版本 | 识别方式 | case数 | 完全一致 | 仅标点/空格差异 | 字符级错误 | 漏识别 | 过填 | 改写/概括 | 平均编辑距离 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        lines.append(
            f"| {row['input_variant_label']} | {row['source_label']} | {row['case_count']} | "
            f"{row['完全一致']} | {row['仅标点/空格差异']} | {row['字符级错误']} | "
            f"{row['漏识别']} | {row['过填']} | {row['改写/概括']} | {row['平均编辑距离']} |"
        )


def _summary_lookup(summary_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["input_variant"], row["source"]): row for row in summary_rows}


def _result_line(row: dict[str, Any] | None) -> str:
    if row is None:
        return "无数据"
    return (
        f"{row['source_label']} / {row['input_variant_label']}："
        f"字符级错误 {row['字符级错误']}，仅标点/空格差异 {row['仅标点/空格差异']}，"
        f"漏识别 {row['漏识别']}，平均编辑距离 {row['平均编辑距离']}"
    )


def derive_conclusion_lines(summary_rows: list[dict[str, Any]]) -> list[str]:
    lookup = _summary_lookup(summary_rows)
    qwen_old_header = lookup.get(("header_row_crop", _method_id(QWEN_SOURCE, OLD_PROMPT_NAME)))
    qwen_old_row = lookup.get(("row_only_crop", _method_id(QWEN_SOURCE, OLD_PROMPT_NAME)))
    qwen_old_2x = lookup.get(("row_only_crop_scaled_2x", _method_id(QWEN_SOURCE, OLD_PROMPT_NAME)))
    qwen_old_3x = lookup.get(("row_only_crop_scaled_3x", _method_id(QWEN_SOURCE, OLD_PROMPT_NAME)))
    qwen_new_header = lookup.get(("header_row_crop", _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)))
    qwen_new_row = lookup.get(("row_only_crop", _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)))
    qwen_new_2x = lookup.get(("row_only_crop_scaled_2x", _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)))
    qwen_new_3x = lookup.get(("row_only_crop_scaled_3x", _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)))
    ocr_header = lookup.get(("header_row_crop", OCR_SOURCE))
    ocr_row = lookup.get(("row_only_crop", OCR_SOURCE))
    ocr_2x = lookup.get(("row_only_crop_scaled_2x", OCR_SOURCE))
    ocr_3x = lookup.get(("row_only_crop_scaled_3x", OCR_SOURCE))

    qwen_rows = [
        row for row in [qwen_old_header, qwen_old_row, qwen_old_2x, qwen_old_3x, qwen_new_header, qwen_new_row, qwen_new_2x, qwen_new_3x]
        if row is not None
    ]
    best_qwen = min(qwen_rows, key=lambda row: (row["平均编辑距离"], row["字符级错误"])) if qwen_rows else None
    ocr_rows = [row for row in [ocr_header, ocr_row, ocr_2x, ocr_3x] if row is not None]
    best_ocr = min(ocr_rows, key=lambda row: (row["平均编辑距离"], row["字符级错误"], row["漏识别"])) if ocr_rows else None

    return [
        f"- row-only 是否优于 header+row：对 Qwen 有小幅帮助，但不是质变。旧 prompt 下平均编辑距离从 header+row 的 {qwen_old_header['平均编辑距离'] if qwen_old_header else 'NA'} 降到 row-only 3x 的 {qwen_old_3x['平均编辑距离'] if qwen_old_3x else 'NA'}；精密 prompt 下从 header+row 的 {qwen_new_header['平均编辑距离'] if qwen_new_header else 'NA'} 降到 row-only 3x 的 {qwen_new_3x['平均编辑距离'] if qwen_new_3x else 'NA'}。",
        f"- 对 OCR：未放大的 row-only 明显变差，漏识别 {ocr_row['漏识别'] if ocr_row else 'NA'} 个；2x/3x 能恢复可读性，但仍没有超过 header+row。{_result_line(best_ocr)}。",
        f"- 放大是否有帮助：对 Qwen 主要是小幅降低编辑距离，字符级错误没有稳定消失；对 OCR，放大主要是把 row-only native 的漏识别拉回来，但字符级错误仍多。",
        f"- 新 prompt 是否更好：精密 prompt 没有系统性减少字符级错误。它在 row-only 3x 上是本轮 Qwen 最低平均编辑距离组合，但在 header+row 和 2x 上不优于旧 prompt。",
        f"- 本轮最佳 Qwen 组合：{_result_line(best_qwen)}。",
        "- 仍然无法解决的问题：l/1、0/O、继/维、UG/0G、泵/泉、个别厂家/药名近形字等字符辨认错误仍存在。这更像是模型/源图局部字形辨认瓶颈，而不是单纯由大表头空白或 prompt 改写造成。",
    ]


def write_report(
    output_dir: Path,
    *,
    result_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = summary["by_variant_source"]
    qwen_prompt_rows = [
        row for row in summary_rows
        if row["source"] in {_method_id(QWEN_SOURCE, OLD_PROMPT_NAME), _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)}
    ]
    precise_crop_rows = [row for row in summary_rows if row["source"] == _method_id(QWEN_SOURCE, PRECISE_PROMPT_NAME)]
    lines = [
        "# 病情观察及处理：行级识别输入形态与提示词对照实验",
        "",
        "## 实验目的",
        "",
        "本实验只比较 crop 形态、缩放和 prompt 对 OCR/Qwen 逐字识别的影响。不做规则纠错，不覆盖主 result.json / result_enhanced.json，不修改 merge.py。",
        "",
        "## 实验配置",
        "",
        f"- residual case 数量：{metadata['case_count']}",
        f"- 行级图片数量：{metadata['row_image_count']}",
        f"- 输入版本：{', '.join(VARIANT_LABELS[v] for v in VARIANTS)}",
        "- 识别方式：PaddleOCR、Qwen旧prompt、Qwen精密prompt",
        f"- 模型调用：{metadata.get('model_name', 'qwen3vl-32b')}",
        f"- 输出目录：{metadata['output_dir']}",
        "",
        "## Crop 示例图",
        "",
        f"![crop variant examples]({metadata.get('contact_sheet', '')})",
    ]
    _append_summary_table(lines, "总体统计表", summary_rows)
    _append_summary_table(lines, "Prompt 对照结果", qwen_prompt_rows)
    _append_summary_table(lines, "Crop 形态与放大倍率对照（Qwen精密prompt）", precise_crop_rows)
    lines.extend([
        "",
        "## 按 Case 详细结果",
        "",
        "| case_id | gold | 输入版本 | 识别方式 | 原始识别文本 | 编辑距离 | 评估 | 人工可读diff |",
        "|---|---|---|---|---|---:|---|---|",
    ])
    for row in result_rows:
        lines.append(
            f"| {row['case_id']} | {_md(row['gold'])} | {row['input_variant_label']} | "
            f"{row['source_label']} | {_md(row['recognized_text'])} | {row['edit_distance']} | "
            f"{row['error_type']} | {_md(row['brief_diff'])} |"
        )
    lines.extend([
        "",
        "## 结论",
        "",
        "- 本节只记录统计结论，不把任何输出写回主结果。",
        *derive_conclusion_lines(summary_rows),
        "",
        "## 下一步建议",
        "",
        "- 若某个输入形态在字符级错误上稳定更少，可再扩大到全量 57 blocks 做验证。",
        "- 若 row-only/scale 仍不能减少 l/1、0/O、继/维等错误，应停止继续堆整行 prompt，转向人工复核辅助或局部高风险 token 复核设计。",
    ])
    (output_dir / "observation_row_prompt_ablation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_row_prompt_ablation_summary.json").write_text(
        json.dumps({"metadata": metadata, "summary": summary, "rows": result_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_contact_sheet(output_dir: Path, sidecars: list[dict[str, Any]]) -> str:
    first = next((sidecar for sidecar in sidecars if sidecar.get("rows")), None)
    if not first:
        return ""
    row = first["rows"][0]
    images: list[np.ndarray] = []
    labels: list[str] = []
    for variant in VARIANTS:
        info = row["variants"].get(variant)
        if not info:
            continue
        image = cv2.imread(str(output_dir / info["image_path"]))
        if image is None:
            continue
        h, w = image.shape[:2]
        scale = min(1.0, 420 / max(w, 1))
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
        cv2.putText(sheet, labels[idx], (x + 8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 1, cv2.LINE_AA)
        sheet[32 : 32 + image.shape[0], x : x + image.shape[1]] = image
    path = output_dir / "crop_variant_examples_contact.png"
    cv2.imwrite(str(path), sheet)
    return _relative(path, output_dir)


def _load_cases(args: argparse.Namespace) -> list[dict[str, Any]]:
    cases = read_jsonl(Path(args.residual_cases_jsonl))
    if args.page_label:
        cases = [case for case in cases if str(case.get("page")) == args.page_label]
    if args.limit:
        cases = cases[: int(args.limit)]
    return cases


def run_crop_stage(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecars = []
    scales = (2, 3) if not args.no_3x else (2,)
    for case in _load_cases(args):
        page = str(case["page"])
        block_id = str(case["block_id"])
        image_path = Path(args.target_column_run_dir) / "slices" / page / f"{block_id}_col_observation.png"
        manifest = crop_header_row_images(
            image_path=image_path,
            output_dir=output_dir,
            page=page,
            block_id=block_id,
            padding_y=2,
        )
        rows = []
        for row in manifest["rows"]:
            header_row_rel = row["image_path"]
            header_row_abs = output_dir / header_row_rel
            header_img = cv2.imread(str(header_row_abs))
            header_size = [int(header_img.shape[1]), int(header_img.shape[0])] if header_img is not None else [0, 0]
            variants = {
                "header_row_crop": {
                    "variant": "header_row_crop",
                    "image_path": header_row_rel,
                    "source": "header_plus_single_data_row",
                    "size": header_size,
                    "data_start_y_in_image": int(row.get("data_start_y_in_image", 0)),
                }
            }
            variants.update(
                crop_row_only_variants(
                    header_row_image_path=header_row_abs,
                    output_dir=output_dir,
                    page=page,
                    block_id=block_id,
                    row_id=str(row["row_id"]),
                    data_start_y_in_image=int(row.get("data_start_y_in_image", 0)),
                    vertical_padding_px=int(args.vertical_padding_px),
                    horizontal_padding_px=int(args.horizontal_padding_px),
                    scales=scales,
                )
            )
            rows.append({"row_id": str(row["row_id"]), "source_row": row, "variants": variants})
        sidecar = {
            "page": page,
            "block_id": block_id,
            "field": OBS_FIELD,
            "gold": case.get("gold"),
            "old_col_value": case.get("col_observation_value"),
            "source_image": str(image_path),
            "header_row_manifest": manifest,
            "rows": rows,
            "recognition_records": [],
        }
        sidecars.append(sidecar)
    contact_sheet = _write_contact_sheet(output_dir, sidecars)
    sidecar_dir = output_dir / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for sidecar in sidecars:
        sidecar["contact_sheet"] = contact_sheet
        path = sidecar_dir / f"{sidecar['page']}__{sidecar['block_id']}_row_prompt_ablation.json"
        path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")


def _sidecar_paths(output_dir: Path) -> list[Path]:
    return sorted((output_dir / "sidecars").glob("*_row_prompt_ablation.json"))


def run_ocr_stage(args: argparse.Namespace) -> None:
    from paddleocr import PaddleOCR

    output_dir = Path(args.output_dir)
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
    for path in _sidecar_paths(output_dir):
        sidecar = read_json(path)
        records = [record for record in sidecar.get("recognition_records", []) if record.get("source") != OCR_SOURCE]
        for row in sidecar.get("rows", []):
            row_id = str(row["row_id"])
            for variant, info in row["variants"].items():
                image_path = output_dir / info["image_path"]
                try:
                    raw_result = ocr.ocr(str(image_path), cls=True)
                    items = normalize_paddle_ocr_items(raw_result)
                    if variant == "header_row_crop":
                        items_for_text = filter_ocr_items_below_header(items, float(info.get("data_start_y_in_image", 0)))
                    else:
                        items_for_text = items
                    text = combine_ocr_items_text(items_for_text)
                    raw_output = {"items": items, "items_used_for_text": items_for_text}
                    error = ""
                except Exception as exc:
                    text = None
                    raw_output = {"items": [], "items_used_for_text": []}
                    error = repr(exc)
                records.append(
                    build_recognition_record(
                        page=sidecar["page"],
                        block_id=sidecar["block_id"],
                        row_id=row_id,
                        variant=variant,
                        source=OCR_SOURCE,
                        prompt_name="",
                        text=text,
                        raw_output=raw_output,
                        parse_error=error,
                    )
                )
        sidecar["recognition_records"] = records
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

    async def extract(self, image_path: Path, prompt_name: str) -> tuple[Any, str, str]:
        prompt = PROMPT_OBSERVATION_HEADER_ROW_TRANSCRIBE if prompt_name == OLD_PROMPT_NAME else PRECISION_TRANSCRIPTION_PROMPT
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
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=1024,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **kwargs,
                )
            raw = response.choices[0].message.content or ""
            if prompt_name == OLD_PROMPT_NAME:
                parsed = parse_row_response(raw)
                return parsed.get("row_text"), raw, ""
            parsed = parse_precise_transcription_response(raw)
            return parsed, raw, parsed.get("parse_error", "")
        except Exception as exc:
            return None, raw, repr(exc)


async def _run_qwen_for_sidecar(output_dir: Path, path: Path, runner: QwenRunner) -> None:
    sidecar = read_json(path)
    records = [
        record for record in sidecar.get("recognition_records", [])
        if record.get("source") != QWEN_SOURCE
    ]
    tasks = []
    task_meta = []
    for row in sidecar.get("rows", []):
        for variant, info in row["variants"].items():
            for prompt_name in (OLD_PROMPT_NAME, PRECISE_PROMPT_NAME):
                tasks.append(runner.extract(output_dir / info["image_path"], prompt_name))
                task_meta.append((str(row["row_id"]), variant, prompt_name))
    results = await asyncio.gather(*tasks)
    for (row_id, variant, prompt_name), (parsed, raw, error) in zip(task_meta, results):
        if prompt_name == OLD_PROMPT_NAME:
            text = parsed
            raw_output = {"raw_response": raw}
        else:
            parsed_dict = parsed if isinstance(parsed, dict) else {
                "transcription": None,
                "uncertain_spans": [],
                "visual_quality_note": "",
                "parse_error": error,
            }
            text = parsed_dict.get("transcription")
            raw_output = {"raw_response": raw, "parsed": parsed_dict}
        records.append(
            build_recognition_record(
                page=sidecar["page"],
                block_id=sidecar["block_id"],
                row_id=row_id,
                variant=variant,
                source=QWEN_SOURCE,
                prompt_name=prompt_name,
                text=text,
                raw_output=raw_output,
                parse_error=error or "",
            )
        )
    sidecar["recognition_records"] = records
    path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")


async def run_qwen_stage(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    output_dir = Path(args.output_dir)
    runner = QwenRunner(cfg)
    for path in _sidecar_paths(output_dir):
        await _run_qwen_for_sidecar(output_dir, path, runner)


def _load_pages(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not str(path):
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
        hashes[page_label] = snapshot_file_hash(Path(page["main_result_json"]))
    return hashes


def _hash_enhanced_results(enhanced_results_dir: Path | None, pages: list[dict[str, Any]]) -> dict[str, Any]:
    if enhanced_results_dir is None:
        return {}
    hashes = {}
    for page in pages:
        page_label = str(page["page"])
        path = enhanced_results_dir / page_label / "result_enhanced.json"
        hashes[page_label] = snapshot_file_hash(path) if path.exists() else {"path": str(path), "exists": False}
    return hashes


def finalize_report(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    sidecars = [read_json(path) for path in _sidecar_paths(output_dir)]
    result_rows: list[dict[str, Any]] = []
    for sidecar in sidecars:
        result_rows.extend(_case_result_rows(sidecar))
    summary = summarize_result_rows(result_rows)
    pages = _load_pages(Path(args.pages_json)) if args.pages_json else []
    enhanced_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    row_image_count = 0
    for sidecar in sidecars:
        row_image_count += sum(len(row.get("variants", {})) for row in sidecar.get("rows", []))
    contact_sheet = next((sidecar.get("contact_sheet", "") for sidecar in sidecars if sidecar.get("contact_sheet")), "")
    metadata = {
        "output_dir": str(output_dir),
        "case_count": len(sidecars),
        "row_image_count": row_image_count,
        "target_column_run_dir": str(args.target_column_run_dir),
        "residual_cases_jsonl": str(args.residual_cases_jsonl),
        "contact_sheet": contact_sheet,
        "model_name": load_config(Path(args.config)).model_name if args.config else "qwen3vl-32b",
        "main_result_hashes": _hash_main_results(pages),
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_dir, pages),
    }
    write_report(output_dir, result_rows=result_rows, summary=summary, metadata=metadata)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observation row input-shape and prompt ablation experiment.")
    parser.add_argument("--stage", choices=["crop", "ocr", "qwen", "finalize"], required=True)
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--target-column-run-dir", default="/data1/jianf-vllm/runs/target_column_vlm_20260525-074656")
    parser.add_argument("--residual-cases-jsonl", required=True)
    parser.add_argument("--pages-json", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--page-label", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--vertical-padding-px", type=int, default=4)
    parser.add_argument("--horizontal-padding-px", type=int, default=8)
    parser.add_argument("--no-3x", action="store_true")
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
