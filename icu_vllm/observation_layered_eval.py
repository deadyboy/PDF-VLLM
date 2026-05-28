from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Sequence


LAYERS = (
    "strict_exact",
    "punctuation_space_normalized_exact",
    "ascii_case_normalized_exact",
    "unit_style_normalized_exact",
    "meaningful_text_difference",
    "severe_failure",
)
SEVERE_ORIGINAL_TYPES = {"漏识别", "过填", "改写/概括", "串行"}
QWEN_PREFIX = "Qwen3-32B"
PADDLE_PREFIX = "PaddleOCR"


def _has_text(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "null", "none"}
    return True


def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def normalize_punctuation_space(value: Any) -> str | None:
    if not _has_text(value):
        return None
    text = _to_text(value)
    replacements = {
        "：": ":",
        "，": ",",
        "；": ";",
        "（": "(",
        "）": ")",
        "　": " ",
        "。": ".",
        "．": ".",
        "、": ",",
        "％": "%",
        "＋": "+",
        "－": "-",
        "×": "x",
        "—": "-",
        "–": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", "", text)
    return text


def normalize_ascii_case(value: Any) -> str | None:
    text = normalize_punctuation_space(value)
    if text is None:
        return None
    return "".join(ch.lower() if ch.isascii() else ch for ch in text)


def normalize_unit_style(value: Any) -> str | None:
    text = normalize_ascii_case(value)
    if text is None:
        return None
    # Generic unit typography normalization only. This does not change digits or
    # map visually similar non-unit characters such as 1/l, 0/O, 泵/泉.
    text = text.replace("µ", "μ")
    text = text.replace("μg", "ug")
    text = text.replace("℃", "°c")
    return text


def classify_layered_difference(gold: Any, actual: Any, *, original_error_type: str = "") -> dict[str, Any]:
    if original_error_type in SEVERE_ORIGINAL_TYPES:
        layer = "severe_failure"
    elif gold == actual:
        layer = "strict_exact"
    elif normalize_punctuation_space(gold) == normalize_punctuation_space(actual) and normalize_punctuation_space(gold) is not None:
        layer = "punctuation_space_normalized_exact"
    elif normalize_ascii_case(gold) == normalize_ascii_case(actual) and normalize_ascii_case(gold) is not None:
        layer = "ascii_case_normalized_exact"
    elif normalize_unit_style(gold) == normalize_unit_style(actual) and normalize_unit_style(gold) is not None:
        layer = "unit_style_normalized_exact"
    else:
        layer = "meaningful_text_difference"
    return {
        "layer": layer,
        "gold": gold,
        "actual": actual,
        "gold_punctuation_norm": normalize_punctuation_space(gold),
        "actual_punctuation_norm": normalize_punctuation_space(actual),
        "gold_ascii_case_norm": normalize_ascii_case(gold),
        "actual_ascii_case_norm": normalize_ascii_case(actual),
        "gold_unit_style_norm": normalize_unit_style(gold),
        "actual_unit_style_norm": normalize_unit_style(actual),
    }


def load_previous_rows(summary_json: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(summary_json).read_text(encoding="utf-8"))
    rows = data.get("rows", [])
    mapped: list[dict[str, Any]] = []
    for row in rows:
        if row.get("skipped"):
            continue
        gold = row.get("gold")
        actual = row.get("recognized_text")
        original_error_type = str(row.get("error_type", ""))
        layered = classify_layered_difference(gold, actual, original_error_type=original_error_type)
        mapped.append({
            "case_id": row.get("case_id", ""),
            "page": row.get("page", ""),
            "block_id": row.get("block_id", ""),
            "gold": gold,
            "input_version": row.get("image_variant", row.get("input_variant", "")),
            "input_version_label": row.get("image_variant_label", row.get("input_variant_label", "")),
            "method": row.get("method_id", row.get("source", "")),
            "method_label": row.get("method_label", row.get("source_label", "")),
            "raw_prediction": actual,
            "edit_distance": row.get("edit_distance"),
            "diff": row.get("brief_diff", ""),
            "original_error_type": original_error_type,
            **layered,
        })
    return mapped


def _empty_counts() -> dict[str, int]:
    return {layer: 0 for layer in LAYERS}


def _passes_through(layer: str, max_layer: str) -> bool:
    order = {name: idx for idx, name in enumerate(LAYERS)}
    return order[layer] <= order[max_layer]


def _group_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["input_version"]), str(row["method"])


def summarize_layered_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    overall = _empty_counts()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        layer = str(row["layer"])
        overall[layer] += 1
        key = _group_key(row)
        item = grouped.setdefault(
            key,
            {
                "input_version": row["input_version"],
                "input_version_label": row["input_version_label"],
                "method": row["method"],
                "method_label": row["method_label"],
                "total": 0,
                "edit_distance_total": 0.0,
                **_empty_counts(),
            },
        )
        item["total"] += 1
        try:
            item["edit_distance_total"] += float(row.get("edit_distance") or 0)
        except (TypeError, ValueError):
            pass
        item[layer] += 1

    by_input_method = []
    for item in grouped.values():
        total = max(1, int(item["total"]))
        item["average_edit_distance"] = round(float(item["edit_distance_total"]) / total, 2)
        item["strict_pass_rate"] = round(item["strict_exact"] / total, 4)
        item["punctuation_space_pass_rate"] = round(
            sum(item[layer] for layer in LAYERS if _passes_through(layer, "punctuation_space_normalized_exact")) / total,
            4,
        )
        item["ascii_case_pass_rate"] = round(
            sum(item[layer] for layer in LAYERS if _passes_through(layer, "ascii_case_normalized_exact")) / total,
            4,
        )
        item["unit_style_pass_rate"] = round(
            sum(item[layer] for layer in LAYERS if _passes_through(layer, "unit_style_normalized_exact")) / total,
            4,
        )
        by_input_method.append(item)
    by_input_method.sort(key=lambda item: (item["input_version"], item["method"]))
    return {
        "overall": overall,
        "total": len(rows),
        "by_input_method": by_input_method,
    }


def _best_qwen_combo(summary: dict[str, Any]) -> dict[str, Any] | None:
    qwen_rows = [row for row in summary["by_input_method"] if str(row["method"]).startswith(QWEN_PREFIX)]
    if not qwen_rows:
        return None
    return max(
        qwen_rows,
        key=lambda row: (
            row["unit_style_pass_rate"],
            row["punctuation_space_pass_rate"],
            -row.get("average_edit_distance", 999999),
            -row["meaningful_text_difference"],
            -row["severe_failure"],
        ),
    )


def _source_totals(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sources = {
        "Qwen": [row for row in rows if str(row["method"]).startswith(QWEN_PREFIX)],
        "PaddleOCR": [row for row in rows if str(row["method"]).startswith(PADDLE_PREFIX)],
    }
    result: dict[str, dict[str, Any]] = {}
    for source, source_rows in sources.items():
        summary = summarize_layered_rows(source_rows)
        counts = summary["overall"]
        total = max(1, len(source_rows))
        result[source] = {
            "total": len(source_rows),
            **counts,
            "unit_style_pass_rate": round(
                (counts["strict_exact"] + counts["punctuation_space_normalized_exact"] + counts["ascii_case_normalized_exact"] + counts["unit_style_normalized_exact"]) / total,
                4,
            ),
        }
    return result


def _md(value: Any) -> str:
    if value is None:
        return "null"
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def _append_counts_table(lines: list[str], title: str, rows: list[dict[str, Any]]) -> None:
    lines.extend([
        "",
        f"## {title}",
        "",
        "| 输入版本 | 方法 | 总数 | strict_exact | punctuation_space | ascii_case | unit_style | meaningful_text_difference | severe_failure | 平均编辑距离 | unit_style通过率 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        lines.append(
            f"| {row['input_version_label']} | {row['method_label']} | {row['total']} | "
            f"{row['strict_exact']} | {row['punctuation_space_normalized_exact']} | "
            f"{row['ascii_case_normalized_exact']} | {row['unit_style_normalized_exact']} | "
            f"{row['meaningful_text_difference']} | {row['severe_failure']} | {row.get('average_edit_distance', 0)} | {row['unit_style_pass_rate']:.2%} |"
        )


def build_report(rows: list[dict[str, Any]], summary: dict[str, Any], metadata: dict[str, Any]) -> str:
    source_totals = _source_totals(rows)
    best_qwen = _best_qwen_combo(summary)
    meaningful = [row for row in rows if row["layer"] == "meaningful_text_difference"]
    severe = [row for row in rows if row["layer"] == "severe_failure"]
    lines = [
        "# 病情观察及处理：分层评估重算报告",
        "",
        "说明：本报告只读取上一轮实验产物并重算评估层级；不重新调用模型，不修改 raw_prediction，不写回任何主结果。",
        "",
        "## 原始输入",
        "",
        f"- source summary: `{metadata['source_summary_json']}`",
        f"- total rows: {summary['total']}",
        "",
        "## 层级定义",
        "",
        "- strict_exact：原始文本完全一致。",
        "- punctuation_space_normalized_exact：忽略空格、全角/半角标点、中文/英文括号、逗号、冒号、分号等格式差异。",
        "- ascii_case_normalized_exact：在上一层基础上忽略英文字母大小写差异。",
        "- unit_style_normalized_exact：在上一层基础上允许常见单位排版差异，例如 μg/ug、℃/°C，不改变数字。",
        "- meaningful_text_difference：仍存在数字、药名、设备缩写、中文近形字、剂量/速度等非格式差异。",
        "- severe_failure：漏识别、过填、改写/概括、串行。",
        "",
        "## 原始严格评估统计",
        "",
        f"- strict_exact: {summary['overall']['strict_exact']}",
        f"- non_strict: {summary['total'] - summary['overall']['strict_exact']}",
        "",
        "## punctuation_space_normalized 后统计",
        "",
        f"- 新增通过: {summary['overall']['punctuation_space_normalized_exact']}",
        f"- 累计通过: {summary['overall']['strict_exact'] + summary['overall']['punctuation_space_normalized_exact']}",
        "",
        "## ascii_case_normalized 后统计",
        "",
        f"- 新增通过: {summary['overall']['ascii_case_normalized_exact']}",
        f"- 累计通过: {summary['overall']['strict_exact'] + summary['overall']['punctuation_space_normalized_exact'] + summary['overall']['ascii_case_normalized_exact']}",
        "",
        "## unit_style_normalized 后统计",
        "",
        f"- 新增通过: {summary['overall']['unit_style_normalized_exact']}",
        f"- 累计通过: {summary['overall']['strict_exact'] + summary['overall']['punctuation_space_normalized_exact'] + summary['overall']['ascii_case_normalized_exact'] + summary['overall']['unit_style_normalized_exact']}",
        f"- meaningful_text_difference: {summary['overall']['meaningful_text_difference']}",
        f"- severe_failure: {summary['overall']['severe_failure']}",
    ]
    _append_counts_table(lines, "每个 Qwen 组合的分层通过率", [row for row in summary["by_input_method"] if str(row["method"]).startswith(QWEN_PREFIX)])
    _append_counts_table(lines, "与 PaddleOCR 的分层对比", summary["by_input_method"])
    lines.extend([
        "",
        "## 来源聚合对比",
        "",
        "| 来源 | 总数 | strict_exact | punctuation_space | ascii_case | unit_style | meaningful_text_difference | severe_failure | unit_style通过率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for source, item in source_totals.items():
        lines.append(
            f"| {source} | {item['total']} | {item['strict_exact']} | {item['punctuation_space_normalized_exact']} | "
            f"{item['ascii_case_normalized_exact']} | {item['unit_style_normalized_exact']} | "
            f"{item['meaningful_text_difference']} | {item['severe_failure']} | {item['unit_style_pass_rate']:.2%} |"
        )
    lines.extend([
        "",
        "## meaningful_text_difference 剩余 Case",
        "",
        "| case_id | 输入版本 | 方法 | gold | raw_prediction | edit_distance | diff |",
        "|---|---|---|---|---|---:|---|",
    ])
    for row in meaningful:
        lines.append(
            f"| {row['case_id']} | {row['input_version_label']} | {row['method_label']} | "
            f"{_md(row['gold'])} | {_md(row['raw_prediction'])} | {row['edit_distance']} | {_md(row['diff'])} |"
        )
    lines.extend([
        "",
        "## severe_failure 列表",
        "",
        "| case_id | 输入版本 | 方法 | 原始错误类型 | gold | raw_prediction | diff |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in severe:
        lines.append(
            f"| {row['case_id']} | {row['input_version_label']} | {row['method_label']} | {row['original_error_type']} | "
            f"{_md(row['gold'])} | {_md(row['raw_prediction'])} | {_md(row['diff'])} |"
        )
    lines.extend([
        "",
        "## 最推荐的固定输入版本和 prompt",
        "",
    ])
    if best_qwen:
        lines.append(
            f"- 推荐：`{best_qwen['input_version']}` + `{best_qwen['method']}`，"
            f"unit_style 层通过率 {best_qwen['unit_style_pass_rate']:.2%}，"
            f"平均编辑距离 {best_qwen.get('average_edit_distance', 'NA')}，"
            f"meaningful_text_difference {best_qwen['meaningful_text_difference']}，severe_failure {best_qwen['severe_failure']}。"
        )
    else:
        lines.append("- 未找到 Qwen 组合。")
    qwen_total = source_totals.get("Qwen", {})
    lines.extend([
        "",
        "## 结论",
        "",
        f"- Qwen 聚合 unit_style 层通过率：{qwen_total.get('unit_style_pass_rate', 0):.2%}。",
        "- VLM 可以作为“病情观察及处理”的候选文本来源，但不建议直接自动覆盖主结果；仍需人工复核或后续候选策略，因为 meaningful_text_difference 仍包含非格式性字符差异。",
        "- 本报告没有修改 gold、raw_prediction、主 result.json 或 result_enhanced.json。",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(source_summary_json: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_previous_rows(source_summary_json)
    summary = summarize_layered_rows(rows)
    metadata = {
        "source_summary_json": str(source_summary_json),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    report = build_report(rows, summary, metadata)
    report_path = output_dir / "observation_layered_eval_report.md"
    summary_path = output_dir / "observation_layered_eval_summary.json"
    cases_path = output_dir / "observation_layered_eval_cases.jsonl"
    report_path.write_text(report, encoding="utf-8")
    summary_path.write_text(json.dumps({"metadata": metadata, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    cases_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return {"report_path": str(report_path), "summary_path": str(summary_path), "cases_path": str(cases_path), "summary": summary}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recompute layered observation eval from prior experiment summary.")
    parser.add_argument("--source-summary-json", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = write_outputs(Path(args.source_summary_json), Path(args.output_dir))
    print(json.dumps({k: v for k, v in result.items() if k.endswith("_path")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
