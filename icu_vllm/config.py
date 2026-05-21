from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PipelineConfig:
    workspace: Path
    input_dir: Path
    runs_dir: Path
    ocr_python: Path
    vllm_base_url: str
    vllm_api_key: str
    model_name: str
    timeout_seconds: float
    max_concurrent_llm: int
    max_concurrent_cut: int
    max_concurrent_img: int

    @property
    def log_base(self) -> Path:
        return self.runs_dir

    @property
    def patient_cache_dir(self) -> Path:
        return self.runs_dir / "_no_global_patient_cache"


@dataclass(frozen=True)
class RunDirs:
    run_id: str
    run_dir: Path
    results_json_dir: Path
    patient_cache_dir: Path
    excel_dir: Path
    logs_dir: Path
    failed_debug_dir: Path
    manifest_path: Path


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def _load_toml(path: Path) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    section: dict[str, Any] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = data.setdefault(line[1:-1], {})
            continue
        if section is None or "=" not in line:
            raise ValueError(f"Invalid TOML line in {path}: {raw_line}")
        key, value = line.split("=", 1)
        section[key.strip()] = _parse_scalar(value)
    return data


def load_config(path: Path) -> PipelineConfig:
    data = _load_toml(path)
    paths = data["paths"]
    vllm = data["vllm"]
    concurrency = data["concurrency"]

    return PipelineConfig(
        workspace=Path(paths["workspace"]),
        input_dir=Path(paths["input_dir"]),
        runs_dir=Path(paths["runs_dir"]),
        ocr_python=Path(paths["ocr_python"]),
        vllm_base_url=str(vllm["base_url"]),
        vllm_api_key=str(vllm["api_key"]),
        model_name=str(vllm["model_name"]),
        timeout_seconds=float(vllm["timeout_seconds"]),
        max_concurrent_llm=int(concurrency["max_concurrent_llm"]),
        max_concurrent_cut=int(concurrency["max_concurrent_cut"]),
        max_concurrent_img=int(concurrency["max_concurrent_img"]),
    )


def prepare_run_dirs(cfg: PipelineConfig, run_id: str) -> RunDirs:
    run_dir = cfg.runs_dir / run_id
    dirs = RunDirs(
        run_id=run_id,
        run_dir=run_dir,
        results_json_dir=run_dir / "results_json",
        patient_cache_dir=run_dir / "patient_cache",
        excel_dir=run_dir / "excel",
        logs_dir=run_dir / "logs",
        failed_debug_dir=run_dir / "failed_debug_images",
        manifest_path=run_dir / "manifest.json",
    )
    for path in [
        dirs.results_json_dir,
        dirs.patient_cache_dir,
        dirs.excel_dir,
        dirs.logs_dir,
        dirs.failed_debug_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    return dirs
