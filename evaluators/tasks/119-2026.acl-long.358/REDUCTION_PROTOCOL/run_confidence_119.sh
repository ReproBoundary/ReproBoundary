#!/usr/bin/env bash
set -euo pipefail
python3 REDUCTION_PROTOCOL/prepare_train_subset.py \
  --source data/training_data/numina_cot_2k.jsonl \
  --manifest REDUCTION_PROTOCOL/numina_train_500_seed42.jsonl \
  --output artifacts/119/numina_train_500_seed42.jsonl
python3 src/python_scripts/confidence_anno.py \
  --model-path Qwen/Qwen2.5-7B-Instruct \
  --model-revision a09a35458c702b33eeacc393d103063234e8bc28 \
  --data-file artifacts/119/numina_train_500_seed42.jsonl \
  --output-file artifacts/119/numina_train_500_seed42_qwen25_confidence.jsonl \
  --max-samples 500 --prompt-type qwen25 --max-len 2048
