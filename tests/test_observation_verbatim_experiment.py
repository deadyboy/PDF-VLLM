import json

from icu_vllm.observation_verbatim_experiment import (
    OBS_FIELD,
    build_verbatim_row,
    build_verbatim_sidecar,
    classify_observation_outcome,
    load_old_col_rows,
    parse_verbatim_response,
    summarize_verbatim_rows,
    write_verbatim_report,
)


def test_parse_verbatim_response_preserves_raw_lines_and_final_text():
    raw = json.dumps(
        {
            "raw_lines": ["患者ECMO应用，机器运转正常", "RASS-4分"],
            "final_text": "患者ECMO应用，机器运转正常RASS-4分",
            "needs_review": False,
            "reason": "",
        },
        ensure_ascii=False,
    )

    raw_lines, final_text, needs_review, reason, error = parse_verbatim_response(raw)

    assert error is None
    assert raw_lines == ["患者ECMO应用，机器运转正常", "RASS-4分"]
    assert final_text == "患者ECMO应用，机器运转正常RASS-4分"
    assert needs_review is False
    assert reason == ""


def test_build_verbatim_sidecar_uses_requested_schema():
    payload = build_verbatim_sidecar(
        block_id="block_03",
        raw_lines=["遵医嘱予碘伏擦浴一次。"],
        final_text="遵医嘱予碘伏擦浴一次。",
        needs_review=False,
        reason="",
        raw_response='{"final_text":"..."}',
        image_path="slices/p/block_03_col_observation.png",
    )

    assert payload["block_id"] == "block_03"
    assert payload["field"] == OBS_FIELD
    assert payload["raw_lines"] == ["遵医嘱予碘伏擦浴一次。"]
    assert payload["final_text"] == "遵医嘱予碘伏擦浴一次。"
    assert payload["needs_review"] is False
    assert payload["_image_path"].endswith("block_03_col_observation.png")


def test_classify_observation_outcome_separates_punctuation_and_rewrite():
    assert classify_observation_outcome("APTT：43.6s，遵医嘱", "APTT:43.6s,遵医嘱") == "canonical_only"
    assert classify_observation_outcome("A;B", "A，B") == "punctuation_only"
    assert classify_observation_outcome("遵医嘱予碘伏擦浴一次", "遵医嘱予碘优擦浴一次") == "rewrite_or_paraphrase"
    assert classify_observation_outcome("CPOT0分", None) == "missing"


def test_summarize_verbatim_rows_counts_three_methods_and_regressions():
    rows = [
        build_verbatim_row(
            page="p",
            block_id="block_00",
            gold="CPOT0分",
            main_value=None,
            old_col_value="CPOT0分",
            verbatim_value="CPOT0分",
            raw_lines=["CPOT0分"],
            needs_review=False,
            reason="",
            image_path="slices/p/block_00_col_observation.png",
        ),
        build_verbatim_row(
            page="p",
            block_id="block_01",
            gold="遵医嘱予碘伏擦浴一次",
            main_value="遵医嘱予碘伏擦浴一次",
            old_col_value="遵医嘱予碘优擦浴一次",
            verbatim_value="遵医嘱予碘优擦浴一次",
            raw_lines=["遵医嘱予碘优擦浴一次"],
            needs_review=True,
            reason="字迹不清",
            image_path="slices/p/block_01_col_observation.png",
        ),
    ]

    summary = summarize_verbatim_rows(rows)

    assert summary["metrics"]["main"]["correct"] == 1
    assert summary["metrics"]["old_col"]["rewrite_or_paraphrase"] == 1
    assert summary["metrics"]["verbatim"]["correct"] == 1
    assert summary["metrics"]["verbatim"]["rewrite_or_paraphrase"] == 1
    assert summary["comparisons"]["main_wrong_verbatim_correct"] == 1
    assert summary["comparisons"]["main_correct_verbatim_wrong"] == 1
    assert summary["comparisons"]["verbatim_needs_review"] == 1


def test_write_verbatim_report_outputs_required_files(tmp_path):
    rows = [
        build_verbatim_row(
            page="p",
            block_id="block_00",
            gold="CPOT0分",
            main_value=None,
            old_col_value="CPOT0分",
            verbatim_value="CPOT0分",
            raw_lines=["CPOT0分"],
            needs_review=False,
            reason="",
            image_path="slices/p/block_00_col_observation.png",
        )
    ]
    summary = summarize_verbatim_rows(rows)
    sidecars = {"p": [{"block_id": "block_00", "final_text": "CPOT0分"}]}

    write_verbatim_report(tmp_path, rows, summary, sidecars, metadata={"model_calls": 1})

    assert (tmp_path / "observation_verbatim_sidecars" / "p" / "block_00_observation_verbatim_v2.json").exists()
    report = (tmp_path / "observation_verbatim_report.md").read_text(encoding="utf-8")
    assert "| p | block_00 |" in report
    assert "| correct | 0 | 1 | 1 |" in report
    payload = json.loads((tmp_path / "observation_verbatim_summary.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_calls"] == 1
    assert payload["rows"][0]["verbatim_value"] == "CPOT0分"


def test_load_old_col_rows_prefers_observation_direct_sidecars(tmp_path):
    source_run = tmp_path / "target"
    direct_run = tmp_path / "direct"
    (source_run / "sidecars" / "p").mkdir(parents=True)
    (direct_run / "sidecars" / "p").mkdir(parents=True)
    (source_run / "sidecars" / "p" / "block_00_col_vlm.json").write_text(
        json.dumps({"block_id": "block_00", OBS_FIELD: None}, ensure_ascii=False),
        encoding="utf-8",
    )
    (direct_run / "sidecars" / "p" / "block_00_observation_direct_v2.json").write_text(
        json.dumps({"block_id": "block_00", OBS_FIELD: "CPOT0分"}, ensure_ascii=False),
        encoding="utf-8",
    )

    rows = load_old_col_rows("p", source_run, direct_run)

    assert rows == [{"block_id": "block_00", OBS_FIELD: "CPOT0分"}]
