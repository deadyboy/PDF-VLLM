from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any, Sequence

from openai import AsyncOpenAI
from PIL import Image

from .config import PipelineConfig, load_config
from .json_utils import normalize_nulls, parse_model_json
from .observation_eval import classify_observation_diff
from .pdf_render_quality_probe import audit_pdf_page, dpi_to_zoom, estimate_rgb_mb, parse_rect_points, render_pdf_region
from .prompts import PROMPT_COL_OBSERVATION
from .target_column_observation_compare import OBS_FIELD
from .target_column_vlm import read_json, sha256_file


DPI_VARIANTS = (
    "pdf_clip_300dpi",
    "pdf_clip_600dpi",
    "pdf_clip_900dpi",
    "pdf_clip_1200dpi",
    "pdf_clip_900dpi_down_to_300dpi",
    "pdf_clip_1200dpi_down_to_300dpi",
)

VARIANT_SPECS = {
    "pdf_clip_300dpi": {"dpi": 300, "down_to_dpi": None},
    "pdf_clip_600dpi": {"dpi": 600, "down_to_dpi": None},
    "pdf_clip_900dpi": {"dpi": 900, "down_to_dpi": None},
    "pdf_clip_1200dpi": {"dpi": 1200, "down_to_dpi": None},
    "pdf_clip_900dpi_down_to_300dpi": {"dpi": 900, "down_to_dpi": 300},
    "pdf_clip_1200dpi_down_to_300dpi": {"dpi": 1200, "down_to_dpi": 300},
}

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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _case_key(page: str, block_id: str) -> str:
    return f"{page}/{block_id}"


def _coerce_rect(value: Any) -> list[float]:
    if isinstance(value, str):
        return parse_rect_points(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = [float(item) for item in value]
        if len(values) == 4 and values[2] > values[0] and values[3] > values[1]:
            return values
    raise ValueError(f"invalid rect: {value!r}")


def load_case_rects(path: Path | None) -> dict[str, list[float]]:
    if path is None:
        return {}
    data = read_json(path)
    rects: dict[str, list[float]] = {}
    if isinstance(data, dict):
        if "default" in data:
            rects["default"] = _coerce_rect(data["default"])
        cases = data.get("cases", data)
        if isinstance(cases, dict):
            for key, value in cases.items():
                if key == "default":
                    continue
                rects[str(key)] = _coerce_rect(value)
    return rects


def select_cases(
    cases: list[dict[str, Any]],
    *,
    page_label: str | None,
    case_rects: dict[str, list[float]],
    default_rect: Sequence[float] | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    fallback = [float(v) for v in default_rect] if default_rect is not None else case_rects.get("default")
    for case in cases:
        page = str(case.get("page", ""))
        block_id = str(case.get("block_id", ""))
        if page_label and page != page_label:
            continue
        key = _case_key(page, block_id)
        rect = case_rects.get(key) or fallback
        if rect is None:
            continue
        item = dict(case)
        item["clip_rect_points"] = [float(v) for v in rect]
        selected.append(item)
    return selected


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _downsample_to_size(source_path: Path, output_path: Path, size: Sequence[int]) -> tuple[int, int]:
    with Image.open(source_path) as image:
        resized = image.convert("RGB").resize((int(size[0]), int(size[1])), Image.Resampling.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resized.save(output_path)
        return resized.size


def _variant_filename(block_id: str, variant: str) -> str:
    return f"{block_id}_{variant}.png"


def render_case_variants(
    *,
    pdf_path: str | Path,
    page_index: int,
    case: dict[str, Any],
    output_dir: str | Path,
    source_pdf_audit: dict[str, Any],
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    page = str(case["page"])
    block_id = str(case["block_id"])
    rect = [float(v) for v in case["clip_rect_points"]]
    case_dir = output_dir / "clips" / page / block_id
    case_dir.mkdir(parents=True, exist_ok=True)

    rendered_by_dpi: dict[int, tuple[Path, dict[str, Any]]] = {}
    variants: dict[str, Any] = {}
    for variant in DPI_VARIANTS:
        spec = VARIANT_SPECS[variant]
        dpi = int(spec["dpi"])
        source_path = case_dir / f"{block_id}_source_{dpi}dpi.png"
        if dpi not in rendered_by_dpi:
            render_manifest = render_pdf_region(
                pdf_path=pdf_path,
                page_index=page_index,
                clip_rect_points=rect,
                dpi=dpi,
                output_path=source_path,
            )
            rendered_by_dpi[dpi] = (source_path, render_manifest)
        else:
            source_path, render_manifest = rendered_by_dpi[dpi]

        output_path = case_dir / _variant_filename(block_id, variant)
        down_to_dpi = spec["down_to_dpi"]
        before_size = list(render_manifest["output_size"])
        if down_to_dpi is not None:
            target_source = rendered_by_dpi.get(int(down_to_dpi))
            if target_source is None:
                target_path = case_dir / f"{block_id}_source_{down_to_dpi}dpi.png"
                target_manifest = render_pdf_region(
                    pdf_path=pdf_path,
                    page_index=page_index,
                    clip_rect_points=rect,
                    dpi=int(down_to_dpi),
                    output_path=target_path,
                )
                target_source = (target_path, target_manifest)
                rendered_by_dpi[int(down_to_dpi)] = target_source
            after_size_tuple = _downsample_to_size(source_path, output_path, target_source[1]["output_size"])
            after_size = [int(after_size_tuple[0]), int(after_size_tuple[1])]
        else:
            if source_path != output_path:
                output_path.write_bytes(source_path.read_bytes())
            after_size = before_size

        manifest = {
            "pdf_path": str(Path(pdf_path)),
            "page_index": page_index,
            "page": page,
            "block_id": block_id,
            "variant": variant,
            "dpi": dpi,
            "zoom": round(dpi_to_zoom(dpi), 6),
            "clip_rect_points": rect,
            "output_size_before_downsample": before_size,
            "output_size_after_downsample": after_size,
            "estimated_rgb_mb": estimate_rgb_mb(before_size[0], before_size[1]),
            "estimated_rgb_mb_after_downsample": estimate_rgb_mb(after_size[0], after_size[1]),
            "used_clip": True,
            "downsampled": down_to_dpi is not None,
            "downsample_to_dpi": down_to_dpi,
            "source_pdf_image_count": int(source_pdf_audit.get("image_count", 0)),
            "possible_tiled_pdf": bool(source_pdf_audit.get("possible_tiled_pdf", False)),
            "image_path": str(output_path.relative_to(output_dir)),
        }
        manifest_path = output_path.with_suffix(".manifest.json")
        _write_json(manifest_path, manifest)
        manifest["manifest_path"] = str(manifest_path.relative_to(output_dir))
        variants[variant] = manifest

    return {
        "page": page,
        "block_id": block_id,
        "clip_rect_points": rect,
        "variants": variants,
    }


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


def build_pdf_dpi_row(
    *,
    page: str,
    block_id: str,
    gold: Any,
    main_value: Any,
    old_col_value: Any,
    variant_values: dict[str, Any],
) -> dict[str, Any]:
    main_diff = classify_observation_diff(gold, main_value)
    old_col_diff = classify_observation_diff(gold, old_col_value)
    variant_results: dict[str, Any] = {}
    for variant, value in variant_values.items():
        diff = classify_observation_diff(gold, value)
        variant_results[variant] = {
            "value": value,
            "eval_kind": diff["kind"],
            "metric": _metric_for_kind(diff["kind"]),
            "brief_diff": diff["brief_diff"],
        }
    return {
        "page": page,
        "block_id": block_id,
        "field": OBS_FIELD,
        "gold": gold,
        "main_value": main_value,
        "old_col_value": old_col_value,
        "main_kind": main_diff["kind"],
        "old_col_kind": old_col_diff["kind"],
        "variant_results": variant_results,
    }


def summarize_pdf_dpi_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = {variant: {metric: 0 for metric in SUMMARY_METRICS} for variant in DPI_VARIANTS}
    for row in rows:
        for variant, result in row.get("variant_results", {}).items():
            if variant not in source_counts:
                source_counts[variant] = {metric: 0 for metric in SUMMARY_METRICS}
            metric = result.get("metric")
            if metric in source_counts[variant]:
                source_counts[variant][metric] += 1
    return {
        "variants": list(DPI_VARIANTS),
        "source_counts": source_counts,
        "case_count": len(rows),
    }


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def _write_summary_table(lines: list[str], summary: dict[str, Any]) -> None:
    lines.extend([
        "| 图像版本 | 完全正确 | 规范化一致 | 仅标点差异 | 改写/概括 | 漏识别 | 过填 | 字符级错误 | 轻微等价差异 | 金标准需复核 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for variant in summary["variants"]:
        item = summary["source_counts"][variant]
        lines.append(
            f"| {variant} | {item['correct']} | {item['canonical_only']} | {item['punctuation_only']} | "
            f"{item['rewrite_or_paraphrase']} | {item['missing']} | {item['overfill']} | "
            f"{item['char_level_mismatch']} | {item['text_equivalent_minor']} | {item['gold_needs_check']} |"
        )


def write_pdf_dpi_report(
    output_dir: Path,
    *,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    sidecars: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar_dir = output_dir / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for sidecar in sidecars:
        path = sidecar_dir / f"{sidecar['page']}__{sidecar['block_id']}_pdf_dpi_probe.json"
        path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 病情观察 PDF 高 DPI Clip 识别验证",
        "",
        "说明：本实验只处理 observation residual cases；不修改主流程、不覆盖任何字段、不做整页 1200 DPI。",
        "",
        "## 汇总",
        "",
    ]
    _write_summary_table(lines, summary)
    lines.extend([
        "",
        "## 明细",
        "",
        "| 页面 | block | 金标准 | 主流程结果 | 旧单列结果 | 图像版本 | 识别结果 | 评估类型 | 简要差异 |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        for variant in summary["variants"]:
            result = row["variant_results"].get(variant, {})
            lines.append(
                f"| {row['page']} | {row['block_id']} | {_md_value(row['gold'])} | "
                f"{_md_value(row['main_value'])} | {_md_value(row['old_col_value'])} | "
                f"{variant} | {_md_value(result.get('value'))} | {result.get('eval_kind', '')} | "
                f"{_md_value(result.get('brief_diff', ''))} |"
            )
    (output_dir / "observation_pdf_dpi_probe_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_pdf_dpi_probe_summary.json").write_text(
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


class ObservationPdfDpiRunner:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[Any, str, str | None]:
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
                            {"type": "text", "text": PROMPT_COL_OBSERVATION},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            raw = response.choices[0].message.content or ""
            data = normalize_nulls(parse_model_json(raw))
            return data.get(OBS_FIELD), raw, None
        except Exception as exc:
            return None, raw, str(exc)


async def _recognize_case_variants(
    case: dict[str, Any],
    clip_payload: dict[str, Any],
    output_dir: Path,
    runner: ObservationPdfDpiRunner,
    reuse_sidecars: bool = False,
) -> dict[str, Any]:
    sidecar_path = output_dir / "sidecars" / f"{case['page']}__{case['block_id']}_pdf_dpi_probe.json"
    if reuse_sidecars and sidecar_path.exists():
        return read_json(sidecar_path)
    variant_results: dict[str, Any] = {}
    for variant in DPI_VARIANTS:
        image_path = output_dir / clip_payload["variants"][variant]["image_path"]
        value, raw, error = await runner.extract(image_path)
        variant_results[variant] = {
            "value": value,
            "_raw_response": raw,
            "_error": error or "",
            "image_path": clip_payload["variants"][variant]["image_path"],
            "manifest_path": clip_payload["variants"][variant]["manifest_path"],
        }
    return {
        "page": case["page"],
        "block_id": case["block_id"],
        "field": OBS_FIELD,
        "gold": case.get("gold"),
        "main_value": case.get("main_value"),
        "old_col_value": case.get("col_observation_value"),
        "clip_rect_points": case["clip_rect_points"],
        "variant_results": variant_results,
    }


def _load_pages(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(item) for item in pages]


def _hash_main_results(pages: list[dict[str, Any]]) -> dict[str, Any]:
    hashes: dict[str, Any] = {}
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
    hashes: dict[str, Any] = {}
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
    default_rect = parse_rect_points(args.rect) if args.rect else None
    case_rects = load_case_rects(Path(args.case_rects_json)) if args.case_rects_json else {}
    cases = select_cases(
        read_jsonl(Path(args.residual_cases_jsonl)),
        page_label=args.page_label or None,
        case_rects=case_rects,
        default_rect=default_rect,
    )
    if not cases:
        raise RuntimeError("no residual cases selected; provide --page-label/--rect or --case-rects-json")

    audit = audit_pdf_page(args.pdf_path, args.page_index)
    _write_json(output_dir / f"page{args.page_index}_pdf_audit.json", audit)
    clip_payloads = [
        render_case_variants(
            pdf_path=args.pdf_path,
            page_index=args.page_index,
            case=case,
            output_dir=output_dir,
            source_pdf_audit=audit,
        )
        for case in cases
    ]

    runner = ObservationPdfDpiRunner(cfg)
    start = time.time()
    sidecars = await asyncio.gather(*(
        _recognize_case_variants(case, clip_payload, output_dir, runner, reuse_sidecars=bool(args.reuse_sidecars))
        for case, clip_payload in zip(cases, clip_payloads)
    ))
    rows = [
        build_pdf_dpi_row(
            page=str(sidecar["page"]),
            block_id=str(sidecar["block_id"]),
            gold=sidecar.get("gold"),
            main_value=sidecar.get("main_value"),
            old_col_value=sidecar.get("old_col_value"),
            variant_values={
                variant: sidecar.get("variant_results", {}).get(variant, {}).get("value")
                for variant in DPI_VARIANTS
            },
        )
        for sidecar in sidecars
    ]
    summary = summarize_pdf_dpi_rows(rows)
    pages = _load_pages(Path(args.pages_json)) if args.pages_json else []
    enhanced_dir = Path(args.enhanced_results_dir) if args.enhanced_results_dir else None
    metadata = {
        "config": str(args.config),
        "pdf_path": str(args.pdf_path),
        "page_index": args.page_index,
        "page_label": args.page_label,
        "residual_cases_jsonl": str(args.residual_cases_jsonl),
        "case_count": len(cases),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "prompt": "PROMPT_COL_OBSERVATION",
        "model_calls": 0 if args.reuse_sidecars else len(cases) * len(DPI_VARIANTS),
        "elapsed_seconds": round(time.time() - start, 3),
        "source_pdf_image_count": audit.get("image_count"),
        "possible_tiled_pdf": audit.get("possible_tiled_pdf"),
        "main_result_hashes": _hash_main_results(pages),
        "result_enhanced_hashes": _hash_enhanced_results(enhanced_dir, pages),
    }
    write_pdf_dpi_report(output_dir, rows=rows, summary=summary, sidecars=sidecars, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run observation PDF high-DPI clip recognition probe.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pdf-path", required=True)
    parser.add_argument("--page-index", type=int, required=True)
    parser.add_argument("--page-label", default="")
    parser.add_argument("--residual-cases-jsonl", required=True)
    parser.add_argument("--case-rects-json", default="")
    parser.add_argument("--rect", default="", help="Fallback clip rect x0,y0,x1,y1 for all selected cases.")
    parser.add_argument("--pages-json", default="")
    parser.add_argument("--enhanced-results-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reuse-sidecars", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
