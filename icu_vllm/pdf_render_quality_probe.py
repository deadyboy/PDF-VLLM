from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Sequence

import fitz
from PIL import Image, ImageDraw, ImageFont


DEFAULT_DPI_LIST = [300, 450, 600, 900, 1200]
HIGH_DPI_CLIP_ONLY_THRESHOLD = 900


def dpi_to_zoom(dpi: int | float) -> float:
    return float(dpi) / 72.0


def estimate_rgb_mb(width: int, height: int) -> float:
    return round(width * height * 3 / (1024 * 1024), 3)


def parse_rect_points(value: str) -> list[float]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError(f"rect must contain 4 comma-separated numbers: {value}")
    rect = [float(part) for part in parts]
    if rect[2] <= rect[0] or rect[3] <= rect[1]:
        raise ValueError(f"rect must satisfy x1>x0 and y1>y0: {value}")
    return rect


def parse_dpi_list(value: str) -> list[int]:
    dpis = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not dpis:
        raise ValueError("dpi list cannot be empty")
    if any(dpi <= 0 for dpi in dpis):
        raise ValueError(f"dpi values must be positive: {value}")
    return dpis


def parse_region_arg(value: str, default_name: str = "obs_clip") -> tuple[str, list[float]]:
    if "=" in value:
        name, rect_value = value.split("=", 1)
    elif ":" in value:
        name, rect_value = value.split(":", 1)
    else:
        name, rect_value = default_name, value
    name = name.strip() or default_name
    return name, parse_rect_points(rect_value)


def _json_safe_rect(rect: fitz.Rect) -> list[float]:
    return [round(float(rect.x0), 3), round(float(rect.y0), 3), round(float(rect.x1), 3), round(float(rect.y1), 3)]


def _image_xobject_to_dict(image_info: tuple) -> dict:
    return {
        "xref": image_info[0] if len(image_info) > 0 else None,
        "width": image_info[2] if len(image_info) > 2 else None,
        "height": image_info[3] if len(image_info) > 3 else None,
        "bpc": image_info[4] if len(image_info) > 4 else None,
        "colorspace": image_info[5] if len(image_info) > 5 else None,
        "name": image_info[7] if len(image_info) > 7 else None,
        "filter": image_info[8] if len(image_info) > 8 else None,
    }


def audit_pdf_page(pdf_path: str | Path, page_index: int, *, tiled_image_threshold: int = 8) -> dict:
    pdf_path = Path(pdf_path)
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        text = page.get_text("text") or ""
        images = [_image_xobject_to_dict(item) for item in page.get_images(full=True)]
        return {
            "pdf_path": str(pdf_path),
            "page_index": page_index,
            "page_rect_points": _json_safe_rect(page.rect),
            "text_length": len(text.strip()),
            "has_text_layer": bool(text.strip()),
            "text_preview": text.strip()[:500],
            "image_count": len(images),
            "possible_tiled_pdf": len(images) >= tiled_image_threshold,
            "tiled_image_threshold": tiled_image_threshold,
            "images": images,
        }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _manifest_path_for_png(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}.manifest.json")


def render_pdf_region(
    *,
    pdf_path: str | Path,
    page_index: int,
    clip_rect_points: Sequence[float] | None,
    dpi: int,
    output_path: str | Path,
    high_dpi_clip_only_threshold: int = HIGH_DPI_CLIP_ONLY_THRESHOLD,
) -> dict:
    if dpi >= high_dpi_clip_only_threshold and clip_rect_points is None:
        raise ValueError("900/1200 DPI renders must use a clip rect; full-page high-DPI export is forbidden")

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    zoom = dpi_to_zoom(dpi)
    clip = fitz.Rect(*clip_rect_points) if clip_rect_points is not None else None
    started = time.perf_counter()
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
        pix.save(output_path)
    elapsed = time.perf_counter() - started

    manifest = {
        "pdf_path": str(pdf_path),
        "page_index": page_index,
        "dpi": int(dpi),
        "zoom": round(zoom, 6),
        "clip_rect_points": [float(v) for v in clip_rect_points] if clip_rect_points is not None else None,
        "output_size": [int(pix.width), int(pix.height)],
        "estimated_rgb_mb": estimate_rgb_mb(pix.width, pix.height),
        "render_time_sec": round(elapsed, 4),
        "used_clip": clip_rect_points is not None,
        "full_page_render_forbidden": dpi >= high_dpi_clip_only_threshold,
    }
    _write_json(_manifest_path_for_png(output_path), manifest)
    return manifest


def _fit_image_to_width(image: Image.Image, width: int) -> Image.Image:
    if image.width == width:
        return image.copy()
    height = max(1, round(image.height * width / image.width))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def write_comparison_contact_sheet(
    *,
    image_paths: Sequence[str | Path],
    labels: Sequence[str],
    output_path: str | Path,
    cell_width: int = 420,
    label_height: int = 28,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Path:
    if len(image_paths) != len(labels):
        raise ValueError("image_paths and labels must have the same length")
    if not image_paths:
        raise ValueError("at least one image is required")

    resized: list[Image.Image] = []
    for path in image_paths:
        with Image.open(path) as image:
            resized.append(_fit_image_to_width(image.convert("RGB"), cell_width))
    cell_height = max(image.height for image in resized) + label_height
    sheet = Image.new("RGB", (cell_width * len(resized), cell_height), background)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, (image, label) in enumerate(zip(resized, labels)):
        x = idx * cell_width
        draw.text((x + 8, 6), label, fill=(0, 0, 0), font=font)
        sheet.paste(image, (x, label_height))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path


def write_seam_debug(image_path: str | Path, output_path: str | Path) -> Path:
    import cv2
    import numpy as np

    image_path = Path(image_path)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read image: {image_path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dark = gray < 80
    row_hits = np.where(dark.mean(axis=1) > 0.65)[0]
    col_hits = np.where(dark.mean(axis=0) > 0.65)[0]
    debug = image.copy()
    for y in row_hits:
        cv2.line(debug, (0, int(y)), (debug.shape[1] - 1, int(y)), (0, 0, 255), 1)
    for x in col_hits:
        cv2.line(debug, (int(x), 0), (int(x), debug.shape[0] - 1), (255, 0, 0), 1)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), debug)
    return output_path


def render_dpi_series(
    *,
    pdf_path: str | Path,
    page_index: int,
    region_name: str,
    clip_rect_points: Sequence[float],
    dpi_list: Sequence[int],
    output_dir: str | Path,
    seam_debug: bool = False,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests = []
    image_paths = []
    labels = []
    for dpi in dpi_list:
        output_path = output_dir / f"page{page_index}_{region_name}_{dpi}dpi.png"
        manifest = render_pdf_region(
            pdf_path=pdf_path,
            page_index=page_index,
            clip_rect_points=clip_rect_points,
            dpi=int(dpi),
            output_path=output_path,
        )
        manifests.append(manifest)
        image_paths.append(output_path)
        labels.append(f"{dpi} DPI")
        if seam_debug:
            write_seam_debug(output_path, output_dir / f"page{page_index}_{region_name}_{dpi}dpi.seam_debug.png")
    contact_sheet = write_comparison_contact_sheet(
        image_paths=image_paths,
        labels=labels,
        output_path=output_dir / "comparison_contact_sheet.png",
    )
    summary = {
        "pdf_path": str(Path(pdf_path)),
        "page_index": page_index,
        "region_name": region_name,
        "clip_rect_points": [float(v) for v in clip_rect_points],
        "dpi_list": [int(v) for v in dpi_list],
        "outputs": manifests,
        "contact_sheet": str(contact_sheet),
    }
    _write_json(output_dir / "render_quality_manifest.json", summary)
    return summary


def run_probe(
    *,
    pdf_path: str | Path,
    page_index: int,
    regions: Sequence[tuple[str, Sequence[float]]],
    output_dir: str | Path,
    dpi_list: Sequence[int] = DEFAULT_DPI_LIST,
    seam_debug: bool = False,
    audit_only: bool = False,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = audit_pdf_page(pdf_path, page_index)
    _write_json(output_dir / f"page{page_index}_audit.json", audit)
    region_summaries = []
    if not audit_only:
        for region_name, rect in regions:
            region_dir = output_dir / region_name
            region_summaries.append(
                render_dpi_series(
                    pdf_path=pdf_path,
                    page_index=page_index,
                    region_name=region_name,
                    clip_rect_points=rect,
                    dpi_list=dpi_list,
                    output_dir=region_dir,
                    seam_debug=seam_debug,
                )
            )
    summary = {"audit": audit, "regions": region_summaries}
    _write_json(output_dir / "pdf_render_quality_probe_summary.json", summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose PDF image tiling and local render quality at multiple DPI values.")
    parser.add_argument("--pdf-path", required=True)
    parser.add_argument("--page-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--rect", action="append", default=[], help="Clip rect as x0,y0,x1,y1 or name=x0,y0,x1,y1. May repeat.")
    parser.add_argument("--region-name", default="obs_clip", help="Name used when --rect omits an explicit name.")
    parser.add_argument("--dpi-list", default=",".join(str(v) for v in DEFAULT_DPI_LIST))
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--seam-debug", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    regions = [parse_region_arg(value, default_name=args.region_name) for value in args.rect]
    if not args.audit_only and not regions:
        parser.error("--rect is required unless --audit-only is set")
    run_probe(
        pdf_path=args.pdf_path,
        page_index=args.page_index,
        regions=regions,
        output_dir=args.output_dir,
        dpi_list=parse_dpi_list(args.dpi_list),
        seam_debug=args.seam_debug,
        audit_only=args.audit_only,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
