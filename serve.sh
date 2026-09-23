#!/bin/sh
set -eu

case "${MODEL_PRESET:-qwen}" in
  qwen)
    model=Qwen/Qwen3-4B
    set -- --reasoning-parser qwen3 "$@"
    ;;
  gemma)
    model=google/gemma-3-4b-it
    set -- --limit-mm-per-prompt '{"image":0}' "$@"
    ;;
  mistral)
    model=mistralai/Ministral-3-3B-Instruct-2512-BF16
    set -- --tokenizer-mode mistral --config-format mistral --load-format mistral \
      --limit-mm-per-prompt '{"image":0}' "$@"
    ;;
  *) echo 'MODEL_PRESET must be qwen, gemma, or mistral' >&2; exit 1 ;;
esac

: "${VLLM_API_KEY:?Set VLLM_API_KEY to a nonempty API key}"
exec vllm serve "$model" \
  --host 0.0.0.0 --port 8000 \
  --served-model-name "${MODEL_PRESET:-qwen}" \
  --dtype bfloat16 \
  --max-model-len "${MAX_MODEL_LEN:-4096}" \
  --max-num-seqs "${MAX_NUM_SEQS:-2}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.85}" \
  --enforce-eager "$@"
