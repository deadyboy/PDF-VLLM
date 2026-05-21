from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import load_config, prepare_run_dirs

SHEET01_COLUMNS = ["住院号", "床号", "性别", "年龄", "体重", "诊断"]

SHEET02_COLUMNS = [
    "住院号", "年份", "日期", "时间", "意识",
    "左瞳孔大小（mm）", "左瞳孔反射", "右瞳孔大小（mm）", "右瞳孔反射",
    "T（体温）", "HR（心率）", "R（呼吸）", "SBP（收缩压）", "DBP（舒张压）",
    "SPO2（氧饱和度）", "CVP", "人工气道方式", "插管深度",
    "呼吸机模式", "VT（潮气量）", "f(呼吸频率)", "FiO2（吸氧浓度）",
    "PEEP", "PC/PS", "给氧方式（无呼吸机）", "给氧流量", "给氧浓度",
    "静脉用药", "其他（非静脉用药）", "每时", "总量",
    "出量-总量", "出量-尿量", "出量-大便颜色性状", "其他出量",
    "痰-色", "痰-量",
    "管道护理-名称", "管道护理-通畅", "管道护理-颜色", "管道护理-外露刻度", "管道护理-留置刻度",
    "床头抬高30°", "约束部位", "约束部位情况", "体位", "血糖",
    "气切护理", "皮肤护理", "护理措施", "APACHEII", "病情观察及处理",
]

SHEET03_COLUMNS = [
    "住院号", "来源文件页码", "日期(推断)", "小结类型",
    "总入量", "静脉用药量", "口服总量", "总出量", "尿量",
]


def parse_filename(filename: str) -> tuple[str, int, str | None]:
    stem = Path(filename).stem.replace("_result", "")
    parts = stem.split("_")
    patient_id = parts[0]
    page_num = int(parts[-1])
    year = parts[1] if len(parts) >= 5 else None
    return patient_id, page_num, year


def _match_id(value: str) -> str:
    stripped = str(value).lstrip("0")
    return stripped or "0"


def padded_patient_id(patient_id: str) -> str:
    return str(patient_id).zfill(10)


def load_patient_info(patient_id: str, cache_dir: str | Path) -> dict[str, Any]:
    target_id = _match_id(patient_id)
    for fpath in glob.glob(os.path.join(str(cache_dir), "*.json")):
        if _match_id(Path(fpath).stem) != target_id:
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {}


def safe_split(value: Any, sep: str = "/", num_parts: int = 2) -> list[Any]:
    if value is None:
        return [None] * num_parts
    parts = str(value).split(sep)
    out = []
    for idx in range(num_parts):
        if idx < len(parts):
            v = parts[idx].strip()
            out.append(v if v else None)
        else:
            out.append(None)
    return out


def is_summary_block(block: dict[str, Any]) -> bool:
    block_id = str(block.get("_block_id", ""))
    return block_id.startswith("summary_") or "小结类型" in block


def map_block_to_sheet02(block: dict[str, Any], patient_info: dict[str, Any], year: str | None) -> dict[str, Any]:
    left_pupil = safe_split(block.get("瞳孔_左"))
    right_pupil = safe_split(block.get("瞳孔_右"))
    bp = safe_split(block.get("血压"))
    oxygen = safe_split(block.get("给氧方式"), sep="/", num_parts=3)
    sputum = safe_split(block.get("痰"), sep="/", num_parts=2)
    tube = safe_split(block.get("管路护理"), sep="/", num_parts=5)
    restraint = safe_split(block.get("约束"), sep="/", num_parts=2)

    return {
        "住院号": patient_info.get("住院号"),
        "年份": year,
        "日期": block.get("日期"),
        "时间": block.get("时间"),
        "意识": block.get("意识"),
        "左瞳孔大小（mm）": left_pupil[0],
        "左瞳孔反射": left_pupil[1],
        "右瞳孔大小（mm）": right_pupil[0],
        "右瞳孔反射": right_pupil[1],
        "T（体温）": block.get("体温"),
        "HR（心率）": block.get("心率"),
        "R（呼吸）": block.get("呼吸"),
        "SBP（收缩压）": bp[0],
        "DBP（舒张压）": bp[1],
        "SPO2（氧饱和度）": block.get("血氧"),
        "CVP": block.get("CVP"),
        "人工气道方式": block.get("人工气道方式"),
        "插管深度": block.get("插管深度"),
        "呼吸机模式": block.get("呼吸模式"),
        "VT（潮气量）": block.get("VT"),
        "f(呼吸频率)": block.get("f"),
        "FiO2（吸氧浓度）": block.get("FiO2"),
        "PEEP": block.get("PEEP"),
        "PC/PS": block.get("PC/PS"),
        "给氧方式（无呼吸机）": oxygen[0],
        "给氧流量": oxygen[1],
        "给氧浓度": oxygen[2],
        "静脉用药": block.get("入量_静脉用药"),
        "其他（非静脉用药）": block.get("入量_其他"),
        "每时": block.get("入量_每时"),
        "总量": block.get("入量_总量"),
        "出量-总量": block.get("出量_总量"),
        "出量-尿量": block.get("尿量"),
        "出量-大便颜色性状": block.get("大便"),
        "其他出量": block.get("其他出量"),
        "痰-色": sputum[0],
        "痰-量": sputum[1],
        "管道护理-名称": tube[0],
        "管道护理-通畅": tube[1],
        "管道护理-颜色": tube[2],
        "管道护理-外露刻度": tube[3],
        "管道护理-留置刻度": tube[4],
        "床头抬高30°": block.get("床头抬高"),
        "约束部位": restraint[0],
        "约束部位情况": restraint[1],
        "体位": block.get("体位"),
        "血糖": block.get("血糖"),
        "气切护理": block.get("气切护理"),
        "皮肤护理": block.get("皮肤护理"),
        "护理措施": block.get("护理措施"),
        "APACHEII": block.get("APACHEII"),
        "病情观察及处理": block.get("病情观察及处理"),
    }


def map_summary_to_sheet03(
    summary: dict[str, Any],
    patient_info: dict[str, Any],
    page_num: int,
    last_date: str | None,
) -> dict[str, Any]:
    return {
        "住院号": patient_info.get("住院号"),
        "来源文件页码": page_num,
        "日期(推断)": last_date,
        "小结类型": summary.get("小结类型"),
        "总入量": summary.get("总入量"),
        "静脉用药量": summary.get("静脉用药量"),
        "口服总量": summary.get("口服总量"),
        "总出量": summary.get("总出量"),
        "尿量": summary.get("尿量"),
    }


def process_patient(
    patient_id: str,
    result_files: list[str],
    patient_info: dict[str, Any],
    base_year: str | None,
) -> tuple[Any, Any, Any]:
    import pandas as pd

    sheet01 = [{col: patient_info.get(col) for col in SHEET01_COLUMNS}]
    rows02: list[dict[str, Any]] = []
    rows03: list[dict[str, Any]] = []
    last_date = None

    def sort_key(fpath: str) -> tuple[int, str]:
        _, page_num, _ = parse_filename(os.path.basename(fpath))
        return page_num, os.path.basename(fpath)

    for fpath in sorted(result_files, key=sort_key):
        _, page_num, year = parse_filename(os.path.basename(fpath))
        with open(fpath, "r", encoding="utf-8") as f:
            blocks = json.load(f)
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if is_summary_block(block):
                rows03.append(map_summary_to_sheet03(block, patient_info, page_num, last_date))
                continue
            row = map_block_to_sheet02(block, patient_info, year or base_year)
            if row.get("日期"):
                last_date = row["日期"]
            rows02.append(row)

    return (
        pd.DataFrame(sheet01, columns=SHEET01_COLUMNS),
        pd.DataFrame(rows02, columns=SHEET02_COLUMNS),
        pd.DataFrame(rows03, columns=SHEET03_COLUMNS),
    )


def merge_run(run_dir: Path, patient_id: str | None = None) -> int:
    import pandas as pd

    result_dir = run_dir / "results_json"
    cache_dir = run_dir / "patient_cache"
    output_dir = run_dir / "excel"
    output_dir.mkdir(parents=True, exist_ok=True)

    patient_files: dict[str, list[str]] = defaultdict(list)
    patient_years: dict[str, str] = {}
    for fpath in glob.glob(str(result_dir / "*_result.json")):
        try:
            pid, _page, year = parse_filename(os.path.basename(fpath))
        except Exception:
            continue
        if patient_id and _match_id(pid) != _match_id(patient_id):
            continue
        patient_files[pid].append(fpath)
        if year and pid not in patient_years:
            patient_years[pid] = year

    count = 0
    for pid, files in patient_files.items():
        patient_info = load_patient_info(pid, cache_dir)
        padded_id = padded_patient_id(pid)
        patient_info["住院号"] = padded_id
        patient_info.pop("姓名", None)
        df01, df02, df03 = process_patient(pid, files, patient_info, patient_years.get(pid))
        output_file = output_dir / f"{padded_id}_护理记录单.xlsx"
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df01.to_excel(writer, sheet_name="01 基本信息", index=False)
            df02.to_excel(writer, sheet_name="02 主要变量", index=False)
            df03.to_excel(writer, sheet_name="03 出入量", index=False)
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge one vLLM run into patient Excel files")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--patient-id")
    args = parser.parse_args(argv)

    count = merge_run(Path(args.run_dir), args.patient_id)
    print(f"merged_patients={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
