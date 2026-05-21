from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .config import load_config


@dataclass(frozen=True)
class InspectReport:
    input_count: int
    result_count: int
    missing_result_count: int
    extra_result_count: int
    bad_json_count: int
    excel_count: int


def inspect_run(run_dir: Path, input_dir: Path) -> InspectReport:
    results_dir = run_dir / "results_json"
    excel_dir = run_dir / "excel"
    input_stems = {
        p.stem
        for pattern in ("*.png", "*.jpg", "*.jpeg")
        for p in input_dir.glob(pattern)
    }
    result_files = list(results_dir.glob("*_result.json"))
    result_stems = {p.name[:-12] for p in result_files}
    bad_json = 0
    for path in result_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            bad_json += 1
    return InspectReport(
        input_count=len(input_stems),
        result_count=len(result_files),
        missing_result_count=len(input_stems - result_stems),
        extra_result_count=len(result_stems - input_stems),
        bad_json_count=bad_json,
        excel_count=len(list(excel_dir.glob("*.xlsx"))),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a vLLM extraction run")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--config", default="config/default.toml")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    report = inspect_run(Path(args.run_dir), cfg.input_dir)
    print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))
    return 0 if report.bad_json_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
