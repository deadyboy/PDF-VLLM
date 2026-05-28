from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
from paddleocr import PaddleOCR

from .cutter_worker_jin import (
    choose_header_bottom_y,
    choose_jin_target_column_ranges,
    get_global_splits_by_counting,
    get_time_from_zone,
    is_summary_row,
)


def _upscale_2x_with_border(img):
    h, w = img.shape[:2]
    upscaled = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(upscaled, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255, 255, 255])


def _detect_horizontal_boundaries(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 15)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 10, 1))
    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=2)
    contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_y = sorted([
        cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3] // 2
        for c in contours
        if cv2.boundingRect(c)[2] > w * 0.5
    ])
    merged_y = []
    for y in all_y:
        if not merged_y or y - merged_y[-1] > 15:
            merged_y.append(y)
    return merged_y


def _scan_block_starts(img, merged_y, start_data_idx, ocr):
    h, w = img.shape[:2]
    time_col_width = int(w * 0.15)
    time_anchors = []
    summary_row_indices = []
    for i in range(start_data_idx, len(merged_y) - 1):
        y_top, y_btm = merged_y[i], merged_y[i + 1]
        summary_zone = img[y_top:y_btm, :min(int(w * 0.25), w)]
        if is_summary_row(summary_zone, ocr):
            summary_row_indices.append(i)
            continue
        time_zone = img[y_top:y_btm, :time_col_width]
        if get_time_from_zone(time_zone, ocr):
            time_anchors.append(i)

    block_starts = []
    summary_set = set(summary_row_indices)
    if not time_anchors:
        for i in range(start_data_idx, len(merged_y) - 1):
            if i not in summary_set:
                block_starts.append((i, ""))
                break
    else:
        if time_anchors[0] > start_data_idx:
            for i in range(start_data_idx, time_anchors[0]):
                if i not in summary_set:
                    block_starts.append((i, ""))
                    break
        for idx in time_anchors:
            block_starts.append((idx, ""))
    return block_starts, summary_row_indices


def _trim_last_block_if_blank(img, merged_y, block_starts, idx, start_node_idx, y_start, y_end, ocr):
    if idx != len(block_starts) - 1:
        return y_end
    huge_roi = img[y_start:y_end, :]
    res = ocr.ocr(huge_roi, cls=False)
    max_text_y = 0
    if res and res[0]:
        for line in res[0]:
            box = line[0]
            bottom_y = max(box[2][1], box[3][1])
            max_text_y = max(max_text_y, bottom_y)
    if max_text_y > 0:
        abs_true_bottom = y_start + max_text_y + 15
        for y in merged_y[start_node_idx + 1:]:
            if y >= abs_true_bottom:
                return y
        return y_end
    fallback_idx = min(start_node_idx + 2, len(merged_y) - 1)
    return merged_y[fallback_idx]


def write_clean2x_iv_crops(img_path: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(img_path))
    if img is None:
        raise RuntimeError(f"OpenCV cannot read image: {img_path}")
    h, w = img.shape[:2]
    ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False, use_gpu=False)

    merged_y = _detect_horizontal_boundaries(img)
    if not merged_y:
        raise RuntimeError(f"no horizontal lines detected: {img_path}")
    header_bottom_y, start_data_idx = choose_header_bottom_y(merged_y, h, 450)
    header = img[0:header_bottom_y, :]
    (_global_splits, col_xs) = get_global_splits_by_counting(header)
    ranges = choose_jin_target_column_ranges(col_xs, w, padding=24)
    iv_spec = ranges["iv_drug"]

    block_starts, summary_row_indices = _scan_block_starts(img, merged_y, start_data_idx, ocr)
    if not block_starts:
        raise RuntimeError(f"no regular blocks detected: {img_path}")

    saved = []
    for idx in range(len(block_starts)):
        start_node_idx = block_starts[idx][0]
        y_start = merged_y[start_node_idx]
        y_end = merged_y[block_starts[idx + 1][0]] if idx < len(block_starts) - 1 else merged_y[-1]
        for s_idx in sorted(summary_row_indices):
            if start_node_idx < s_idx and merged_y[s_idx] < y_end:
                y_end = merged_y[s_idx]
                break
        y_end = _trim_last_block_if_blank(img, merged_y, block_starts, idx, start_node_idx, y_start, y_end, ocr)

        clean_block = np.vstack((header, img[y_start:y_end, :]))
        x1 = max(0, min(iv_spec.x1, clean_block.shape[1] - 1))
        x2 = max(x1 + 1, min(iv_spec.x2, clean_block.shape[1]))
        crop = clean_block[:, x1:x2]
        block_id = f"block_{idx:02d}"
        crop_name = f"{block_id}_col_iv_drug_clean_2x.png"
        cv2.imwrite(str(output_dir / crop_name), _upscale_2x_with_border(crop))

        overlay = clean_block.copy()
        cv2.rectangle(overlay, (x1, 0), (x2 - 1, clean_block.shape[0] - 1), (255, 0, 0), 4)
        cv2.putText(overlay, "iv_drug_clean_2x", (x1 + 4, min(44, clean_block.shape[0] - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.imwrite(str(output_dir / f"{block_id}_col_iv_drug_clean_2x_overlay.png"), _upscale_2x_with_border(overlay))
        saved.append({
            "block_id": block_id,
            "image": crop_name,
            "overlay": f"{block_id}_col_iv_drug_clean_2x_overlay.png",
            "x1": int(x1),
            "x2": int(x2),
            "y_start": int(y_start),
            "y_end": int(y_end),
            "header_bottom_y": int(header_bottom_y),
        })

    manifest = {
        "image": str(img_path),
        "variant": "clean_2x",
        "source": "original image clean block without red lines",
        "scale": 2,
        "padding": 24,
        "blocks": saved,
    }
    (output_dir / "clean_2x_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write clean 2x IV-drug single-column crops for Jin profile.")
    parser.add_argument("--img", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    write_clean2x_iv_crops(Path(args.img), Path(args.out))


if __name__ == "__main__":
    main()
