#!/bin/bash
# ==========================================
# vLLM 多卡推理服务器启动脚本（优化版）
# 使用 DP-2 × TP-4 架构最大化吞吐量
# ==========================================

# 配置项 —— 按你的实际环境修改
MODEL_PATH="/data1/bigmodels/qwen2.5-vl-72B"   # HuggingFace 模型路径（本地或远程）
TENSOR_PARALLEL=4                               # 张量并行 GPU 数量（每组 4 卡）
DATA_PARALLEL=2                                 # 数据并行副本数（2 组独立引擎）
PORT=8000                                       # vLLM OpenAI 兼容 API 监听端口
HOST="127.0.0.1"                                # 仅允许本机访问，业务脚本通过 localhost 调用
GPU_IDS="0,1,2,3,4,5,6,7"                       # 可用 GPU

# 限制使用的 GPU
export CUDA_VISIBLE_DEVICES=$GPU_IDS

echo "🚀 启动 vLLM 推理服务器（DP-2 × TP-4 优化模式）..."
echo "   模型: $MODEL_PATH"
echo "   张量并行: $TENSOR_PARALLEL 卡 × 数据并行: $DATA_PARALLEL 组"
echo "   监听地址: $HOST:$PORT"
echo "   GPU: $GPU_IDS"
echo ""

# 启动 vLLM OpenAI 兼容 API 服务器
# --tensor-parallel-size 4:  每组用 4 张 H100 做张量并行（72B FP16 ≈ 144GB，4×80GB 绰绰有余）
# --data-parallel-size 2:    启动 2 个独立推理引擎，各占 4 卡，请求自动负载均衡
# --max-num-seqs 64:         每个引擎同时处理 64 个请求（两组合计可达 128 并发）
# --enable-chunked-prefill:  允许 decode 和 prefill 交错执行，减少 GPU 空闲气泡
# --enable-prefix-caching:   缓存相同 prompt 模板的 KV Cache，避免重复计算
# --gpu-memory-utilization:  提高到 0.92，为更多 KV Cache 腾出空间

python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --tensor-parallel-size $TENSOR_PARALLEL \
    --data-parallel-size $DATA_PARALLEL \
    --host "$HOST" \
    --port $PORT \
    --max-model-len 24576 \
    --max-num-seqs 64 \
    --gpu-memory-utilization 0.92 \
    --trust-remote-code \
    --enable-chunked-prefill \
    --enable-prefix-caching \
    --limit-mm-per-prompt '{"image": 1}' \
    --dtype auto \
    --served-model-name "qwen2.5vl-72b"
