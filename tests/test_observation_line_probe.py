import json

import cv2
import numpy as np

from icu_vllm.observation_line_probe import (
    LINE_PROBE_SOURCES,
    build_line_contact_sheet,
    build_line_probe_row,
    combine_line_texts,
    detect_text_line_boxes,
    parse_line_transcription_response,
    summarize_line_probe_rows,
    write_line_probe_report,
)


def _synthetic_observation_crop() -> np.ndarray:
    image = np.full((180, 320, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (0, 0), (319, 179), (0, 0, 0), 1)
    cv2.line(image, (0, 60), (319, 60), (0, 0, 0), 1)
    cv2.rectangle(image, (30, 82), (210, 96), (0, 0, 0), -1)
    cv2.rectangle(image, (30, 123), (260, 137), (0, 0, 0), -1)
    return image


def test_detect_text_line_boxes_ignores_header_and_finds_data_lines():
    image = _synthetic_observation_crop()

    boxes = detect_text_line_boxes(image, data_top_y=60, padding_y=4)

    assert len(boxes) == 2
    assert boxes[0]["line_id"] == "01"
    assert boxes[0]["y1"] <= 82
    assert boxes[0]["y2"] >= 96
    assert boxes[1]["line_id"] == "02"
    assert boxes[1]["y1"] <= 123
    assert boxes[1]["y2"] >= 137


def test_build_line_contact_sheet_preserves_numbered_lines():
    image = _synthetic_observation_crop()
    boxes = detect_text_line_boxes(image, data_top_y=60, padding_y=4)
    crops = [image[box["y1"]:box["y2"], box["x1"]:box["x2"]] for box in boxes]

    sheet, placements = build_line_contact_sheet(crops, [box["line_id"] for box in boxes])

    assert sheet.shape[0] > sum(crop.shape[0] for crop in crops)
    assert placements[0]["line_id"] == "01"
    assert placements[1]["line_id"] == "02"
    assert placements[0]["sheet_y1"] < placements[1]["sheet_y1"]


def test_parse_line_response_and_combine_texts():
    raw = json.dumps(
        {
            "lines": {"02": "CPOT0分", "01": "患者继观。"},
            "uncertain_lines": ["02"],
            "needs_review": True,
        },
        ensure_ascii=False,
    )

    parsed, error = parse_line_transcription_response(raw)

    assert error is None
    assert parsed["lines"] == {"01": "患者继观。", "02": "CPOT0分"}
    assert parsed["uncertain_lines"] == ["02"]
    assert parsed["needs_review"] is True
    assert combine_line_texts(parsed["lines"]) == "患者继观。CPOT0分"


def test_build_row_and_summary_count_main_old_col_and_line_probe_sources():
    row = build_line_probe_row(
        page="gold_validation_003",
        block_id="block_03",
        gold="生命体征汇报值班医生，医嘱继观。",
        main_value="生命体征汇报值班医生，医嘱难观。",
        old_col_value="生命体征汇报值班医生，医嘱难观。",
        line_probe_a_value="生命体征汇报值班医生，医嘱继观。",
        line_probe_b_value="生命体征汇报值班医生，医嘱继观。",
    )

    summary = summarize_line_probe_rows([row])

    assert row["main_kind"] == "char_level_mismatch"
    assert row["line_probe_A_kind"] == "exact_equal"
    assert row["line_probe_B_kind"] == "exact_equal"
    assert tuple(summary["sources"]) == LINE_PROBE_SOURCES
    assert summary["source_counts"]["main"]["char_level_mismatch"] == 1
    assert summary["source_counts"]["line_probe_A"]["correct"] == 1
    assert summary["source_counts"]["line_probe_B"]["correct"] == 1


def test_write_line_probe_report_outputs_markdown_json_and_sidecars(tmp_path):
    row = build_line_probe_row(
        page="p",
        block_id="block_01",
        gold="CPOT0分",
        main_value=None,
        old_col_value="CPOT0分",
        line_probe_a_value="CPOT0分",
        line_probe_b_value="CPOT0分",
    )
    summary = summarize_line_probe_rows([row])
    sidecar = {
        "page": "p",
        "block_id": "block_01",
        "line_probe_A": {"final_value": "CPOT0分"},
        "line_probe_B": {"final_value": "CPOT0分"},
    }

    write_line_probe_report(tmp_path, [row], summary, [sidecar], metadata={"model_calls": 2})

    report = (tmp_path / "observation_line_probe_report.md").read_text(encoding="utf-8")
    assert "| p | block_01 |" in report
    assert "line_probe_A" in report
    payload = json.loads((tmp_path / "observation_line_probe_summary.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["model_calls"] == 2
    assert payload["summary"]["source_counts"]["old_col"]["correct"] == 1
    sidecars = list((tmp_path / "observation_line_probe_sidecars").glob("*.json"))
    assert len(sidecars) == 1
