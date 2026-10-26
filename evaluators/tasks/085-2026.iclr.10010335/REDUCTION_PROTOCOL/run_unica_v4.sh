#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
DATA_PATH="$PWD/data_v4" WANDB_MODE=offline OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
python3 main.py \
  --model_name ts_adapter/unica \
  --base_model chronos_bolt_base \
  --with_gate --with_future --future_with_gate \
  --datasets mmsp \
  --num_workers 0 \
  --num_batches_per_epoch 20 \
  --max_epochs 10 \
  --indexed_sample --split_val \
  --gradient_clip 0.1 \
  --d_multi_modal 1 \
  --batch_size 8 \
  --lr 1e-6 \
  --seed 20260903 \
  2>&1 | tee logs/unica-v4.log
python3 REDUCTION_PROTOCOL/extract_unica_metric.py \
  results/ts_adapter/unica/normalized_results.csv artifacts/unica-mmsp-mae.json
