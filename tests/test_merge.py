import json

from icu_vllm.merge import load_patient_info, parse_filename, padded_patient_id


def test_parse_filename_extracts_patient_page_and_year():
    patient_id, page_num, year = parse_filename("0010016667_2025_4_25_10_result.json")

    assert patient_id == "0010016667"
    assert page_num == 10
    assert year == "2025"


def test_patient_cache_matches_by_filename_not_extracted_id(tmp_path):
    cache = tmp_path / "patient_cache"
    cache.mkdir()
    (cache / "0010016667.json").write_text(
        json.dumps({"住院号": "模型错识别", "姓名": "张三", "年龄": "66"}, ensure_ascii=False),
        encoding="utf-8",
    )

    data = load_patient_info("10016667", cache)

    assert data["住院号"] == "模型错识别"
    assert data["年龄"] == "66"


def test_padded_patient_id_uses_filename_id():
    assert padded_patient_id("10016667") == "0010016667"
