from pathlib import Path

from icu_vllm.config import load_config, prepare_run_dirs


def test_default_config_only_uses_old_project_as_input():
    cfg = load_config(Path("config/default.toml"))

    assert cfg.input_dir.as_posix() == "/data1/jianf/新提取pdf/180data"
    assert cfg.workspace == Path("/data1/jianf-vllm")

    old_project = "/data1/jianf/新提取pdf"
    assert old_project not in str(cfg.runs_dir)
    assert old_project not in str(cfg.log_base)
    assert old_project not in str(cfg.patient_cache_dir)


def test_prepare_run_dirs_creates_isolated_output_paths(tmp_path):
    cfg = load_config(Path("config/default.toml"))
    cfg.workspace = tmp_path
    cfg.runs_dir = tmp_path / "runs"

    run = prepare_run_dirs(cfg, "20260521-test")

    assert run.run_dir == tmp_path / "runs" / "20260521-test"
    assert run.results_json_dir == run.run_dir / "results_json"
    assert run.patient_cache_dir == run.run_dir / "patient_cache"
    assert run.excel_dir == run.run_dir / "excel"
    assert run.logs_dir == run.run_dir / "logs"
    assert run.failed_debug_dir == run.run_dir / "failed_debug_images"
    assert run.manifest_path == run.run_dir / "manifest.json"
    assert all(p.exists() for p in [
        run.results_json_dir,
        run.patient_cache_dir,
        run.excel_dir,
        run.logs_dir,
        run.failed_debug_dir,
    ])
