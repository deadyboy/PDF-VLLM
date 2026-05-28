from icu_vllm.iv_eval import classify_iv_diff


def test_iv_diff_classifies_unit_case_equal():
    diff = classify_iv_diff(
        "5%GS100ml+葡萄糖酸钙20MLiv.gtt120",
        "5%GS100ml+葡萄糖酸钙20mliv.gtt120",
    )

    assert diff["kind"] == "unit_case_equal"


def test_iv_diff_classifies_manufacturer_punctuation_equal():
    diff = classify_iv_diff(
        "枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持",
        "枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持",
    )

    assert diff["kind"] == "manufacturer_punctuation_equal"


def test_iv_diff_classifies_gold_needs_check_for_m1_vs_ml():
    diff = classify_iv_diff(
        "白蛋白10giv.gtt50;NS50m1+肝素0.5支iv微泵维持",
        "白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持",
    )

    assert diff["kind"] == "gold_needs_check"


def test_iv_diff_keeps_true_char_mismatch_for_l_vs_1():
    diff = classify_iv_diff(
        "枸橼酸舒芬太尼注射液4ml/l+氯化钠注射液46MLiv微泵维",
        "枸橼酸舒芬太尼注射液4ml/1+氯化钠注射液46MLiv微泵维",
    )

    assert diff["kind"] == "true_char_mismatch"
