from pathlib import Path
from types import SimpleNamespace

from icu_vllm.config import load_config, prepare_run_dirs
from icu_vllm.pipeline import ExtractionPipeline, select_input_images


def test_select_input_images_uses_samples_in_given_order(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    first = input_dir / "b.png"
    second = input_dir / "a.png"
    first.write_bytes(b"png")
    second.write_bytes(b"png")
    (input_dir / "c.png").write_bytes(b"png")

    assert select_input_images(input_dir, sample_names=["b.png", "a.png"]) == [first, second]


def test_select_input_images_rejects_missing_sample(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    try:
        select_input_images(input_dir, sample_names=["missing.png"])
    except FileNotFoundError as exc:
        assert "missing.png" in str(exc)
    else:
        raise AssertionError("missing sample should fail before launching a benchmark")


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


def test_extract_single_part_passes_mm_processor_kwargs(tmp_path):
    cfg = load_config(Path("config/default.toml"))
    cfg.workspace = tmp_path
    cfg.runs_dir = tmp_path / "runs"
    cfg.mm_processor_kwargs = {"max_pixels": 1003520}
    run_dirs = prepare_run_dirs(cfg, "unit")
    pipeline = ExtractionPipeline(cfg, run_dirs)
    image_path = tmp_path / "slice.png"
    image_path.write_bytes(b"png")
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"体温": "36.5"}'))]
            )

    pipeline.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    data = __import__("asyncio").run(pipeline.extract_single_part(image_path, "prompt"))

    assert data == {"体温": "36.5"}
    assert captured["extra_body"] == {"mm_processor_kwargs": {"max_pixels": 1003520}}
