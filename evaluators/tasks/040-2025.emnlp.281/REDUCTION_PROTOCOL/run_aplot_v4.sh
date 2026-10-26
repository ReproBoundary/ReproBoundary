#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs
cd reward_models
WANDB_MODE=offline python3 run_aplot_reward_models_train.py \
  --base_model google/gemma-2b-it \
  --train_dataset llm-blender/Unified-Feedback \
  --dataset_mode 40k \
  --loss_type bt \
  --weight_ratio 0.5 \
  --num_train_epochs 1 \
  --max_length 1024 \
  --gradient_accumulation_steps 128 \
  --per_device_train_batch_size 1 \
  --per_device_eval_batch_size 1 \
  --learning_rate 2e-6 \
  --attn_implementation eager \
  --seed 20260903 \
  --report_to none \
  --log_dir ../artifacts/aplot-checkpoint \
  --save_strategy epoch \
  2>&1 | tee ../logs/aplot-v4.log
cd ..
python3 REDUCTION_PROTOCOL/extract_aplot_metric.py \
  logs/aplot-v4.log artifacts/aplot-unified-feedback-accuracy.json
