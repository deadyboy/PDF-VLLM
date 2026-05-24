# PDF-VLLM Project Rules

## Purpose

This repository maintains the clean vLLM extraction pipeline for ICU nursing
record images. The old project under `/data1/jianf/新提取pdf` is a read-only
input source; generated outputs belong under `/data1/jianf-vllm/runs`.

## Accuracy Review Gate

For any code change that can affect extraction behavior, automatically run the
accuracy model review before reporting completion. This includes changes to:

- `icu_vllm/pipeline.py`, `icu_vllm/config.py`, `icu_vllm/profiles.py`,
  `icu_vllm/json_utils.py`, `icu_vllm/merge.py`, `icu_vllm/inspect.py`
- `icu_vllm/cutter_worker_*.py`
- `icu_vllm/prompts.py`
- model/config files under `config/`
- future QC, eval, visual validation, or evidence-saving code

Do not use old run outputs for this review. Every review must create fresh
`modelcmp-*` run IDs and report those IDs explicitly.

## Required Model Matrix

Use the fixed sample image:

- `/data1/jianf/新提取pdf/180data/0013807667_2023_10_15_3.png`

Use the gold file:

- local source: `C:\Users\lenovo\Desktop\图像金标准\0013807667_2023_10_15_3_result.json`
- remote review path: `/tmp/0013807667_2023_10_15_3_gold.json`

The review matrix is:

- `Qwen3-VL-32B`: run three times for repeatability.
- `Qwen2.5-VL-72B`: larger-reference comparison.
- `Qwen2.5-VL-32B`: medium baseline.
- `Qwen3-VL-8B`: fast candidate.

Do not include `Qwen2.5-VL-7B` in future accuracy reviews. It overfills and
cross-fills too aggressively for this task. Do not delete model weights from the
server unless the user explicitly asks for filesystem cleanup.

When starting the full accuracy model review matrix, maximize GPU utilization
instead of using conservative defaults. First inspect active GPU/tmux state and
stop only stale review-owned `modelcmp_*` sessions from prior interrupted runs.
Then pass explicit GPU/TP/DP overrides so the matrix uses all GPUs that are
available or authorized for the review; do not leave large models on only a
small subset of cards by accident. Preserve unrelated long-lived services unless
the current user request authorizes stopping them.

Use `scripts/run_accuracy_model_review.sh` to run the matrix. The script writes
reports under:

- `/data1/jianf-vllm/runs/model_compare_report_<timestamp>/report.md`
- `/data1/jianf-vllm/runs/model_compare_report_<timestamp>/summary.json`

The user has authorized using all GPUs for this review class. The helper script
defaults to non-conflicting GPU choices when an existing long-lived Qwen3-32B
service is already running, but a reviewer may override GPU environment
variables to use all cards when appropriate. Do not stop unrelated long-lived
services unless the current user request authorizes taking all GPUs or stopping
that service.

## Review Report Requirements

The final response after a behavior-affecting change must include:

- fresh run IDs and report path
- model summary table with runtime and total/L/M/R differences
- Qwen3-VL-32B three-run repeatability summary
- M-region error breakdown, especially `入量_静脉用药`, `入量_其他`, `痰_色`,
  `痰_量`, and `管路护理`
- whether differences are `missing`, `overfill`, or `mismatch`
- lessons for the next change

Comparison rules:

- Ignore `_profile`.
- Treat missing keys as equivalent to `null`.
- Do not use bitwise equality of two live model runs as the sole correctness
  signal; report field-level differences.

## Normal Verification

Before model review, run the normal code checks:

```bash
cd /data1/jianf-vllm
/home/jianf/miniconda3/envs/vllm/bin/python -m pytest -q
/home/jianf/miniconda3/envs/vllm/bin/python -m compileall -q icu_vllm tests
bash -n scripts/start_vllm_server.sh
bash -n scripts/run_accuracy_model_review.sh
```
