#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs checkpoints/sppo-v4
bash run_scripts/run_ds1.5B_PPO_SEQUENCE_shuffle.sh \
  "data.train_files=['data/deepscaler-math-v4-512.parquet']" \
  "data.val_files=['data/offline_eval/math__math_500.parquet']" \
  data.train_batch_size=32 \
  data.seed=20260903 \
  actor_rollout_ref.actor.ppo_mini_batch_size=16 \
  actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1 \
  critic.ppo_mini_batch_size=16 \
  critic.ppo_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.actor.optim.total_training_steps=32 \
  actor_rollout_ref.rollout.val_kwargs.n=16 \
  trainer.n_gpus_per_node=1 \
  trainer.logger='["console"]' \
  trainer.default_local_dir=checkpoints/sppo-v4 \
  trainer.val_before_train=False \
  trainer.test_freq=32 \
  trainer.save_freq=32 \
  trainer.total_training_steps=32 2>&1 | tee logs/sppo-v4.log
python3 REDUCTION_PROTOCOL/extract_sppo_metric.py \
  logs/sppo-v4.log artifacts/math500-average16.json
