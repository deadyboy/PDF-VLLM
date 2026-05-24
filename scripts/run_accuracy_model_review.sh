#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-/data1/jianf-vllm}
PY=${PY:-/home/jianf/miniconda3/envs/vllm/bin/python}
TARGET_IMAGE_NAME=${TARGET_IMAGE_NAME:-0013807667_2023_10_15_3.png}
GOLD_PATH=${GOLD_PATH:-/tmp/0013807667_2023_10_15_3_gold.json}
INPUT_DIR=${INPUT_DIR:-/data1/jianf/新提取pdf/180data}
STAMP=${STAMP:-$(date +%Y%m%d-%H%M%S)}

cd "$PROJECT_DIR"

if [ ! -f "$GOLD_PATH" ]; then
  echo "Gold file not found: $GOLD_PATH" >&2
  echo "Copy C:\\Users\\lenovo\\Desktop\\图像金标准\\0013807667_2023_10_15_3_result.json to $GOLD_PATH first." >&2
  exit 2
fi

if [ ! -f "$INPUT_DIR/$TARGET_IMAGE_NAME" ]; then
  echo "Target image not found: $INPUT_DIR/$TARGET_IMAGE_NAME" >&2
  exit 2
fi

SAMPLE="/tmp/model_compare_${TARGET_IMAGE_NAME%.png}_${STAMP}.txt"
LABELS="/tmp/model_compare_labels_${STAMP}.txt"
RUN_LIST="/tmp/model_compare_${TARGET_IMAGE_NAME%.png}_runs_${STAMP}.json"
LATEST="/tmp/model_compare_${TARGET_IMAGE_NAME%.png}_runs_latest.json"
: > "$LABELS"
printf '%s\n' "$TARGET_IMAGE_NAME" > "$SAMPLE"

make_cfg() {
  local cfg=$1 base_url=$2 model_name=$3
  "$PY" - "$cfg" "$base_url" "$model_name" <<'PY'
from pathlib import Path
import sys

cfg, base_url, model_name = sys.argv[1:4]
src = Path("/data1/jianf-vllm/config/default.toml").read_text(encoding="utf-8")
lines = []
section = None
for raw in src.splitlines():
    line = raw.strip()
    if line.startswith("[") and line.endswith("]"):
        section = line[1:-1]
        lines.append(raw)
        continue
    if section == "pipeline" and line.startswith("keep_success_m_evidence"):
        lines.append("keep_success_m_evidence = false")
    elif section == "vllm" and line.startswith("base_url"):
        lines.append(f'base_url = "{base_url}"')
    elif section == "vllm" and line.startswith("model_name"):
        lines.append(f'model_name = "{model_name}"')
    elif section == "concurrency" and line.startswith("max_concurrent_llm"):
        lines.append("max_concurrent_llm = 4")
    elif section == "concurrency" and line.startswith("max_concurrent_cut"):
        lines.append("max_concurrent_cut = 1")
    elif section == "concurrency" and line.startswith("max_concurrent_img"):
        lines.append("max_concurrent_img = 1")
    else:
        lines.append(raw)
Path(cfg).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

wait_model() {
  local base_url=$1 session=${2:-}
  for i in $(seq 1 180); do
    if curl -sS --max-time 5 "$base_url/models" >/tmp/model_compare_models.json 2>/tmp/model_compare_curl.err; then
      cat /tmp/model_compare_models.json
      return 0
    fi
    sleep 5
    if [ -n "$session" ] && ! tmux has-session -t "$session" 2>/dev/null; then
      echo "Service exited: $session" >&2
      return 1
    fi
    echo "waiting $base_url $i"
  done
  echo "Timed out waiting for $base_url" >&2
  return 1
}

start_service() {
  local session=$1 model_path=$2 served=$3 port=$4 gpu_ids=$5 tp=$6 dp=$7 max_num_seqs=$8 max_len=$9
  local log="runs/model_compare_${served}_${port}_${STAMP}.log"
  tmux kill-session -t "$session" 2>/dev/null || true
  tmux new-session -d -s "$session" \
    "cd '$PROJECT_DIR' && source /home/jianf/miniconda3/etc/profile.d/conda.sh && conda activate vllm && MODEL_PATH='$model_path' TENSOR_PARALLEL='$tp' DATA_PARALLEL='$dp' PORT='$port' HOST=127.0.0.1 GPU_IDS='$gpu_ids' SERVED_MODEL_NAME='$served' MAX_MODEL_LEN='$max_len' MAX_NUM_SEQS='$max_num_seqs' GPU_MEMORY_UTILIZATION=0.88 MM_PROCESSOR_CACHE_GB=0 GENERATION_CONFIG=vllm OMP_NUM_THREADS=1 bash scripts/start_vllm_server.sh 2>&1 | tee '$log'"
  echo "STARTED session=$session served=$served port=$port log=$log"
  wait_model "http://127.0.0.1:$port/v1" "$session" || {
    tail -160 "$log" || true
    return 1
  }
}

run_once() {
  local label=$1 cfg=$2
  local run_id="modelcmp-${label}-${STAMP}"
  echo "RUN_BEGIN $label $run_id"
  "$PY" -m icu_vllm.run --config "$cfg" --run-id "$run_id" --samples-file "$SAMPLE"
  echo "RUN_DONE $label $run_id"
  printf '%s %s\n' "$label" "$run_id" >> "$LABELS"
}

stop_if_started() {
  local session=$1
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session"
    sleep 5
  fi
}

# Qwen3-VL-32B: prefer the existing long-lived service if present.
Q3_32_CFG="/tmp/model_compare_qwen3_32b_${STAMP}.toml"
Q3_32_BASE=${Q3_32_BASE:-http://172.18.0.1:18080/v1}
Q3_32_STARTED_SESSION=""
if curl -sS --max-time 5 "$Q3_32_BASE/models" >/dev/null 2>&1; then
  echo "Using existing Qwen3-VL-32B service: $Q3_32_BASE"
else
  Q3_32_BASE="http://127.0.0.1:8006/v1"
  Q3_32_STARTED_SESSION="modelcmp_qwen3_32b_8006"
  start_service "$Q3_32_STARTED_SESSION" /data1/bigmodels/Qwen3-VL-32B-Instruct qwen3-vl-32b 8006 "${Q3_32_GPU_IDS:-1,2}" "${Q3_32_TP:-2}" 1 4 24576
fi
make_cfg "$Q3_32_CFG" "$Q3_32_BASE" qwen3-vl-32b
wait_model "$Q3_32_BASE"
run_once qwen3_32b_rep1 "$Q3_32_CFG"
run_once qwen3_32b_rep2 "$Q3_32_CFG"
run_once qwen3_32b_rep3 "$Q3_32_CFG"
if [ -n "$Q3_32_STARTED_SESSION" ]; then stop_if_started "$Q3_32_STARTED_SESSION"; fi

# Qwen2.5-VL-72B: larger-reference model. Defaults avoid GPUs 6/7 when a long-lived
# Qwen3-32B service is running; override Q25_72_GPU_IDS/Q25_72_TP/Q25_72_DP to use all GPUs.
Q25_72_CFG="/tmp/model_compare_qwen25_72b_${STAMP}.toml"
make_cfg "$Q25_72_CFG" http://127.0.0.1:8002/v1 qwen2.5vl-72b
start_service modelcmp_qwen25_72b_8002 /data1/bigmodels/qwen2.5-vl-72B qwen2.5vl-72b 8002 "${Q25_72_GPU_IDS:-1,2,3,4}" "${Q25_72_TP:-4}" "${Q25_72_DP:-1}" 4 24576
run_once qwen25_72b "$Q25_72_CFG"
stop_if_started modelcmp_qwen25_72b_8002

# Qwen2.5-VL-32B.
Q25_32_CFG="/tmp/model_compare_qwen25_32b_${STAMP}.toml"
make_cfg "$Q25_32_CFG" http://127.0.0.1:8004/v1 qwen2.5vl-32b
start_service modelcmp_qwen25_32b_8004 /data1/bigmodels/Qwen2.5-VL-32B-Instruct qwen2.5vl-32b 8004 "${Q25_32_GPU_IDS:-1,2}" "${Q25_32_TP:-2}" 1 4 24576
run_once qwen25_32b "$Q25_32_CFG"
stop_if_started modelcmp_qwen25_32b_8004

# Qwen3-VL-8B.
Q3_8_CFG="/tmp/model_compare_qwen3_8b_${STAMP}.toml"
make_cfg "$Q3_8_CFG" http://127.0.0.1:8005/v1 qwen3vl-8b
start_service modelcmp_qwen3_8b_8005 /data1/bigmodels/Qwen3-VL-8B-Instruct qwen3vl-8b 8005 "${Q3_8_GPU_IDS:-1}" "${Q3_8_TP:-1}" 1 4 24576
run_once qwen3_8b "$Q3_8_CFG"
stop_if_started modelcmp_qwen3_8b_8005

"$PY" - "$STAMP" "$LABELS" "$RUN_LIST" "$LATEST" "$GOLD_PATH" "$TARGET_IMAGE_NAME" <<'PY'
from pathlib import Path
import json
import itertools
from collections import Counter
import sys

stamp, labels_path, run_list_path, latest_path, gold_path, target_image = sys.argv[1:7]
base = Path("/data1/jianf-vllm/runs")
result_name = f"{Path(target_image).stem}_result.json"
gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
labels = []
for line in Path(labels_path).read_text(encoding="utf-8").splitlines():
    label, run_id = line.split(maxsplit=1)
    labels.append({"label": label, "run_id": run_id})
Path(run_list_path).write_text(json.dumps({"stamp": stamp, "runs": labels}, ensure_ascii=False, indent=2), encoding="utf-8")
Path(latest_path).write_text(Path(run_list_path).read_text(encoding="utf-8"), encoding="utf-8")

L = {"日期","时间","意识","瞳孔_左","瞳孔_右","体温","心率","呼吸","血压","血氧","CVP","人工气道方式","插管深度","呼吸模式","VT","f","FiO2","PEEP","PC/PS","给氧方式"}
M = {"入量_静脉用药","入量_其他","入量_每时","入量_总量","出量_总量","出量_尿量","出量_大便_颜色性状","出量_其他出量","痰_色","痰_量","管路护理"}
R = {"床头抬高30度","气囊压力","约束部位_情况","体位","血糖","气切护理","皮肤护理","护理措施","APACHEII","病情观察及处理"}
IGNORE = {"_profile"}

def group(key: str) -> str:
    return "M" if key in M else "L" if key in L else "R" if key in R else "other"

def kind(expected, actual) -> str:
    if expected is None and actual is not None:
        return "overfill"
    if expected is not None and actual is None:
        return "missing"
    return "mismatch"

def by_block(rows):
    return {
        str(row.get("_block_id", f"idx_{idx}")): row
        for idx, row in enumerate(rows)
        if isinstance(row, dict)
    }

def diff_rows(actual, expected):
    actual_blocks = by_block(actual)
    expected_blocks = by_block(expected)
    diffs = []
    for block_id in sorted(set(actual_blocks) | set(expected_blocks)):
        actual_row = actual_blocks.get(block_id, {})
        expected_row = expected_blocks.get(block_id, {})
        for key in sorted((set(actual_row) | set(expected_row)) - IGNORE):
            expected_value = expected_row.get(key, None)
            actual_value = actual_row.get(key, None)
            if expected_value != actual_value:
                diffs.append({
                    "block": block_id,
                    "field": key,
                    "group": group(key),
                    "kind": kind(expected_value, actual_value),
                    "gold": expected_value,
                    "actual": actual_value,
                })
    return diffs

def diff_between(left_rows, right_rows, left_label, right_label):
    left_blocks = by_block(left_rows)
    right_blocks = by_block(right_rows)
    diffs = []
    for block_id in sorted(set(left_blocks) | set(right_blocks)):
        left_row = left_blocks.get(block_id, {})
        right_row = right_blocks.get(block_id, {})
        for key in sorted((set(left_row) | set(right_row)) - IGNORE):
            left_value = left_row.get(key, None)
            right_value = right_row.get(key, None)
            if left_value != right_value:
                diffs.append({
                    "block": block_id,
                    "field": key,
                    "group": group(key),
                    left_label: left_value,
                    right_label: right_value,
                })
    return diffs

def count_by_group(diffs):
    counts = Counter(d["group"] for d in diffs)
    return {key: counts.get(key, 0) for key in ["L", "M", "R", "other"]}

runs = []
for item in labels:
    run_dir = base / item["run_id"]
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = json.loads((run_dir / "results_json" / result_name).read_text(encoding="utf-8"))
    diffs = diff_rows(rows, gold)
    runs.append({
        "label": item["label"],
        "run_id": item["run_id"],
        "run_dir": str(run_dir),
        "model_name": manifest.get("model_name"),
        "elapsed_seconds": manifest.get("elapsed_seconds"),
        "success": manifest.get("success"),
        "failed": manifest.get("failed"),
        "objects": len(rows),
        "rows": rows,
        "diffs": diffs,
    })

rep_runs = [run for run in runs if run["label"].startswith("qwen3_32b_rep")]
pairwise = []
for left, right in itertools.combinations(rep_runs, 2):
    diffs = diff_between(left["rows"], right["rows"], left["label"], right["label"])
    pairwise.append({
        "left": left["label"],
        "right": right["label"],
        "exact_equal": left["rows"] == right["rows"],
        "total": len(diffs),
        "by_group": count_by_group(diffs),
        "sample_diffs": diffs[:20],
    })

model_order = ["qwen3_32b_rep1", "qwen25_72b", "qwen25_32b", "qwen3_8b"]
model_runs = [run for label in model_order for run in runs if run["label"] == label]

out_dir = base / f"model_compare_report_{stamp}"
out_dir.mkdir(exist_ok=True)
summary = {
    "stamp": stamp,
    "target_image": f"/data1/jianf/新提取pdf/180data/{target_image}",
    "gold_path": gold_path,
    "result_name": result_name,
    "runs": [
        {
            "label": run["label"],
            "run_id": run["run_id"],
            "run_dir": run["run_dir"],
            "model_name": run["model_name"],
            "elapsed_seconds": run["elapsed_seconds"],
            "success": run["success"],
            "failed": run["failed"],
            "objects": run["objects"],
            "total_diffs": len(run["diffs"]),
            "by_group": count_by_group(run["diffs"]),
            "by_kind": dict(Counter(diff["kind"] for diff in run["diffs"])),
            "top_fields": Counter(diff["field"] for diff in run["diffs"]).most_common(10),
        }
        for run in runs
    ],
    "qwen3_32b_repetition_pairwise": pairwise,
}
(out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

lines = ["# Accuracy Model Review", ""]
lines.append(f"- stamp: `{stamp}`")
lines.append(f"- target: `/data1/jianf/新提取pdf/180data/{target_image}`")
lines.append(f"- gold: `{gold_path}`")
lines.append("")
lines.append("| label | model | run_id | seconds | total | L | M | R | missing | overfill | mismatch |")
lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for run in model_runs:
    by_group = count_by_group(run["diffs"])
    by_kind = Counter(diff["kind"] for diff in run["diffs"])
    lines.append(
        f"| {run['label']} | {run['model_name']} | {run['run_id']} | {run['elapsed_seconds']} | "
        f"{len(run['diffs'])} | {by_group['L']} | {by_group['M']} | {by_group['R']} | "
        f"{by_kind.get('missing', 0)} | {by_kind.get('overfill', 0)} | {by_kind.get('mismatch', 0)} |"
    )
lines.append("")
lines.append("## Qwen3-VL-32B Repeatability")
lines.append("| pair | exact_equal | total | L | M | R |")
lines.append("|---|---:|---:|---:|---:|---:|")
for item in pairwise:
    by_group = item["by_group"]
    lines.append(f"| {item['left']} vs {item['right']} | {item['exact_equal']} | {item['total']} | {by_group['L']} | {by_group['M']} | {by_group['R']} |")
lines.append("")
for run in model_runs:
    lines.append(f"## {run['label']} M Diffs")
    for diff in [d for d in run["diffs"] if d["group"] == "M"][:40]:
        def short(value):
            text = "null" if value is None else str(value)
            return text if len(text) <= 180 else text[:177] + "..."
        lines.append(f"- {diff['block']} `{diff['field']}` {diff['kind']}: gold={short(diff['gold'])} | actual={short(diff['actual'])}")
    lines.append("")
(out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
print(f"REPORT_DIR={out_dir}")
print((out_dir / "report.md").read_text(encoding="utf-8"))
PY

