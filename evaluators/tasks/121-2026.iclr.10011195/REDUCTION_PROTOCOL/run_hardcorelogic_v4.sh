#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs config
python3 REDUCTION_PROTOCOL/prepare_hardcorelogic_v4.py 2>&1 | tee logs/prepare.log
python3 -c 'import json; from pathlib import Path; Path("config/api.json").write_text(json.dumps({"local":{"type":"openai-vllm","addr":"http://127.0.0.1","ports":[8000],"key":"","proxy":None}}, indent=2)+"\n")'

python3 -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-8B --served-model-name Qwen3-8B --port 8000 \
  --max-model-len 32768 --gpu-memory-utilization 0.90 \
  > logs/vllm.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
python3 -c 'import time,urllib.request
for _ in range(180):
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2); break
    except Exception: time.sleep(2)
else: raise SystemExit("vLLM health check timed out")'

python3 main.py \
  --split hardcore --task hitori --api local --model-type qwen3 --model Qwen3-8B \
  --run-name qwen3-8b-v4 --sample-rep 4 --max-token 32768 --max-comp-token 2048 \
  --temperature 0.6 --seed 19260817 --api-rep 8 \
  2>&1 | tee logs/infer.log
python3 evaluate.py hitori hardcore_qwen3-8b-v4 --rewrite 2>&1 | tee logs/evaluate.log
python3 REDUCTION_PROTOCOL/summarize_hardcorelogic_v4.py \
  eval/hitori/hardcore_qwen3-8b-v4.jsonl METRICS.json
