from pathlib import Path
from types import SimpleNamespace
import json

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


def test_extract_single_part_can_save_raw_response_without_changing_parse(tmp_path):
    cfg = load_config(Path("config/default.toml"))
    cfg.workspace = tmp_path
    cfg.runs_dir = tmp_path / "runs"
    run_dirs = prepare_run_dirs(cfg, "unit")
    pipeline = ExtractionPipeline(cfg, run_dirs)
    image_path = tmp_path / "slice.png"
    image_path.write_bytes(b"png")
    raw_path = tmp_path / "slice.raw_response.txt"

    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='前缀 {"入量_静脉用药": "20"} 后缀'))]
            )

    pipeline.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    data = __import__("asyncio").run(
        pipeline.extract_single_part(image_path, "prompt", raw_output_path=raw_path)
    )

    assert data == {"入量_静脉用药": "20"}
    assert raw_path.read_text(encoding="utf-8") == '前缀 {"入量_静脉用药": "20"} 后缀'


def test_process_columns_batch_keeps_only_success_m_evidence_when_enabled(tmp_path, monkeypatch):
    cfg = load_config(Path("config/default.toml"))
    cfg.workspace = tmp_path
    cfg.runs_dir = tmp_path / "runs"
    cfg.keep_success_m_evidence = True
    run_dirs = prepare_run_dirs(cfg, "unit")
    pipeline = ExtractionPipeline(cfg, run_dirs)
    slice_dir = tmp_path / "slices"
    slice_dir.mkdir()
    for suffix in ("L", "M", "R"):
        (slice_dir / f"block_00_{suffix}.png").write_bytes(f"png-{suffix}".encode())
    (slice_dir / "block_00_M.txt").write_text("ocr text", encoding="utf-8")
    (slice_dir / "block_00_M.ocr.json").write_text(
        json.dumps({"image": "block_00_M.png", "part": "M", "ocr_items": []}),
        encoding="utf-8",
    )
    raw_paths = []

    async def fake_extract(img_path, prompt_text, retries=5, raw_output_path=None):
        if raw_output_path is not None:
            raw_paths.append(raw_output_path)
            raw_output_path.write_text(f"raw for {img_path.name}", encoding="utf-8")
        return {f"field_{img_path.stem[-1]}": img_path.name}

    monkeypatch.setattr(pipeline, "extract_single_part", fake_extract)

    output_json = run_dirs.results_json_dir / "0010016667_2025_4_25_1_result.json"
    __import__("asyncio").run(
        pipeline.process_columns_batch(slice_dir, output_json, "0010016667_2025_4_25_1.png")
    )

    assert [path.name for path in raw_paths] == ["block_00_M.raw_response.txt"]
    data = json.loads(output_json.read_text(encoding="utf-8"))
    assert data == [{
        "field_L": "block_00_L.png",
        "field_M": "block_00_M.png",
        "field_R": "block_00_R.png",
        "_block_id": "block_00",
        "_profile": "jin",
    }]
    evidence_dir = run_dirs.run_dir / "debug" / "m_evidence" / "0010016667_2025_4_25_1"
    assert sorted(path.name for path in evidence_dir.iterdir()) == [
        "block_00_M.ocr.json",
        "block_00_M.png",
        "block_00_M.raw_response.txt",
        "block_00_M.txt",
    ]
    assert (evidence_dir / "block_00_M.raw_response.txt").read_text(encoding="utf-8") == "raw for block_00_M.png"


def test_process_columns_batch_does_not_keep_m_evidence_by_default(tmp_path, monkeypatch):
    cfg = load_config(Path("config/default.toml"))
    cfg.workspace = tmp_path
    cfg.runs_dir = tmp_path / "runs"
    run_dirs = prepare_run_dirs(cfg, "unit")
    pipeline = ExtractionPipeline(cfg, run_dirs)
    slice_dir = tmp_path / "slices"
    slice_dir.mkdir()
    for suffix in ("L", "M", "R"):
        (slice_dir / f"block_00_{suffix}.png").write_bytes(f"png-{suffix}".encode())
    raw_paths = []

    async def fake_extract(img_path, prompt_text, retries=5, raw_output_path=None):
        if raw_output_path is not None:
            raw_paths.append(raw_output_path)
        return {f"field_{img_path.stem[-1]}": img_path.name}

    monkeypatch.setattr(pipeline, "extract_single_part", fake_extract)

    output_json = run_dirs.results_json_dir / "0010016667_2025_4_25_1_result.json"
    __import__("asyncio").run(
        pipeline.process_columns_batch(slice_dir, output_json, "0010016667_2025_4_25_1.png")
    )

    assert raw_paths == []
    assert not (run_dirs.run_dir / "debug").exists()
