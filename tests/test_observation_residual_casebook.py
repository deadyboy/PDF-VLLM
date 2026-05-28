import json

from icu_vllm.observation_residual_casebook import (
    OBS_FIELD,
    build_observation_case,
    build_observation_cases_for_page,
    summarize_cases,
    suggest_error_type,
    write_casebook,
)


def test_suggest_error_type_prefers_column_when_column_corrects_main():
    assert (
        suggest_error_type(
            gold="患者RASS-4分，CPOT0分",
            main_value="患者RASS-3分，CPOT0分",
            col_value="患者RASS-4分，CPOT0分",
            main_eval_kind="substantive_mismatch",
            col_eval_kind="equal",
        )
        == "col_better_than_main"
    )


def test_suggest_error_type_marks_main_better_and_canonical_only():
    assert (
        suggest_error_type(
            gold="患者APTT：63.3，RASS-4分",
            main_value="患者APTT:63.3,RASS-4分",
            col_value="患者APTT:63.3,RASS-4分",
            main_eval_kind="canonical_equal",
            col_eval_kind="canonical_equal",
        )
        == "canonical_only"
    )
    assert (
        suggest_error_type(
            gold="患者ECMO持续应用",
            main_value="患者ECMO持续应用",
            col_value="患者ECMO",
            main_eval_kind="equal",
            col_eval_kind="substantive_mismatch",
        )
        == "main_better_than_col"
    )


def test_build_observation_case_includes_norms_images_and_empty_human_fields():
    case = build_observation_case(
        page="gold_smoke_001",
        block_id="block_04",
        gold="患者RASS-4分，CPOT0分",
        main_value="患者RASS-3分，CPOT0分",
        col_value="患者RASS-4分，CPOT0分",
        r_slice="slices/gold_smoke_001/block_04_R.png",
        observation_col="slices/gold_smoke_001/block_04_col_observation.png",
    )

    assert case["page"] == "gold_smoke_001"
    assert case["field"] == OBS_FIELD
    assert case["main_eval_kind"] == "substantive_mismatch"
    assert case["col_eval_kind"] == "equal"
    assert case["suggested_error_type"] == "col_better_than_main"
    assert case["human_error_type"] == ""
    assert case["image_paths"]["r_slice"].endswith("block_04_R.png")
    assert case["image_paths"]["observation_col"].endswith("block_04_col_observation.png")
    assert "RASS-3" in case["main_norm"]
    assert "RASS-4" in case["col_norm"]


def test_build_observation_cases_for_page_keeps_all_non_equal_observation_cases():
    gold_rows = [
        {"_block_id": "block_00", OBS_FIELD: "A1"},
        {"_block_id": "block_01", OBS_FIELD: "B2"},
        {"_block_id": "block_02", OBS_FIELD: "C3"},
    ]
    main_rows = [
        {"_block_id": "block_00", OBS_FIELD: "A1"},
        {"_block_id": "block_01", OBS_FIELD: "B"},
        {"_block_id": "block_02", OBS_FIELD: "C3"},
    ]
    col_rows = [
        {"block_id": "block_00", OBS_FIELD: "A1"},
        {"block_id": "block_01", OBS_FIELD: "B2"},
        {"block_id": "block_02", OBS_FIELD: "C"},
    ]

    cases = build_observation_cases_for_page(
        page="p",
        gold_rows=gold_rows,
        main_rows=main_rows,
        col_rows=col_rows,
        slice_root="runs/slices",
    )

    assert [case["block_id"] for case in cases] == ["block_01", "block_02"]
    assert cases[0]["suggested_error_type"] == "col_better_than_main"
    assert cases[1]["suggested_error_type"] == "main_better_than_col"


def test_write_casebook_outputs_markdown_jsonl_and_summary(tmp_path):
    cases = [
        build_observation_case(
            page="p",
            block_id="block_01",
            gold="B2",
            main_value="B",
            col_value="B2",
            r_slice="runs/slices/p/block_01_R.png",
            observation_col="runs/slices/p/block_01_col_observation.png",
        )
    ]
    summary = summarize_cases(cases)

    write_casebook(tmp_path, cases, summary, metadata={"model_calls": 0})

    md = (tmp_path / "observation_residual_casebook.md").read_text(encoding="utf-8")
    assert "| p | block_01 |" in md
    assert "col_better_than_main" in md
    assert "runs/slices/p/block_01_R.png" in md
    assert "runs/slices/p/block_01_col_observation.png" in md
    lines = (tmp_path / "observation_residual_cases.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["field"] == OBS_FIELD
    payload = json.loads((tmp_path / "observation_residual_summary.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_calls"] == 0
    assert payload["summary"]["col_better_than_main"] == 1
