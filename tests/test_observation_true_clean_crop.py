import json

from icu_vllm.observation_true_clean_crop import (
    REPORT_VARIANTS,
    TRUE_CLEAN_VARIANTS,
    build_true_clean_manifest,
    build_true_clean_row,
    summarize_true_clean_rows,
    summarize_true_clean_sanity,
    true_clean_image_name,
    write_true_clean_report,
)


def test_true_clean_variants_and_image_names_are_explicit():
    assert TRUE_CLEAN_VARIANTS == (
        "obs_true_clean_native",
        "obs_true_clean_2x",
        "obs_true_clean_3x",
    )
    assert "raw_col" in REPORT_VARIANTS
    assert true_clean_image_name("block_04", "obs_true_clean_2x") == "block_04_obs_true_clean_2x.png"


def test_build_true_clean_manifest_records_source_stage_and_variant_sizes():
    manifest = build_true_clean_manifest(
        source_image="/data/input/page.png",
        page="gold_smoke_001",
        block_id="block_00",
        final_block_shape=(100, 200),
        crop_box=(150, 190, 0, 100),
        padding=12,
        native_size=(100, 40),
        variants={
            "obs_true_clean_native": {
                "path": "block_00_obs_true_clean_native.png",
                "size_before": (100, 40),
                "size_after": (100, 40),
                "used_optimize": False,
            },
            "obs_true_clean_2x": {
                "path": "block_00_obs_true_clean_2x.png",
                "size_before": (200, 80),
                "size_after": (200, 80),
                "used_optimize": False,
            },
            "obs_true_clean_3x": {
                "path": "block_00_obs_true_clean_3x.png",
                "size_before": (300, 120),
                "size_after": (300, 120),
                "used_optimize": False,
            },
        },
    )

    assert manifest["source_stage"] == "clean_final_block_before_redline_before_optimize"
    assert manifest["final_block_shape"] == [100, 200]
    assert manifest["crop_x1"] == 150
    assert manifest["native_size"] == [100, 40]
    assert manifest["variant_size_before_llm_optimize"] == [100, 40]
    assert manifest["used_optimize_image_for_llm"] is False
    assert manifest["variants"]["obs_true_clean_2x"]["variant_size_before_llm_optimize"] == [200, 80]
    assert manifest["variants"]["obs_true_clean_3x"]["was_downscaled_before_model"] is False


def test_summarize_true_clean_sanity_checks_ratios_stage_and_downscale():
    manifests = [
        build_true_clean_manifest(
            source_image="/x.png",
            page="p",
            block_id="block_00",
            final_block_shape=(100, 200),
            crop_box=(0, 20, 0, 100),
            padding=0,
            native_size=(100, 20),
            variants={
                "obs_true_clean_native": {"path": "n.png", "size_before": (100, 20), "size_after": (100, 20), "used_optimize": False},
                "obs_true_clean_2x": {"path": "2.png", "size_before": (200, 40), "size_after": (200, 40), "used_optimize": False},
                "obs_true_clean_3x": {"path": "3.png", "size_before": (300, 60), "size_after": (300, 60), "used_optimize": False},
            },
        )
    ]

    sanity = summarize_true_clean_sanity(manifests)

    assert sanity["total_manifests"] == 1
    assert sanity["two_x_size_ok"] == 1
    assert sanity["three_x_size_ok"] == 1
    assert sanity["source_stage_ok"] == 1
    assert sanity["downscaled_before_model"] == 0


def test_build_row_and_summary_compare_raw_col_with_true_clean_variants():
    row = build_true_clean_row(
        page="p",
        block_id="block_00",
        gold="CPOT0分",
        main_value="CFO10分",
        raw_col_value="CFO10分",
        true_clean_values={
            "obs_true_clean_native": "CFO10分",
            "obs_true_clean_2x": "CPOT0分",
            "obs_true_clean_3x": "CPOT0分",
        },
    )

    summary = summarize_true_clean_rows([row])

    assert row["raw_col_eval_kind"] == "char_level_mismatch"
    assert row["obs_true_clean_2x_eval_kind"] == "exact_equal"
    assert summary["variants"]["raw_col"]["char_level_mismatch"] == 1
    assert summary["variants"]["obs_true_clean_2x"]["correct"] == 1
    assert summary["variants"]["obs_true_clean_3x"]["correct"] == 1


def test_write_true_clean_report_outputs_required_files(tmp_path):
    row = build_true_clean_row(
        page="p",
        block_id="block_00",
        gold="CPOT0分",
        main_value="CFO10分",
        raw_col_value="CFO10分",
        true_clean_values={
            "obs_true_clean_native": "CFO10分",
            "obs_true_clean_2x": "CPOT0分",
            "obs_true_clean_3x": "CPOT0分",
        },
    )
    summary = summarize_true_clean_rows([row])
    sanity = {"total_manifests": 1, "two_x_size_ok": 1, "three_x_size_ok": 1, "source_stage_ok": 1, "downscaled_before_model": 0}

    write_true_clean_report(tmp_path, [row], summary, sanity, metadata={"model_calls": 3})

    report = (tmp_path / "observation_true_clean_crop_report.md").read_text(encoding="utf-8")
    assert "clean_final_block_before_redline_before_optimize" in report
    assert "| obs_true_clean_2x | 1 |" in report
    payload = json.loads((tmp_path / "observation_true_clean_crop_summary.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_calls"] == 3
    assert payload["sanity"]["two_x_size_ok"] == 1
