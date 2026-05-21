from icu_vllm.json_utils import parse_model_json, normalize_nulls


def test_parse_model_json_extracts_object_and_quotes_arrow_values():
    raw = '说明文字 {"心率": 90, "瞳孔": 3→2, "备注": "ok"} 结束'

    data = parse_model_json(raw)

    assert data == {"心率": 90, "瞳孔": "3→2", "备注": "ok"}


def test_normalize_nulls_converts_false_null_strings():
    data = {"体温": "null", "血压": " None ", "备注": "", "心率": "90"}

    assert normalize_nulls(data) == {
        "体温": None,
        "血压": None,
        "备注": None,
        "心率": "90",
    }
