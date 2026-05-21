from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .config import load_config, prepare_run_dirs
from .pipeline import ExtractionPipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a clean vLLM extraction batch")
    parser.add_argument("--config", default="config/default.toml")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--patient-id", help="Optional patient prefix for smoke or focused reruns")
    parser.add_argument("--limit", type=int, help="Optional image limit for smoke testing")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    run_dir = cfg.runs_dir / args.run_id
    if run_dir.exists() and not args.resume and any(run_dir.iterdir()):
        raise SystemExit(f"Run directory already exists and is not empty: {run_dir}. Use --resume or a new --run-id.")

    run_dirs = prepare_run_dirs(cfg, args.run_id)
    pipeline = ExtractionPipeline(cfg, run_dirs, resume=args.resume)
    manifest = asyncio.run(pipeline.batch_process_parallel(patient_id=args.patient_id, limit=args.limit))
    print(
        "run_id={run_id} image_count={image_count} success={success} skipped={skipped} failed={failed}".format(
            **manifest
        )
    )
    print(f"manifest={run_dirs.manifest_path}")
    return 0 if manifest["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
