#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/results artifacts/predictors logs
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 train_and_eval.py \
  --models qwen-0.6b \
  --datasets scifact \
  --base-data-path data/beir \
  --base-emb-path data/embeddings \
  --base-result-path artifacts/results \
  --save-dir artifacts/predictors \
  --best-hyperparams-file REDUCTION_PROTOCOL/best_hyperparams_v4.json \
  --seed 42 \
  --batch-size 32 \
  --train-ratio 0.9 \
  --hard-negative-topk 1000 \
  --num-negatives 64 \
  --device cuda \
  --overwrite \
  2>&1 | tee logs/learning2select-v4.log
python3 REDUCTION_PROTOCOL/extract_learning2select_metric.py \
  artifacts/results/qwen-0.6b/scifact.json artifacts/learning2select-scifact-ndcg10.json
