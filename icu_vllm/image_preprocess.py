from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


VARIANT_FILENAMES = {
    "raw_col": "{block_id}_obs_raw_col.png",
    "clean_2x": "{block_id}_obs_clean_2x.png",
    "clean_3x": "{block_id}_obs_clean_3x.png",
    "line_removed_2x": "{block_id}_obs_line_removed_2x.png",
    "clahe_2x": "{block_id}_obs_clahe_2x.png",
    "binary_2x": "{block_id}_obs_binary_2x.png",
}


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def upscale_with_border(image: np.ndarray, scale: int = 2, border: int = 40) -> np.ndarray:
    image = _ensure_bgr(image)
    h, w = image.shape[:2]
    resized = cv2.resize(image, (w * int(scale), h * int(scale)), interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(resized, border, border, border, border, cv2.BORDER_CONSTANT, value=[255, 255, 255])


def line_removed(image: np.ndarray) -> np.ndarray:
    image = _ensure_bgr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 12)
    h, w = gray.shape[:2]
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 4), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 4)))
    horizontal = cv2.morphologyEx(inv, cv2.MORPH_OPEN, h_kernel, iterations=1)
    vertical = cv2.morphologyEx(inv, cv2.MORPH_OPEN, v_kernel, iterations=1)
    mask = cv2.bitwise_or(horizontal, vertical)
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)
    result = image.copy()
    result[mask > 0] = (255, 255, 255)
    return result


def clahe_enhance(image: np.ndarray) -> np.ndarray:
    image = _ensure_bgr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def adaptive_binary(image: np.ndarray) -> np.ndarray:
    image = _ensure_bgr(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def _fit_width(image: np.ndarray, width: int) -> np.ndarray:
    h, w = image.shape[:2]
    if w == width:
        return image
    scale = width / max(w, 1)
    return cv2.resize(image, (width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)


def make_variant_overlay(variant_images: dict[str, np.ndarray]) -> np.ndarray:
    labels = list(VARIANT_FILENAMES)
    width = max(variant_images[label].shape[1] for label in labels if label in variant_images)
    panels = []
    for label in labels:
        if label not in variant_images:
            continue
        panel = _fit_width(_ensure_bgr(variant_images[label]), width)
        label_bar = np.full((36, width, 3), 255, dtype=np.uint8)
        cv2.putText(label_bar, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 180), 2, cv2.LINE_AA)
        panels.append(np.vstack((label_bar, panel)))
    return np.vstack(panels) if panels else np.full((40, 160, 3), 255, dtype=np.uint8)


def build_observation_variant_images(raw_col_image: np.ndarray) -> dict[str, np.ndarray]:
    raw = _ensure_bgr(raw_col_image)
    return {
        "raw_col": raw.copy(),
        "clean_2x": upscale_with_border(raw, scale=2),
        "clean_3x": upscale_with_border(raw, scale=3),
        "line_removed_2x": upscale_with_border(line_removed(raw), scale=2),
        "clahe_2x": upscale_with_border(clahe_enhance(raw), scale=2),
        "binary_2x": upscale_with_border(adaptive_binary(raw), scale=2),
    }


def write_observation_preprocess_variants(raw_col_path: Path, output_dir: Path, block_id: str) -> dict[str, Any]:
    image = cv2.imread(str(raw_col_path))
    if image is None:
        raise RuntimeError(f"OpenCV cannot read image: {raw_col_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    variant_images = build_observation_variant_images(image)
    manifest_blocks = {}
    for variant, variant_image in variant_images.items():
        filename = VARIANT_FILENAMES[variant].format(block_id=block_id)
        cv2.imwrite(str(output_dir / filename), variant_image)
        manifest_blocks[variant] = filename
    overlay_name = f"{block_id}_obs_preprocess_overlay.png"
    cv2.imwrite(str(output_dir / overlay_name), make_variant_overlay(variant_images))
    manifest = {
        "block_id": block_id,
        "source": str(raw_col_path),
        "variants": manifest_blocks,
        "overlay": overlay_name,
    }
    (output_dir / f"{block_id}_obs_preprocess_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
