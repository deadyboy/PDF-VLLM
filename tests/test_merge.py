import json

from icu_vllm.merge import load_patient_info, map_block_to_sheet02, parse_filename, padded_patient_id


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


def test_jin_sheet02_mapping_uses_prompt_field_names():
    row = map_block_to_sheet02(
        {
            "出量_尿量": "100",
            "出量_大便_颜色性状": "黄软",
            "出量_其他出量": "引流20",
            "痰_色": "白",
            "痰_量": "少",
            "床头抬高30度": "是",
            "约束部位_情况": "双上肢/良好",
        },
        {"住院号": "0010016667"},
        "2025",
    )

    assert row["出量-尿量"] == "100"
    assert row["出量-大便颜色性状"] == "黄软"
    assert row["其他出量"] == "引流20"
    assert row["痰-色"] == "白"
    assert row["痰-量"] == "少"
    assert row["床头抬高30°"] == "是"
    assert row["约束部位"] == "双上肢"
    assert row["约束部位情况"] == "良好"
