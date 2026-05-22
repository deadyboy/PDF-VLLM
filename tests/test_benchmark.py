import json
from pathlib import Path

from icu_vllm.benchmark import summarize_run


def test_summarize_run_counts_bad_json_and_timings(tmp_path):
    run_dir = tmp_path / "run"
    results_dir = run_dir / "results_json"
    results_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({
            "run_id": "bench-test",
            "image_count": 2,
            "success": 2,
            "failed": 0,
            "elapsed_seconds": 12.5,
            "image_timings_seconds": {"a.png": 4.0, "b.png": 8.5},
        }),
        encoding="utf-8",
    )
    (results_dir / "a_result.json").write_text(json.dumps([{"x": 1}]), encoding="utf-8")
    (results_dir / "b_result.json").write_text(json.dumps([{"_error": "bad"}]), encoding="utf-8")

    summary = summarize_run(run_dir)

    assert summary["run_id"] == "bench-test"
    assert summary["json_files"] == 2
    assert summary["bad_json_objects"] == 1
    assert summary["avg_image_seconds"] == 6.25
