import json

from icu_vllm.target_column_observation_compare import (
    OBS_FIELD,
    build_observation_row,
    build_rawlines_sidecar,
    observation_text_metrics,
    summarize_observation_rows,
    write_observation_report,
)


def test_build_rawlines_sidecar_preserves_final_and_raw_lines():
    payload = build_rawlines_sidecar(
        block_id="block_04",
        raw_lines=["患者ECMO持续应用，机器运转正常，", "RASS-4分"],
        final_value="患者ECMO持续应用，机器运转正常，RASS-4分",
        needs_review=False,
        reason="",
        raw_response='{"raw_lines":["..."],"final_value":"..."}',
        image_path="block_04_col_observation.png",
    )

    assert payload["block_id"] == "block_04"
    assert payload["field"] == OBS_FIELD
    assert payload["raw_lines"] == ["患者ECMO持续应用，机器运转正常，", "RASS-4分"]
    assert payload["final_value"] == "患者ECMO持续应用，机器运转正常，RASS-4分"
    assert payload["needs_review"] is False
    assert payload["_image_path"] == "block_04_col_observation.png"


def test_observation_text_metrics_reports_distance_and_numeric_diff():
    metrics = observation_text_metrics(
        "APTT:63.3，RASS-4分，CPOT0分",
        "APTT:63.3，RASS-3分，CPOT0分",
    )

    assert metrics["strict_equal"] is False
    assert metrics["canonical_equal"] is False
    assert metrics["edit_distance"] == 1
    assert metrics["gold_len"] > 0
    assert metrics["actual_len"] > 0
    assert "4" in metrics["numeric_token_diff"]
    assert "3" in metrics["numeric_token_diff"]


def test_build_observation_row_includes_all_method_evals_and_metrics():
    row = build_observation_row(
        page="gold_smoke_001",
        block_id="block_00",
        gold="患者ECMO持续应用，RASS-4分",
        main_actual="患者ECMO持续应用，RASS-4分",
        old_col="患者ECMO持续应用，RASS-4分",
        direct_v2="患者ECMO持续应用，RASS-4分",
        rawlines_final="患者ECMO持续应用，RASS-3分",
        rawlines=["患者ECMO持续应用，", "RASS-3分"],
        rawlines_needs_review=False,
        rawlines_reason="",
    )

    assert row["main_eval"] == "equal"
    assert row["old_col_eval"] == "equal"
    assert row["direct_v2_eval"] == "equal"
    assert row["rawlines_eval"] == "substantive_mismatch"
    assert row["rawlines_metrics"]["edit_distance"] == 1
    assert row["rawlines"] == ["患者ECMO持续应用，", "RASS-3分"]


def test_summarize_observation_rows_counts_methods():
    rows = [
        build_observation_row(
            page="p",
            block_id="block_00",
            gold="A1",
            main_actual="A",
            old_col="A",
            direct_v2="A1",
            rawlines_final="A1",
            rawlines=["A1"],
            rawlines_needs_review=False,
            rawlines_reason="",
        ),
        build_observation_row(
            page="p",
            block_id="block_01",
            gold="B2",
            main_actual="B2",
            old_col="B2",
            direct_v2=None,
            rawlines_final="B3",
            rawlines=["B3"],
            rawlines_needs_review=False,
            rawlines_reason="",
        ),
    ]

    summary = summarize_observation_rows(rows)

    assert summary["main_actual"]["canonical_correct"] == 1
    assert summary["old_col"]["canonical_correct"] == 1
    assert summary["direct_v2"]["canonical_correct"] == 1
    assert summary["rawlines_final"]["canonical_correct"] == 1
    assert summary["direct_v2"]["main_wrong_method_correct"] == 1
    assert summary["direct_v2"]["main_correct_method_wrong"] == 1
    assert summary["direct_v2"]["missing"] == 1
    assert summary["rawlines_final"]["avg_normalized_edit_distance"] > 0


def test_write_observation_report_outputs_expected_files(tmp_path):
    rows = [
        build_observation_row(
            page="gold_smoke_001",
            block_id="block_00",
            gold="A1",
            main_actual="A",
            old_col="A",
            direct_v2="A1",
            rawlines_final="A1",
            rawlines=["A1"],
            rawlines_needs_review=False,
            rawlines_reason="",
        )
    ]
    summary = summarize_observation_rows(rows)

    write_observation_report(tmp_path, rows, summary, metadata={"run": "unit"})

    report = (tmp_path / "observation_direct_vs_rawlines_report.md").read_text(encoding="utf-8")
    assert "| gold_smoke_001 | block_00 |" in report
    data = json.loads((tmp_path / "observation_direct_vs_rawlines_summary.json").read_text(encoding="utf-8"))
    assert data["metadata"]["run"] == "unit"
    assert data["summary"]["direct_v2"]["main_wrong_method_correct"] == 1
