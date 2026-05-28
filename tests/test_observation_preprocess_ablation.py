import json

from icu_vllm.observation_preprocess_ablation import (
    OBS_FIELD,
    VARIANTS,
    _variant_image_path,
    build_ablation_row,
    build_variant_sidecar,
    parse_observation_response,
    summarize_ablation_rows,
    write_ablation_report,
)


def test_parse_observation_response_reads_same_observation_prompt_schema():
    raw = json.dumps({OBS_FIELD: "APTT:43.6s,遵医嘱"}, ensure_ascii=False)

    value, error = parse_observation_response(raw)

    assert value == "APTT:43.6s,遵医嘱"
    assert error is None


def test_build_variant_sidecar_records_variant_image_and_raw_response():
    sidecar = build_variant_sidecar(
        block_id="block_04",
        variant="clean_2x",
        value="RASS-4分",
        raw_response='{"病情观察及处理":"RASS-4分"}',
        image_path="preprocessed/gold/block_04_obs_clean_2x.png",
    )

    assert sidecar["block_id"] == "block_04"
    assert sidecar["variant"] == "clean_2x"
    assert sidecar[OBS_FIELD] == "RASS-4分"
    assert sidecar["_image_path"].endswith("block_04_obs_clean_2x.png")


def test_summarize_ablation_rows_maps_refined_eval_to_requested_metrics():
    rows = [
        build_ablation_row(
            page="p",
            block_id="block_00",
            gold="CPOT0分",
            main_value=None,
            variant="raw_col",
            variant_value="CPOT0分",
        ),
        build_ablation_row(
            page="p",
            block_id="block_01",
            gold="A;B",
            main_value="A，B",
            variant="raw_col",
            variant_value="A，B",
        ),
        build_ablation_row(
            page="p",
            block_id="block_02",
            gold="RASS-4分",
            main_value="RASS-4分",
            variant="clean_2x",
            variant_value="RASS-3分",
        ),
    ]

    summary = summarize_ablation_rows(rows)

    assert summary["variants"]["raw_col"]["correct"] == 1
    assert summary["variants"]["raw_col"]["punctuation_only"] == 1
    assert summary["variants"]["clean_2x"]["char_level_mismatch"] == 1
    assert set(summary["variants"]).issubset(set(VARIANTS))


def test_write_ablation_report_outputs_sidecars_report_and_summary(tmp_path):
    rows = [
        build_ablation_row(
            page="p",
            block_id="block_00",
            gold="CPOT0分",
            main_value=None,
            variant="raw_col",
            variant_value="CPOT0分",
        )
    ]
    summary = summarize_ablation_rows(rows)
    sidecars = {"raw_col": {"p": [build_variant_sidecar("block_00", "raw_col", "CPOT0分", "{}", "img.png")]}}

    write_ablation_report(tmp_path, rows, summary, sidecars, metadata={"model_calls": 0})

    assert (tmp_path / "observation_preprocess_sidecars" / "raw_col" / "p" / "block_00_obs_raw_col.json").exists()
    report = (tmp_path / "observation_preprocess_ablation_report.md").read_text(encoding="utf-8")
    assert "| raw_col | 1 |" in report
    payload = json.loads((tmp_path / "observation_preprocess_ablation_summary.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_calls"] == 0
    assert payload["summary"]["variants"]["raw_col"]["correct"] == 1


def test_variant_image_path_uses_single_page_segment(tmp_path):
    path = _variant_image_path(tmp_path / "observation_preprocess_images", "gold", "block_00", "clean_2x")

    assert path == tmp_path / "observation_preprocess_images" / "gold" / "block_00_obs_clean_2x.png"
