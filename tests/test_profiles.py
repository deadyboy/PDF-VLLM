from pathlib import Path

from icu_vllm.config import load_config
from icu_vllm.profiles import get_profile


def test_jin_profile_matches_current_180data_pipeline():
    profile = get_profile("jin")

    assert profile.column_suffixes == ("L", "M", "R")
    assert profile.cutter_script == "cutter_worker_jin.py"
    assert profile.enable_summary is True
    assert profile.header_prompt_name == "PROMPT_HEADER"


def test_wang_record_profiles_do_not_reuse_jin_columns():
    record1 = get_profile("wang_record1")
    record2 = get_profile("wang_record2")

    assert record1.column_suffixes == ("1", "2", "3")
    assert record1.prompt_names == ("PROMPT_RECORD1_1", "PROMPT_RECORD1_2", "PROMPT_RECORD1_3")
    assert record1.cutter_script == "cutter_worker_wang_record1.py"
    assert record1.enable_summary is False

    assert record2.column_suffixes == ("1", "2", "3", "4", "5")
    assert record2.prompt_names == (
        "PROMPT_RECORD2_1",
        "PROMPT_RECORD2_2",
        "PROMPT_RECORD2_3",
        "PROMPT_RECORD2_4",
        "PROMPT_RECORD2_5",
    )
    assert record2.cutter_script == "cutter_worker_wang_record2.py"
    assert record2.header_prompt_name == "PROMPT_RECORD2_HEADER"


def test_record_configs_point_to_routed_wang_inputs():
    record1_cfg = load_config(Path("config/wang_record1.toml"))
    record2_cfg = load_config(Path("config/wang_record2.toml"))

    assert record1_cfg.profile_name == "wang_record1"
    assert record1_cfg.input_dir.as_posix().endswith("/routed_data/data_record1")
    assert record2_cfg.profile_name == "wang_record2"
    assert record2_cfg.input_dir.as_posix().endswith("/routed_data/data_record2")
