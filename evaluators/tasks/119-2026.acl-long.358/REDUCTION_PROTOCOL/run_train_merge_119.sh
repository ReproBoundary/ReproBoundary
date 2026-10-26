#!/usr/bin/env bash
set -euo pipefail
python3 src/python_scripts/qwen25_gift_2k.py \
  --mode gift --model_max_length 2048 --per_device_train_batch_size 4 \
  --global_batch_size 64 --learning_rate 2e-4 --num_train_epochs 1 \
  --model_name_or_path Qwen/Qwen2.5-7B \
  --model_revision d149729398750b98c0af14eb82c78cfe92750796 \
  --data_path artifacts/119/numina_train_500_seed42_qwen25_confidence.jsonl \
  --output_dir artifacts/119/qwen25-7b-gift-adapter
python3 src/python_scripts/merge_adapter_to_base_model.py \
  --base_model Qwen/Qwen2.5-7B-Instruct \
  --base_revision a09a35458c702b33eeacc393d103063234e8bc28 \
  --adapter artifacts/119/qwen25-7b-gift-adapter \
  --output_path artifacts/119/qwen25-7b-instruct-gift-merged
