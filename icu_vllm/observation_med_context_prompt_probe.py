from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any, Sequence

from .config import PipelineConfig, load_config
from .json_utils import parse_model_json
from .observation_layered_eval import classify_layered_difference
from .observation_recognition_bottleneck_probe import IMAGE_VARIANT_LABELS, IMAGE_VARIANTS
from .observation_row_prompt_ablation import classify_raw_text_diff
from .observation_header_row_probe import combine_row_texts


MED_CONTEXT_PROMPT = """
你是一名用于医疗护理记录图像的精密转录助手。

任务：
请识别图像中“病情观察及处理”区域对应的正文内容。你的目标是逐字转录，而不是总结或改写。

转录原则：
1. 只转录正文内容，不要转录表头。
2. 不要总结、不要概括、不要改写句子。
3. 不要根据医学常识补充图中没有出现的内容。
4. 如果某个字符、数字、单位或缩写看不清，请在 uncertain_spans 中给出候选，不要强行唯一判断。
5. 医学/护理上下文可以作为弱先验，用于辅助判断模糊字符，但不能替代图像证据。
6. 对于数字、单位、英文缩写、药品名和人名/厂家名，请尽量保持图像原文，不要自行规范化大小写或单位写法。

常见医学/护理表达参考：
- 遵医嘱
- 泵入
- 胃管泵入
- 肠内营养液
- 肝素钠
- 咪达唑仑
- 枸橼酸舒芬太尼
- 舒芬太尼
- 氯化钠注射液
- 气管插管
- 呼吸机辅助通气
- VV-ECMO
- CVVHDF
- ECMO转速
- 血流量
- L/min
- r/min
- ml/h
- CPOT0分
- APTT

这些表达只作为弱参考，帮助你在字形很接近时判断；如果图像证据不同，必须以图像为准。

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

MED_METHOD = "Qwen3-32B:medical_context_prompt"
BASELINE_METHOD = "Qwen3-32B:precise_transcription_prompt"


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_med_context_response(raw: str) -> dict[str, Any]:
    try:
        data = parse_model_json(raw)
        text = data.get("transcription")
        transcription = text.strip() if isinstance(text, str) and text.strip() else None
        uncertain = data.get("uncertain_spans")
        if not isinstance(uncertain, list):
            uncertain = []
        return {
            "transcription": transcription,
            "uncertain_spans": uncertain,
            "visual_quality_note": str(data.get("visual_quality_note") or ""),
            "parse_error": "",
        }
    except Exception as exc:
        return {
            "transcription": None,
            "uncertain_spans": [],
            "visual_quality_note": "",
            "parse_error": repr(exc),
        }


def build_med_context_record(
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
        "prompt_name": "medical_context_prompt",
        "method_id": MED_METHOD,
        "text": text,
        "raw_response": raw_response,
        "parsed": parsed,
        "parse_error": parse_error,
    }


def load_precise_baseline_rows(summary_json: str | Path) -> list[dict[str, Any]]:
    data = read_json(summary_json)
    rows = []
    for row in data.get("rows", []):
        if row.get("method_id") != BASELINE_METHOD:
            continue
        rows.append({
            "case_id": row.get("case_id", ""),
            "page": row.get("page", ""),
            "block_id": row.get("block_id", ""),
            "gold": row.get("gold"),
            "input_version": row.get("image_variant", ""),
            "input_version_label": row.get("image_variant_label", ""),
            "method": BASELINE_METHOD,
            "method_label": row.get("method_label", "Qwen精密prompt"),
            "raw_prediction": row.get("recognized_text"),
            "edit_distance": int(row.get("edit_distance") or 0),
            "diff": row.get("brief_diff", ""),
            "original_error_type": row.get("error_type", ""),
            "layer": classify_layered_difference(row.get("gold"), row.get("recognized_text"), original_error_type=row.get("error_type", ""))["layer"],
        })
    return rows


def _row_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["case_id"]), str(row["input_version"])


def _map_med_records_to_rows(records: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline_by_case_variant = {_row_key(row): row for row in baseline_rows}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        case_id = f"{record['page']}__{record['block_id']}"
        key = (case_id, record["image_variant"])
        grouped.setdefault(key, []).append(record)
    rows = []
    for key, group in grouped.items():
        baseline = baseline_by_case_variant.get(key)
        if not baseline:
            continue
        first = group[0]
        row_texts = {str(record["row_id"]): record.get("text") for record in group}
        combined_text = combine_row_texts(row_texts)
        uncertain_spans = []
        visual_notes = []
        for record in sorted(group, key=lambda item: str(item.get("row_id", ""))):
            parsed = record.get("parsed", {}) if isinstance(record.get("parsed"), dict) else {}
            uncertain_spans.extend(parsed.get("uncertain_spans", []) if isinstance(parsed.get("uncertain_spans"), list) else [])
            if parsed.get("visual_quality_note"):
                visual_notes.append(str(parsed["visual_quality_note"]))
        diff = classify_raw_text_diff(baseline.get("gold"), combined_text)
        layer = classify_layered_difference(baseline.get("gold"), combined_text, original_error_type=diff["error_type"])["layer"]
        rows.append({
            "case_id": key[0],
            "page": first["page"],
            "block_id": first["block_id"],
            "gold": baseline.get("gold"),
            "input_version": key[1],
            "input_version_label": IMAGE_VARIANT_LABELS.get(key[1], key[1]),
            "method": MED_METHOD,
            "method_label": "Qwen医学参考prompt",
            "raw_prediction": combined_text,
            "edit_distance": int(diff["edit_distance"]),
            "diff": diff["brief_diff"],
            "original_error_type": diff["error_type"],
            "layer": layer,
            "uncertain_spans": uncertain_spans,
            "visual_quality_note": "; ".join(dict.fromkeys(visual_notes)),
        })
    return rows


def compare_prompt_rows(baseline_rows: list[dict[str, Any]], med_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline_map = {_row_key(row): row for row in baseline_rows}
    compared = []
    for med in med_rows:
        baseline = baseline_map.get(_row_key(med))
        if not baseline:
            continue
        delta = int(med.get("edit_distance") or 0) - int(baseline.get("edit_distance") or 0)
        if delta < 0:
            change = "improved"
        elif delta > 0:
            change = "worse"
        else:
            change = "same"
        compared.append({
            "case_id": med["case_id"],
            "input_version": med["input_version"],
            "input_version_label": med["input_version_label"],
            "gold": med.get("gold"),
            "baseline_prediction": baseline.get("raw_prediction"),
            "med_context_prediction": med.get("raw_prediction"),
            "baseline_edit_distance": baseline.get("edit_distance"),
            "med_context_edit_distance": med.get("edit_distance"),
            "delta_edit_distance": delta,
            "baseline_layer": baseline.get("layer"),
            "med_context_layer": med.get("layer"),
            "baseline_diff": baseline.get("diff"),
            "med_context_diff": med.get("diff"),
            "change": change,
            "uncertain_spans": med.get("uncertain_spans", []),
            "visual_quality_note": med.get("visual_quality_note", ""),
        })
    return compared


def _empty_counts() -> dict[str, int]:
    return {"improved": 0, "same": 0, "worse": 0}


def summarize_prompt_comparison(compared: list[dict[str, Any]]) -> dict[str, Any]:
    overall = _empty_counts()
    by_variant: dict[str, dict[str, Any]] = {}
    for row in compared:
        overall[row["change"]] += 1
        item = by_variant.setdefault(
            row["input_version"],
            {
                "input_version": row["input_version"],
                "input_version_label": row["input_version_label"],
                "total": 0,
                **_empty_counts(),
                "baseline_edit_distance_total": 0,
                "med_context_edit_distance_total": 0,
                "baseline_unit_style_pass": 0,
                "med_context_unit_style_pass": 0,
            },
        )
        item["total"] += 1
        item[row["change"]] += 1
        item["baseline_edit_distance_total"] += int(row.get("baseline_edit_distance") or 0)
        item["med_context_edit_distance_total"] += int(row.get("med_context_edit_distance") or 0)
        if row.get("baseline_layer") in {"strict_exact", "punctuation_space_normalized_exact", "ascii_case_normalized_exact", "unit_style_normalized_exact"}:
            item["baseline_unit_style_pass"] += 1
        if row.get("med_context_layer") in {"strict_exact", "punctuation_space_normalized_exact", "ascii_case_normalized_exact", "unit_style_normalized_exact"}:
            item["med_context_unit_style_pass"] += 1
    for item in by_variant.values():
        total = max(1, int(item["total"]))
        item["baseline_avg_edit_distance"] = round(item["baseline_edit_distance_total"] / total, 2)
        item["med_context_avg_edit_distance"] = round(item["med_context_edit_distance_total"] / total, 2)
        item["baseline_unit_style_pass_rate"] = round(item["baseline_unit_style_pass"] / total, 4)
        item["med_context_unit_style_pass_rate"] = round(item["med_context_unit_style_pass"] / total, 4)
    return {
        "overall": overall,
        "by_variant": sorted(by_variant.values(), key=lambda item: item["input_version"]),
        "total": len(compared),
    }


class QwenRunner:
    def __init__(self, cfg: PipelineConfig):
        from openai import AsyncOpenAI

        self.cfg = cfg
        self.client = AsyncOpenAI(base_url=cfg.vllm_base_url, api_key=cfg.vllm_api_key, timeout=cfg.timeout_seconds)
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def _encode(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    async def extract(self, image_path: Path) -> tuple[dict[str, Any], str, str]:
        kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            kwargs["extra_body"] = {"mm_processor_kwargs": self.cfg.mm_processor_kwargs}
        raw = ""
        try:
            image_b64 = self._encode(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": MED_CONTEXT_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=1024,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **kwargs,
                )
            raw = response.choices[0].message.content or ""
            parsed = parse_med_context_response(raw)
            return parsed, raw, parsed.get("parse_error", "")
        except Exception as exc:
            return {"transcription": None, "uncertain_spans": [], "visual_quality_note": "", "parse_error": repr(exc)}, raw, repr(exc)


def _sidecar_paths(source_run_dir: Path) -> list[Path]:
    return sorted((source_run_dir / "sidecars").glob("*_recognition_bottleneck.json"))


async def run_qwen_stage(args: argparse.Namespace) -> None:
    source_run_dir = Path(args.source_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_config(Path(args.config))
    runner = QwenRunner(cfg)
    all_records = []
    for sidecar_path in _sidecar_paths(source_run_dir):
        sidecar = read_json(sidecar_path)
        tasks = []
        meta = []
        for row in sidecar.get("rows", []):
            row_id = str(row["row_id"])
            for variant in IMAGE_VARIANTS:
                info = row["image_variants"].get(variant)
                if not info:
                    continue
                tasks.append(runner.extract(source_run_dir / info["image_path"]))
                meta.append((sidecar, row_id, variant))
        results = await asyncio.gather(*tasks)
        sidecar_records = []
        for (source_sidecar, row_id, variant), (parsed, raw, error) in zip(meta, results):
            record = build_med_context_record(
                page=source_sidecar["page"],
                block_id=source_sidecar["block_id"],
                row_id=row_id,
                image_variant=variant,
                text=parsed.get("transcription") if isinstance(parsed, dict) else None,
                raw_response=raw,
                parsed=parsed,
                parse_error=error or "",
            )
            sidecar_records.append(record)
            all_records.append(record)
        out_path = output_dir / "sidecars" / f"{sidecar['page']}__{sidecar['block_id']}_med_context_prompt.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"source_sidecar": str(sidecar_path), "records": sidecar_records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "med_context_prompt_records.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in all_records),
        encoding="utf-8",
    )


def _load_med_records(output_dir: Path) -> list[dict[str, Any]]:
    path = output_dir / "med_context_prompt_records.jsonl"
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _md(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_report(output_dir: Path, compared: list[dict[str, Any]], summary: dict[str, Any], metadata: dict[str, Any]) -> None:
    lines = [
        "# 病情观察及处理：医学表达参考 Prompt 对照实验",
        "",
        "说明：本实验只新增 VLM prompt 对照，不跑 OCR，不改主结果，不做纠错或替换规则。",
        "",
        "## 输入",
        "",
        f"- source run: `{metadata['source_run_dir']}`",
        f"- baseline summary: `{metadata['baseline_summary_json']}`",
        f"- total comparisons: {summary['total']}",
        "",
        "## 总体变化",
        "",
        f"- improved: {summary['overall']['improved']}",
        f"- same: {summary['overall']['same']}",
        f"- worse: {summary['overall']['worse']}",
        "",
        "## 按输入版本统计",
        "",
        "| 输入版本 | 总数 | improved | same | worse | baseline平均编辑距离 | 新prompt平均编辑距离 | baseline分层通过率 | 新prompt分层通过率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["by_variant"]:
        lines.append(
            f"| {row['input_version_label']} | {row['total']} | {row['improved']} | {row['same']} | {row['worse']} | "
            f"{row['baseline_avg_edit_distance']} | {row['med_context_avg_edit_distance']} | "
            f"{row['baseline_unit_style_pass_rate']:.2%} | {row['med_context_unit_style_pass_rate']:.2%} |"
        )
    lines.extend([
        "",
        "## 详细对比",
        "",
        "| case_id | 输入版本 | gold | baseline预测 | 新prompt预测 | baseline层级 | 新prompt层级 | Δ编辑距离 | 变化 | 新prompt diff |",
        "|---|---|---|---|---|---|---|---:|---|---|",
    ])
    for row in compared:
        lines.append(
            f"| {row['case_id']} | {row['input_version_label']} | {_md(row['gold'])} | "
            f"{_md(row['baseline_prediction'])} | {_md(row['med_context_prediction'])} | "
            f"{row['baseline_layer']} | {row['med_context_layer']} | {row['delta_edit_distance']} | "
            f"{row['change']} | {_md(row['med_context_diff'])} |"
        )
    best = min(summary["by_variant"], key=lambda row: (row["med_context_avg_edit_distance"], -row["med_context_unit_style_pass_rate"])) if summary["by_variant"] else None
    lines.extend([
        "",
        "## 结论",
        "",
    ])
    if best:
        lines.append(
            f"- 本轮最佳输入版本按新 prompt 平均编辑距离看是 `{best['input_version']}`，"
            f"新 prompt 平均编辑距离 {best['med_context_avg_edit_distance']}，分层通过率 {best['med_context_unit_style_pass_rate']:.2%}。"
        )
    lines.extend([
        "- 如果 improved 明显多于 worse，说明常见表达弱参考有收益；如果 worse 接近或超过 improved，则说明列词表会带来先验干扰。",
        "- 本报告只做候选判断，不建议直接覆盖主结果。",
    ])
    (output_dir / "observation_med_context_prompt_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "observation_med_context_prompt_summary.json").write_text(
        json.dumps({"metadata": metadata, "summary": summary, "comparisons": compared}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def finalize_report(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    baseline = load_precise_baseline_rows(Path(args.baseline_summary_json))
    med_records = _load_med_records(output_dir)
    med_rows = _map_med_records_to_rows(med_records, baseline)
    compared = compare_prompt_rows(baseline, med_rows)
    summary = summarize_prompt_comparison(compared)
    metadata = {
        "source_run_dir": str(args.source_run_dir),
        "baseline_summary_json": str(args.baseline_summary_json),
    }
    write_report(output_dir, compared, summary, metadata)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run VLM medical context prompt probe for observation row crops.")
    parser.add_argument("--stage", choices=["qwen", "finalize"], required=True)
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--baseline-summary-json", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    start = time.time()
    if args.stage == "qwen":
        asyncio.run(run_qwen_stage(args))
    elif args.stage == "finalize":
        finalize_report(args)
    print(f"{args.stage} done in {time.time() - start:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
