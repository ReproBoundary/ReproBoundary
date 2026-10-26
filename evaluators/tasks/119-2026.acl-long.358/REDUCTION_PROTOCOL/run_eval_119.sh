#!/usr/bin/env bash
set -euo pipefail
python3 -u src/Qwen2.5-Math/evaluation/math_eval.py \
  --model_name_or_path artifacts/119/qwen25-7b-instruct-gift-merged \
  --data_names aime24 --data_dir data --output_dir artifacts/119/evaluation \
  --split test --prompt_type qwen25 --num_test_sample -1 --seed 42 \
  --temperature 1 --n_sampling 16 --top_p 1 --max_tokens_per_call 4096 \
  --start 0 --end -1 --use_vllm --save_outputs --overwrite
