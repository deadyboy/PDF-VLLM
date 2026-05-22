#!/bin/bash
# ==========================================
# vLLM 多卡推理服务器启动脚本（优化版）
# 使用 DP-2 × TP-4 架构最大化吞吐量
# ==========================================

# 配置项可通过环境变量覆盖，默认仍是 72B 正式服务。
MODEL_PATH="${MODEL_PATH:-/data1/bigmodels/qwen2.5-vl-72B}"
TENSOR_PARALLEL="${TENSOR_PARALLEL:-4}"
DATA_PARALLEL="${DATA_PARALLEL:-2}"
PORT="${PORT:-8002}"
HOST="${HOST:-127.0.0.1}"
GPU_IDS="${GPU_IDS:-0,1,2,3,4,5,6,7}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5vl-72b}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-24576}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-64}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
LIMIT_MM_PER_PROMPT="${LIMIT_MM_PER_PROMPT:-{\"image\": 1}}"
MM_PROCESSOR_CACHE_GB="${MM_PROCESSOR_CACHE_GB:-}"
GENERATION_CONFIG="${GENERATION_CONFIG:-}"
EXTRA_VLLM_ARGS="${EXTRA_VLLM_ARGS:-}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"

# 限制使用的 GPU
export CUDA_VISIBLE_DEVICES=$GPU_IDS

echo "🚀 启动 vLLM 推理服务器（DP-2 × TP-4 优化模式）..."
echo "   模型: $MODEL_PATH"
echo "   张量并行: $TENSOR_PARALLEL 卡 × 数据并行: $DATA_PARALLEL 组"
echo "   监听地址: $HOST:$PORT"
echo "   GPU: $GPU_IDS"
echo "   OpenMP 线程: $OMP_NUM_THREADS"
echo ""

# 启动 vLLM OpenAI 兼容 API 服务器
# --tensor-parallel-size 4:  每组用 4 张 H100 做张量并行（72B FP16 ≈ 144GB，4×80GB 绰绰有余）
# --data-parallel-size 2:    启动 2 个独立推理引擎，各占 4 卡，请求自动负载均衡
# --max-num-seqs 64:         每个引擎同时处理 64 个请求（两组合计可达 128 并发）
# --enable-chunked-prefill:  允许 decode 和 prefill 交错执行，减少 GPU 空闲气泡
# --enable-prefix-caching:   缓存相同 prompt 模板的 KV Cache，避免重复计算
# --gpu-memory-utilization:  提高到 0.92，为更多 KV Cache 腾出空间

ARGS=(
    --model "$MODEL_PATH"
    --tensor-parallel-size "$TENSOR_PARALLEL"
    --data-parallel-size "$DATA_PARALLEL"
    --host "$HOST"
    --port "$PORT"
    --max-model-len "$MAX_MODEL_LEN"
    --max-num-seqs "$MAX_NUM_SEQS"
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
    --trust-remote-code
    --enable-chunked-prefill
    --enable-prefix-caching
    --limit-mm-per-prompt "$LIMIT_MM_PER_PROMPT"
    --dtype auto
    --served-model-name "$SERVED_MODEL_NAME"
)

if [ -n "$MM_PROCESSOR_CACHE_GB" ]; then
    ARGS+=(--mm-processor-cache-gb "$MM_PROCESSOR_CACHE_GB")
fi

if [ -n "$GENERATION_CONFIG" ]; then
    ARGS+=(--generation-config "$GENERATION_CONFIG")
fi

if [ -n "$EXTRA_VLLM_ARGS" ]; then
    # shellcheck disable=SC2206
    ARGS+=($EXTRA_VLLM_ARGS)
fi

python -m vllm.entrypoints.openai.api_server "${ARGS[@]}"
