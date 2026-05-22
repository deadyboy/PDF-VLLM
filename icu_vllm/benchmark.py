from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


SUMMARY_FIELDS = [
    "run_id",
    "profile",
    "model_name",
    "vllm_base_url",
    "image_count",
    "success",
    "failed",
    "skipped",
    "elapsed_seconds",
    "avg_image_seconds",
    "json_files",
    "result_objects",
    "bad_json_objects",
    "run_dir",
]


def _count_bad_objects(value: Any) -> tuple[int, int]:
    if isinstance(value, list):
        objects = [item for item in value if isinstance(item, dict)]
        return len(objects), sum(1 for item in objects if "_error" in item)
    if isinstance(value, dict):
        return 1, 1 if "_error" in value else 0
    return 0, 1


def summarize_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results_dir = run_dir / "results_json"
    json_files = sorted(results_dir.glob("*.json")) if results_dir.exists() else []

    result_objects = 0
    bad_json_objects = 0
    for path in json_files:
        try:
            object_count, error_count = _count_bad_objects(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            object_count, error_count = 0, 1
        result_objects += object_count
        bad_json_objects += error_count

    timings = manifest.get("image_timings_seconds") or {}
    avg_image_seconds = 0.0
    if timings:
        avg_image_seconds = round(sum(float(v) for v in timings.values()) / len(timings), 3)
    elif manifest.get("image_count"):
        avg_image_seconds = round(float(manifest.get("elapsed_seconds", 0)) / int(manifest["image_count"]), 3)

    return {
        "run_id": manifest.get("run_id", run_dir.name),
        "profile": manifest.get("profile", ""),
        "model_name": manifest.get("model_name", ""),
        "vllm_base_url": manifest.get("vllm_base_url", ""),
        "image_count": int(manifest.get("image_count", 0)),
        "success": int(manifest.get("success", 0)),
        "failed": int(manifest.get("failed", 0)),
        "skipped": int(manifest.get("skipped", 0)),
        "elapsed_seconds": float(manifest.get("elapsed_seconds", 0)),
        "avg_image_seconds": avg_image_seconds,
        "json_files": len(json_files),
        "result_objects": result_objects,
        "bad_json_objects": bad_json_objects,
        "run_dir": str(run_dir),
    }


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize benchmark run directories")
    parser.add_argument("--run-dir", action="append", required=True, help="Run directory to summarize")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-json")
    args = parser.parse_args(argv)

    rows = [summarize_run(Path(path)) for path in args.run_dir]
    write_csv(rows, Path(args.output_csv))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
