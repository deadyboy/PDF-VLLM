from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import PipelineConfig, load_config
from .iv_eval import classify_iv_diff, is_report_correct
from .json_utils import normalize_nulls, parse_model_json
from .prompts import (
    PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE,
    PROMPT_COL_OBSERVATION_DIRECT_V2,
    PROMPT_COL_TUBE_CARE,
)
from .target_column_iv_rawlines import IV_FIELD, _as_raw_lines, parse_iv_rawlines_response, raw_lines_tail_kind
from .target_column_vlm import by_block, classify_diff, is_correct, read_json, read_rows, sha256_file


TUBE_FIELD = "管路护理"
OBS_FIELD = "病情观察及处理"
HIGH_RISK_FIELDS = (IV_FIELD, TUBE_FIELD, OBS_FIELD)
FIELD_STRATEGIES = {
    IV_FIELD: "iv_v4_preserve_case_clean2x",
    TUBE_FIELD: "tube_care_single_col_vlm",
    OBS_FIELD: "observation_direct_v2",
}


def _field_diff(field: str, gold: Any, actual: Any) -> dict[str, Any]:
    if field == IV_FIELD:
        return classify_iv_diff(gold, actual)
    return classify_diff(gold, actual)


def _field_correct(field: str, kind: str) -> bool:
    if field == IV_FIELD:
        return is_report_correct(kind)
    return is_correct(kind)


def build_high_risk_row(
    page: str,
    block_id: str,
    field: str,
    strategy: str,
    gold: Any,
    main_actual: Any,
    candidate_actual: Any,
    raw_lines: list[str] | None = None,
    needs_review: bool = False,
    reason: str = "",
    image_path: str = "",
) -> dict[str, Any]:
    main_diff = _field_diff(field, gold, main_actual)
    candidate_diff = _field_diff(field, gold, candidate_actual)
    main_ok = _field_correct(field, main_diff["kind"])
    candidate_ok = _field_correct(field, candidate_diff["kind"])
    row = {
        "page": page,
        "block_id": block_id,
        "field": field,
        "strategy": strategy,
        "gold": gold,
        "main_actual": main_actual,
        "candidate_actual": candidate_actual,
        "main_eval_kind": main_diff["kind"],
        "candidate_eval_kind": candidate_diff["kind"],
        "main_report_correct": main_ok,
        "candidate_report_correct": candidate_ok,
        "raw_lines": raw_lines or [],
        "needs_review": bool(needs_review),
        "reason": reason or "",
        "image_path": image_path,
    }
    if field == IV_FIELD:
        row["tail_kind"] = raw_lines_tail_kind(gold, candidate_actual, raw_lines or [])
    else:
        row["tail_kind"] = "none"
    return row


def _empty_counts() -> dict[str, Any]:
    return {
        "total": 0,
        "main_correct": 0,
        "candidate_correct": 0,
        "main_wrong_candidate_correct": 0,
        "main_correct_candidate_wrong": 0,
        "both_wrong": 0,
        "candidate_missing": 0,
        "candidate_overfill": 0,
        "needs_review_true": 0,
        "correct_but_needs_review": 0,
        "eval_kind_counts": {},
    }


def _add_row(counts: dict[str, Any], row: dict[str, Any]) -> None:
    counts["total"] += 1
    main_ok = bool(row["main_report_correct"])
    cand_ok = bool(row["candidate_report_correct"])
    if main_ok:
        counts["main_correct"] += 1
    if cand_ok:
        counts["candidate_correct"] += 1
    if not main_ok and cand_ok:
        counts["main_wrong_candidate_correct"] += 1
    elif main_ok and not cand_ok:
        counts["main_correct_candidate_wrong"] += 1
    elif not main_ok and not cand_ok:
        counts["both_wrong"] += 1
    if row["candidate_eval_kind"] == "missing":
        counts["candidate_missing"] += 1
    if row["candidate_eval_kind"] == "overfill":
        counts["candidate_overfill"] += 1
    if row["needs_review"]:
        counts["needs_review_true"] += 1
    if cand_ok and row["needs_review"]:
        counts["correct_but_needs_review"] += 1
    eval_counts = counts["eval_kind_counts"]
    eval_counts[row["candidate_eval_kind"]] = eval_counts.get(row["candidate_eval_kind"], 0) + 1


def summarize_high_risk_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "overall": _empty_counts(),
        "fields": {field: _empty_counts() for field in HIGH_RISK_FIELDS},
    }
    for row in rows:
        _add_row(summary["overall"], row)
        if row["field"] in summary["fields"]:
            _add_row(summary["fields"][row["field"]], row)
    return summary


def _md_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def write_high_risk_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# High Risk Strategy Review",
        "",
        "## Current Strategies",
        "",
        "| field | strategy |",
        "| --- | --- |",
    ]
    for field in HIGH_RISK_FIELDS:
        lines.append(f"| {field} | {FIELD_STRATEGIES[field]} |")
    lines.extend([
        "",
        "## Summary",
        "",
        "| field | total | main_correct | candidate_correct | main_wrong_candidate_correct | main_correct_candidate_wrong | both_wrong | candidate_missing | candidate_overfill | needs_review_true | correct_but_needs_review | eval_kind_counts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for label, counts in [("OVERALL", summary["overall"])] + list(summary["fields"].items()):
        lines.append(
            f"| {label} | {counts['total']} | {counts['main_correct']} | "
            f"{counts['candidate_correct']} | {counts['main_wrong_candidate_correct']} | "
            f"{counts['main_correct_candidate_wrong']} | {counts['both_wrong']} | "
            f"{counts['candidate_missing']} | {counts['candidate_overfill']} | "
            f"{counts['needs_review_true']} | {counts['correct_but_needs_review']} | "
            f"{_md_value(json.dumps(counts['eval_kind_counts'], ensure_ascii=False))} |"
        )
    lines.extend([
        "",
        "## Details",
        "",
        "| page | block_id | field | strategy | gold | main_actual | candidate_actual | main_eval_kind | candidate_eval_kind | needs_review | tail_kind | reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            f"| {row['page']} | {row['block_id']} | {row['field']} | {row['strategy']} | "
            f"{_md_value(row['gold'])} | {_md_value(row['main_actual'])} | "
            f"{_md_value(row['candidate_actual'])} | {row['main_eval_kind']} | "
            f"{row['candidate_eval_kind']} | {row['needs_review']} | {row['tail_kind']} | "
            f"{_md_value(row['reason'])} |"
        )
    payload = {"metadata": metadata or {}, "summary": summary, "rows": rows}
    (output_dir / "high_risk_strategy_review_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    (output_dir / "high_risk_strategy_review_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pages(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError(f"pages json must contain a list: {path}")
    return [dict(page) for page in pages]


def _block_sort_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.name.split("_")[1]), path.name
    except Exception:
        return 999999, path.name


class HighRiskStrategyRunner:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.client = AsyncOpenAI(
            base_url=cfg.vllm_base_url,
            api_key=cfg.vllm_api_key,
            timeout=cfg.timeout_seconds,
        )
        self.semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)

    @staticmethod
    def encode_image_base64(img_path: Path) -> str:
        return base64.b64encode(img_path.read_bytes()).decode("utf-8")

    async def _chat(self, image_path: Path, prompt: str) -> tuple[str, str | None]:
        if not image_path.exists():
            return "", f"missing image: {image_path}"
        request_kwargs: dict[str, Any] = {}
        if self.cfg.mm_processor_kwargs:
            request_kwargs["extra_body"] = {"mm_processor_kwargs": self.cfg.mm_processor_kwargs}
        raw = ""
        try:
            img_b64 = self.encode_image_base64(image_path)
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        ],
                    }],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    **request_kwargs,
                )
            raw = response.choices[0].message.content or ""
            return raw, None
        except Exception as exc:
            return raw, str(exc)

    async def extract_iv(self, image_path: Path) -> tuple[Any, list[str], bool, str, str, str | None]:
        raw, error = await self._chat(image_path, PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE)
        if error:
            return None, [], True, "request_error", raw, error
        raw_lines, final_value, needs_review, reason, parse_error = parse_iv_rawlines_response(raw)
        return final_value, raw_lines, needs_review, reason, raw, parse_error

    async def extract_direct_field(self, image_path: Path, field: str, prompt: str) -> tuple[Any, str, str | None]:
        raw, error = await self._chat(image_path, prompt)
        if error:
            return None, raw, error
        try:
            data = normalize_nulls(parse_model_json(raw))
        except Exception as exc:
            return None, raw, str(exc)
        return data.get(field), raw, None


def _read_sidecar_rows(sidecar_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(sidecar_dir.glob("block_*_high_risk_strategy.json"), key=_block_sort_key):
        data = read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    return rows


async def run_page(
    page: dict[str, Any],
    source_run_dir: Path,
    clean2x_run_dir: Path,
    output_dir: Path,
    runner: HighRiskStrategyRunner,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_label = str(page["page"])
    gold_path = Path(page["gold_json"])
    main_path = Path(page["main_result_json"])
    before_hash = sha256_file(main_path)
    source_slice_dir = source_run_dir / "slices" / page_label
    clean2x_crop_dir = clean2x_run_dir / "crops" / page_label
    sidecar_dir = output_dir / "sidecars" / page_label
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    block_ids = sorted(
        {
            path.name.split("_col_", 1)[0]
            for path in list(source_slice_dir.glob("block_*_col_tube_care.png"))
            + list(source_slice_dir.glob("block_*_col_observation.png"))
            + list(clean2x_crop_dir.glob("block_*_col_iv_drug_clean_2x.png"))
        }
    )

    async def process_block(block_id: str) -> None:
        iv_path = clean2x_crop_dir / f"{block_id}_col_iv_drug_clean_2x.png"
        tube_path = source_slice_dir / f"{block_id}_col_tube_care.png"
        obs_path = source_slice_dir / f"{block_id}_col_observation.png"
        iv_task = runner.extract_iv(iv_path)
        tube_task = runner.extract_direct_field(tube_path, TUBE_FIELD, PROMPT_COL_TUBE_CARE)
        obs_task = runner.extract_direct_field(obs_path, OBS_FIELD, PROMPT_COL_OBSERVATION_DIRECT_V2)
        (iv_value, iv_raw_lines, iv_review, iv_reason, iv_raw, iv_error), (
            tube_value,
            tube_raw,
            tube_error,
        ), (obs_value, obs_raw, obs_error) = await asyncio.gather(iv_task, tube_task, obs_task)
        payload = {
            "block_id": block_id,
            "values": {
                IV_FIELD: iv_value,
                TUBE_FIELD: tube_value,
                OBS_FIELD: obs_value,
            },
            "strategies": FIELD_STRATEGIES,
            "raw_lines": {IV_FIELD: iv_raw_lines},
            "needs_review": {IV_FIELD: bool(iv_review), TUBE_FIELD: False, OBS_FIELD: False},
            "reasons": {IV_FIELD: iv_reason or "", TUBE_FIELD: "", OBS_FIELD: ""},
            "raw_responses": {IV_FIELD: iv_raw, TUBE_FIELD: tube_raw, OBS_FIELD: obs_raw},
            "image_paths": {
                IV_FIELD: str(iv_path.relative_to(clean2x_run_dir)) if iv_path.exists() else str(iv_path),
                TUBE_FIELD: str(tube_path.relative_to(source_run_dir)) if tube_path.exists() else str(tube_path),
                OBS_FIELD: str(obs_path.relative_to(source_run_dir)) if obs_path.exists() else str(obs_path),
            },
            "errors": {},
        }
        for field, error in ((IV_FIELD, iv_error), (TUBE_FIELD, tube_error), (OBS_FIELD, obs_error)):
            if error:
                payload["errors"][field] = error
        (sidecar_dir / f"{block_id}_high_risk_strategy.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    await asyncio.gather(*(process_block(block_id) for block_id in block_ids))

    gold_blocks = by_block(read_rows(gold_path))
    main_blocks = by_block(read_rows(main_path))
    candidate_blocks = by_block(_read_sidecar_rows(sidecar_dir))
    all_block_ids = sorted(
        {block_id for block_id in set(gold_blocks) | set(main_blocks) | set(candidate_blocks) if block_id.startswith("block_")}
    )
    rows = []
    for block_id in all_block_ids:
        gold_row = gold_blocks.get(block_id, {})
        main_row = main_blocks.get(block_id, {})
        candidate_row = candidate_blocks.get(block_id, {})
        values = candidate_row.get("values", {})
        raw_lines_by_field = candidate_row.get("raw_lines", {})
        review_by_field = candidate_row.get("needs_review", {})
        reasons = candidate_row.get("reasons", {})
        image_paths = candidate_row.get("image_paths", {})
        for field in HIGH_RISK_FIELDS:
            rows.append(
                build_high_risk_row(
                    page=page_label,
                    block_id=block_id,
                    field=field,
                    strategy=FIELD_STRATEGIES[field],
                    gold=gold_row.get(field),
                    main_actual=main_row.get(field),
                    candidate_actual=values.get(field),
                    raw_lines=_as_raw_lines(raw_lines_by_field.get(field)),
                    needs_review=bool(review_by_field.get(field, False)),
                    reason=str(reasons.get(field) or ""),
                    image_path=str(image_paths.get(field) or ""),
                )
            )
    after_hash = sha256_file(main_path)
    return rows, {
        "path": str(main_path),
        "before": before_hash,
        "after": after_hash,
        "unchanged": before_hash == after_hash,
        "blocks": len(block_ids),
        "sidecars": len(list(sidecar_dir.glob("block_*_high_risk_strategy.json"))),
    }


async def run_experiment(args: argparse.Namespace) -> None:
    cfg = load_config(Path(args.config))
    source_run_dir = Path(args.source_run_dir)
    clean2x_run_dir = Path(args.clean2x_run_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(Path(args.pages_json))
    runner = HighRiskStrategyRunner(cfg)
    start = time.time()
    rows: list[dict[str, Any]] = []
    hashes: dict[str, Any] = {}
    for page in pages:
        page_rows, page_hash = await run_page(page, source_run_dir, clean2x_run_dir, output_dir, runner)
        rows.extend(page_rows)
        hashes[str(page["page"])] = page_hash
    summary = summarize_high_risk_rows(rows)
    metadata = {
        "config": str(args.config),
        "pages_json": str(args.pages_json),
        "source_run_dir": str(source_run_dir),
        "clean2x_run_dir": str(clean2x_run_dir),
        "model_name": cfg.model_name,
        "vllm_base_url": cfg.vllm_base_url,
        "elapsed_seconds": round(time.time() - start, 3),
        "main_result_hashes": hashes,
        "strategies": FIELD_STRATEGIES,
    }
    write_high_risk_report(output_dir, rows, summary, metadata=metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run combined high-risk field strategy review.")
    parser.add_argument("--config", default="config/benchmark_qwen3_32b.toml")
    parser.add_argument("--pages-json", required=True)
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--clean2x-run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    asyncio.run(run_experiment(args))


if __name__ == "__main__":
    main()
