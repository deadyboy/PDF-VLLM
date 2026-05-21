from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionProfile:
    name: str
    cutter_script: str
    column_suffixes: tuple[str, ...]
    prompt_names: tuple[str, ...]
    enable_summary: bool = False
    header_prompt_name: str | None = None


PROFILES: dict[str, ExtractionProfile] = {
    "jin": ExtractionProfile(
        name="jin",
        cutter_script="cutter_worker_jin.py",
        column_suffixes=("L", "M", "R"),
        prompt_names=("PROMPT_L", "PROMPT_M", "PROMPT_R"),
        enable_summary=True,
        header_prompt_name="PROMPT_HEADER",
    ),
    "wang_record1": ExtractionProfile(
        name="wang_record1",
        cutter_script="cutter_worker_wang_record1.py",
        column_suffixes=("1", "2", "3"),
        prompt_names=("PROMPT_RECORD1_1", "PROMPT_RECORD1_2", "PROMPT_RECORD1_3"),
        enable_summary=False,
        header_prompt_name=None,
    ),
    "wang_record2": ExtractionProfile(
        name="wang_record2",
        cutter_script="cutter_worker_wang_record2.py",
        column_suffixes=("1", "2", "3", "4", "5"),
        prompt_names=(
            "PROMPT_RECORD2_1",
            "PROMPT_RECORD2_2",
            "PROMPT_RECORD2_3",
            "PROMPT_RECORD2_4",
            "PROMPT_RECORD2_5",
        ),
        enable_summary=False,
        header_prompt_name="PROMPT_RECORD2_HEADER",
    ),
}


def get_profile(name: str) -> ExtractionProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        known = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile {name!r}; expected one of: {known}") from exc
