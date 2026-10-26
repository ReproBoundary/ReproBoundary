#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/logs
if ! curl --silent --fail http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ollama serve >artifacts/logs/ollama.log 2>&1 &
  ollama_pid=$!
  trap 'kill "$ollama_pid" 2>/dev/null || true' EXIT
  for _ in $(seq 1 60); do
    curl --silent --fail http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi
ollama pull gemma3:4b
python3 REDUCTION_PROTOCOL/run_minds_eye_qwen3b.py

