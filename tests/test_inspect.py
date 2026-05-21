import json

from icu_vllm.inspect import inspect_run


def test_inspect_run_counts_inputs_results_and_bad_json(tmp_path):
    input_dir = tmp_path / "input"
    run_dir = tmp_path / "runs" / "run1"
    results_dir = run_dir / "results_json"
    excel_dir = run_dir / "excel"
    input_dir.mkdir()
    results_dir.mkdir(parents=True)
    excel_dir.mkdir(parents=True)

    (input_dir / "001_2025_1_1_1.png").write_bytes(b"png")
    (input_dir / "002_2025_1_1_1.png").write_bytes(b"png")
    (results_dir / "001_2025_1_1_1_result.json").write_text(
        json.dumps([{"_block_id": "block_00"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (results_dir / "bad_result.json").write_text("{broken", encoding="utf-8")
    (excel_dir / "0000000001_护理记录单.xlsx").write_bytes(b"xlsx")

    report = inspect_run(run_dir, input_dir)

    assert report.input_count == 2
    assert report.result_count == 2
    assert report.missing_result_count == 1
    assert report.bad_json_count == 1
    assert report.excel_count == 1
