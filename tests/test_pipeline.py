from pathlib import Path

from icu_vllm.config import load_config, prepare_run_dirs
from icu_vllm.pipeline import ExtractionPipeline


def test_cutter_runs_as_module_to_avoid_stdlib_inspect_shadow(tmp_path, monkeypatch):
    cfg = load_config(Path("config/default.toml"))
    cfg.workspace = tmp_path
    cfg.runs_dir = tmp_path / "runs"
    run_dirs = prepare_run_dirs(cfg, "unit")
    pipeline = ExtractionPipeline(cfg, run_dirs)
    calls = {}

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(args, env, capture_output, text, cwd):
        calls["args"] = args
        calls["env"] = env
        calls["cwd"] = cwd
        out_dir = Path(args[-1])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "block_00_L.png").write_bytes(b"png")
        return Result()

    monkeypatch.setattr("icu_vllm.pipeline.subprocess.run", fake_run)

    pipeline.call_paddle_env_to_cut(tmp_path / "input.png", tmp_path / "slices")

    assert calls["args"][1:3] == ["-m", "icu_vllm.cutter_worker_jin"]
    assert calls["cwd"] == Path(__file__).resolve().parents[1]
    assert str(calls["cwd"]) in calls["env"]["PYTHONPATH"].split(__import__("os").pathsep)
