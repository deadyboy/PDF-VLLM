from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import cv2
import numpy as np


SOURCE_STAGE = "clean_final_block_before_redline_before_optimize"
TRUE_CLEAN_VARIANTS = (
    "obs_true_clean_native",
    "obs_true_clean_2x",
    "obs_true_clean_3x",
)


def _variant_filename(block_id: str, variant: str) -> str:
    suffix = variant.replace("obs_true_clean_", "obs_true_clean_")
    return f"{block_id}_{suffix}.png"


def _resize_variant(image: np.ndarray, scale: int) -> np.ndarray:
    if scale == 1:
        return image.copy()
    h, w = image.shape[:2]
    return cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def _size_hw(image: np.ndarray) -> list[int]:
    h, w = image.shape[:2]
    return [int(h), int(w)]


def _build_manifest(
    source_image: Path,
    page: str,
    block_id: str,
    clean_final_block: np.ndarray,
    crop_box: tuple[int, int, int, int],
    padding: int,
    native_crop: np.ndarray,
    variants: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    x1, x2, y1, y2 = crop_box
    native_size = _size_hw(native_crop)
    native_variant = variants["obs_true_clean_native"]
    return {
        "source_image": str(source_image),
        "page": page,
        "block_id": block_id,
        "source_stage": SOURCE_STAGE,
        "final_block_shape": _size_hw(clean_final_block),
        "crop_x1": int(x1),
        "crop_x2": int(x2),
        "crop_y1": int(y1),
        "crop_y2": int(y2),
        "padding": int(padding),
        "native_size": native_size,
        "variant_size_before_llm_optimize": native_variant["variant_size_before_llm_optimize"],
        "variant_size_after_llm_optimize": native_variant["variant_size_after_llm_optimize"],
        "used_optimize_image_for_llm": native_variant["used_optimize_image_for_llm"],
        "was_downscaled_before_model": native_variant["was_downscaled_before_model"],
        "variants": variants,
    }


def write_true_clean_observation_crops(
    img_path: Path,
    output_dir: Path,
    page: str = "",
    padding: int = 12,
) -> dict[str, Any]:
    from paddleocr import PaddleOCR

    from .cutter_worker_jin import (
        choose_header_bottom_y,
        choose_jin_target_column_ranges,
        get_global_splits_by_counting,
    )
    from .iv_clean2x_crop_worker import (
        _detect_horizontal_boundaries,
        _scan_block_starts,
        _trim_last_block_if_blank,
    )

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
    ranges = choose_jin_target_column_ranges(col_xs, w, padding=padding)
    obs_spec = ranges["observation"]

    block_starts, summary_row_indices = _scan_block_starts(img, merged_y, start_data_idx, ocr)
    if not block_starts:
        raise RuntimeError(f"no regular blocks detected: {img_path}")

    blocks = []
    for idx in range(len(block_starts)):
        start_node_idx = block_starts[idx][0]
        y_start = merged_y[start_node_idx]
        y_end = merged_y[block_starts[idx + 1][0]] if idx < len(block_starts) - 1 else merged_y[-1]
        for s_idx in sorted(summary_row_indices):
            if start_node_idx < s_idx and merged_y[s_idx] < y_end:
                y_end = merged_y[s_idx]
                break
        y_end = _trim_last_block_if_blank(img, merged_y, block_starts, idx, start_node_idx, y_start, y_end, ocr)

        clean_final_block = np.vstack((header, img[y_start:y_end, :]))
        block_id = f"block_{idx:02d}"
        x1 = max(0, min(obs_spec.x1, clean_final_block.shape[1] - 1))
        x2 = max(x1 + 1, min(obs_spec.x2, clean_final_block.shape[1]))
        y1, y2 = 0, clean_final_block.shape[0]
        native_crop = clean_final_block[y1:y2, x1:x2]

        variants: dict[str, dict[str, Any]] = {}
        for variant, scale in (
            ("obs_true_clean_native", 1),
            ("obs_true_clean_2x", 2),
            ("obs_true_clean_3x", 3),
        ):
            variant_img = _resize_variant(native_crop, scale)
            filename = _variant_filename(block_id, variant)
            cv2.imwrite(str(output_dir / filename), variant_img)
            size = _size_hw(variant_img)
            variants[variant] = {
                "path": filename,
                "scale": scale,
                "variant_size_before_llm_optimize": size,
                "variant_size_after_llm_optimize": size,
                "used_optimize_image_for_llm": False,
                "was_downscaled_before_model": False,
            }

        overlay = clean_final_block.copy()
        cv2.rectangle(overlay, (x1, y1), (x2 - 1, y2 - 1), (0, 128, 0), 4)
        cv2.putText(
            overlay,
            "observation_true_clean",
            (x1 + 4, min(44, overlay.shape[0] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 128, 0),
            2,
            cv2.LINE_AA,
        )
        overlay_name = f"{block_id}_obs_true_clean_overlay.png"
        cv2.imwrite(str(output_dir / overlay_name), overlay)

        manifest = _build_manifest(
            source_image=img_path,
            page=page,
            block_id=block_id,
            clean_final_block=clean_final_block,
            crop_box=(x1, x2, y1, y2),
            padding=padding,
            native_crop=native_crop,
            variants=variants,
        )
        manifest["overlay"] = overlay_name
        manifest["source_y_start"] = int(y_start)
        manifest["source_y_end"] = int(y_end)
        manifest["header_bottom_y"] = int(header_bottom_y)
        manifest_path = output_dir / f"{block_id}_obs_true_clean_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        blocks.append(manifest)

    top_manifest = {
        "source_image": str(img_path),
        "page": page,
        "source_stage": SOURCE_STAGE,
        "padding": int(padding),
        "block_count": len(blocks),
        "blocks": blocks,
    }
    (output_dir / "observation_true_clean_crop_manifest.json").write_text(
        json.dumps(top_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return top_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write true-clean observation column crops for Jin profile.")
    parser.add_argument("--img", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--page", default="")
    parser.add_argument("--padding", type=int, default=12)
    args = parser.parse_args()
    write_true_clean_observation_crops(Path(args.img), Path(args.out), page=args.page, padding=args.padding)


if __name__ == "__main__":
    main()
