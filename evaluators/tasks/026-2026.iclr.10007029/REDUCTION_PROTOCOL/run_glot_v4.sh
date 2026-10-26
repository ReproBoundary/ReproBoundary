#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
WANDB_MODE=offline python3 diagnostic_stress_test.py \
  --model_name_or_path bert-base-uncased \
  --seed 0 \
  --num_train_samples 1000 \
  --num_eval_samples 2000 \
  --max_length 256 \
  --distractor_ratio 0.9 \
  --signal_position random \
  --relational_distance 10 \
  --epochs 3 \
  --batch_size 32 \
  --eval_batch_size 64 \
  --lr 0.0001 \
  --pooling_method glot \
  --gat_hidden_dim 64 \
  --scorer_hidden 128 \
  --num_layers 2 \
  --tau 0.6 \
  2>&1 | tee logs/glot-v4.log
python3 REDUCTION_PROTOCOL/extract_glot_metric.py \
  logs/glot-v4.log artifacts/glot-bert-diagnostic-90pct.json
