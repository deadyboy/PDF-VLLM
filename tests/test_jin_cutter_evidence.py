import importlib
import json
import sys
import types


def load_jin_cutter(monkeypatch):
    monkeypatch.setitem(sys.modules, "cv2", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "paddleocr", types.SimpleNamespace(PaddleOCR=object))
    import icu_vllm.cutter_worker_jin as cutter

    return importlib.reload(cutter)


def test_write_ocr_evidence_json_sorts_by_position(tmp_path, monkeypatch):
    cutter = load_jin_cutter(monkeypatch)

    ocr_result = [[
        ([[20, 5], [30, 5], [30, 15], [20, 15]], ("right", 0.91)),
        ([[0, 5], [10, 5], [10, 15], [0, 15]], ("left", 0.98)),
        ([[0, 40], [10, 40], [10, 50], [0, 50]], ("lower", 0.88)),
    ]]

    cutter.write_ocr_evidence_json(tmp_path, "block_00_M", ocr_result)

    data = json.loads((tmp_path / "block_00_M.ocr.json").read_text(encoding="utf-8"))
    assert data["image"] == "block_00_M.png"
    assert data["part"] == "M"
    assert [item["text"] for item in data["ocr_items"]] == ["left", "right", "lower"]
    assert data["ocr_items"][0]["bbox"] == [[0.0, 5.0], [10.0, 5.0], [10.0, 15.0], [0.0, 15.0]]
    assert data["ocr_items"][0]["score"] == 0.98
    assert data["ocr_items"][0]["center_x"] == 5.0
    assert data["ocr_items"][0]["center_y"] == 10.0


def test_write_ocr_evidence_json_writes_empty_items_when_no_ocr(tmp_path, monkeypatch):
    cutter = load_jin_cutter(monkeypatch)

    cutter.write_ocr_evidence_json(tmp_path, "block_00_M", None)

    data = json.loads((tmp_path / "block_00_M.ocr.json").read_text(encoding="utf-8"))
    assert data == {
        "image": "block_00_M.png",
        "part": "M",
        "ocr_items": [],
    }


def test_jin_column_splits_keep_m_prompt_fields_in_m_slice(monkeypatch):
    cutter = load_jin_cutter(monkeypatch)

    col_xs = [
        21, 92, 164, 213, 235, 251, 292, 306, 377, 409, 448, 519,
        590, 679, 750, 839, 910, 981, 1052, 1124, 1176, 1229, 1282,
        1354, 1398, 1425, 1852, 2172, 2243, 2332, 2421, 2493, 2563,
        2776, 2829, 2883, 3096, 3150, 3221, 3292, 3346, 3453, 3506,
        3559, 3684, 3755, 4306, 4430,
    ]

    assert cutter.choose_jin_column_splits(col_xs, image_width=4451) == (1176, 3096)


def test_jin_target_column_ranges_use_profile_grid_lines(monkeypatch):
    cutter = load_jin_cutter(monkeypatch)

    col_xs = [
        21, 92, 164, 213, 235, 251, 292, 306, 377, 409, 448, 519,
        590, 679, 750, 839, 910, 981, 1052, 1124, 1176, 1229, 1282,
        1354, 1398, 1425, 1852, 2172, 2243, 2332, 2421, 2493, 2563,
        2776, 2829, 2883, 3096, 3150, 3221, 3292, 3346, 3453, 3506,
        3559, 3684, 3755, 4306, 4430,
    ]

    ranges = cutter.choose_jin_target_column_ranges(col_xs, image_width=4451, padding=10)

    assert ranges["iv_drug"].field == "入量_静脉用药"
    assert ranges["iv_drug"].x1 == 1166
    assert ranges["iv_drug"].x2 == 1862
    assert ranges["tube_care"].field == "管路护理"
    assert ranges["tube_care"].x1 == 2873
    assert ranges["tube_care"].x2 == 3106
    assert ranges["observation"].field == "病情观察及处理"
    assert ranges["observation"].x1 == 3745
    assert ranges["observation"].x2 == 4316


def test_jin_target_column_ranges_fallback_stays_inside_image(monkeypatch):
    cutter = load_jin_cutter(monkeypatch)

    ranges = cutter.choose_jin_target_column_ranges([], image_width=1000, padding=50)

    assert ranges["iv_drug"].x1 == 250
    assert ranges["iv_drug"].x2 == 470
    assert ranges["tube_care"].x1 == 595
    assert ranges["tube_care"].x2 == 750
    assert ranges["observation"].x1 == 830
    assert ranges["observation"].x2 == 1000


def test_choose_header_bottom_y_uses_horizontal_line_gap(monkeypatch):
    cutter = load_jin_cutter(monkeypatch)

    merged_y = [
        299, 343, 520, 565, 610, 655, 698, 743, 788, 832, 876, 921,
        965, 1010, 1054, 1099,
    ]

    assert cutter.choose_header_bottom_y(merged_y, image_height=3130) == (520, 2)
