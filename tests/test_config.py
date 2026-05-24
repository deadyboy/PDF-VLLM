from pathlib import Path

from icu_vllm.config import load_config, prepare_run_dirs


def test_default_config_only_uses_old_project_as_input():
    cfg = load_config(Path("config/default.toml"))

    assert cfg.input_dir.as_posix() == "/data1/jianf/新提取pdf/180data"
    assert cfg.workspace == Path("/data1/jianf-vllm")
    assert cfg.vllm_base_url == "http://localhost:8002/v1"

    old_project = "/data1/jianf/新提取pdf"
    assert old_project not in str(cfg.runs_dir)
    assert old_project not in str(cfg.log_base)
    assert old_project not in str(cfg.patient_cache_dir)
    assert cfg.mm_processor_kwargs == {}
    assert cfg.keep_success_m_evidence is False


def test_config_loads_optional_mm_processor_kwargs(tmp_path):
    config_path = tmp_path / "qwen3.toml"
    config_path.write_text(
        """
[paths]
workspace = "/data1/jianf-vllm"
input_dir = "/data1/jianf/新提取pdf/180data"
runs_dir = "/data1/jianf-vllm/runs"
ocr_python = "/home/jianf/miniconda3/envs/ocr_legacy/bin/python"

[pipeline]
profile = "jin"
keep_success_m_evidence = true

[vllm]
base_url = "http://localhost:8005/v1"
api_key = "EMPTY"
model_name = "qwen3vl-8b"
timeout_seconds = 300

[concurrency]
max_concurrent_llm = 32
max_concurrent_cut = 8
max_concurrent_img = 3

[mm_processor]
min_pixels = 200704
max_pixels = 1003520
""",
        encoding="utf-8",
    )

    cfg = load_config(config_path)

    assert cfg.keep_success_m_evidence is True
    assert cfg.mm_processor_kwargs == {
        "min_pixels": 200704,
        "max_pixels": 1003520,
    }


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


def test_qwen3_benchmark_configs_are_isolated():
    cfg_8b = load_config(Path("config/benchmark_qwen3_8b.toml"))
    cfg_8b_low = load_config(Path("config/benchmark_qwen3_8b_low_pixels.toml"))
    cfg_8b_high = load_config(Path("config/benchmark_qwen3_8b_high_pixels.toml"))
    cfg_32b = load_config(Path("config/benchmark_qwen3_32b.toml"))

    assert cfg_8b.vllm_base_url == "http://localhost:8005/v1"
    assert cfg_8b.model_name == "qwen3vl-8b"
    assert cfg_32b.vllm_base_url == "http://localhost:8006/v1"
    assert cfg_32b.model_name == "qwen3vl-32b"
    assert cfg_8b_low.mm_processor_kwargs == {"max_pixels": 602112}
    assert cfg_8b_high.mm_processor_kwargs == {"max_pixels": 1605632}
    assert all(
        cfg.runs_dir == Path("/data1/jianf-vllm/runs")
        for cfg in [cfg_8b, cfg_8b_low, cfg_8b_high, cfg_32b]
    )
