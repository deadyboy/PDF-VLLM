from __future__ import annotations

import json
import re
from typing import Any

try:
    from json_repair import repair_json
except Exception:  # pragma: no cover - production env has json_repair
    repair_json = None


KEY_ALIASES = {
    "床头抬高30°": "床头抬高30度",
}


def normalize_nulls(data_dict: dict[str, Any]) -> dict[str, Any]:
    for source, target in KEY_ALIASES.items():
        if source not in data_dict:
            continue
        source_value = data_dict.pop(source)
        if target not in data_dict or data_dict[target] in (None, "", "null", "NULL"):
            data_dict[target] = source_value

    for key, value in data_dict.items():
        if isinstance(value, str) and value.strip().lower() in ["null", "none", ""]:
            data_dict[key] = None
    return data_dict


def parse_model_json(raw: str) -> dict[str, Any]:
    if not raw or "{" not in raw:
        raise ValueError(f"model returned no JSON object: {raw[:80]!r}")

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    raw_json_str = match.group(0) if match else raw
    raw_json_str = re.sub(
        r'(:\s*)([0-9]+(?:→|->|~|-)[0-9]+)(\s*[,}])',
        r'\1"\2"\3',
        raw_json_str,
    )

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError:
        if repair_json is None:
            raise
        data = repair_json(raw_json_str, return_objects=True)

    if isinstance(data, list):
        if not data:
            return {}
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError(f"model JSON was {type(data).__name__}, expected object")
    return data
