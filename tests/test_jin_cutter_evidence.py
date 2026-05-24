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
