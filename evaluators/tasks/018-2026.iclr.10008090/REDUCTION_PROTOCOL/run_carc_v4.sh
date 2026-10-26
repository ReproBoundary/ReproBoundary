#!/usr/bin/env bash
set -euo pipefail

export WANDB_MODE=disabled
mkdir -p data/raw data/split_seed_1860 models/split_seed_1860 artifacts/carc artifacts/wandb artifacts/plots logs

python3 scripts/gen_data.py \
  --data_dir data/raw --plot_freq 0 --num_samples 100000 --max_tries 500 --seed 1860 \
  2>&1 | tee logs/generate.log

python3 scripts/split_data_systematicity.py \
  --data_path data/raw/all_episodes.jsonl --frac_test_compositions 0.2 \
  --min_func_examples 5000 --no_shuffle_study_examples --num_primitives 2 \
  --num_compositions 2 --num_train_samples 4096 --num_test_samples 0 --seed 1860 \
  2>&1 | tee logs/split.log

python3 REDUCTION_PROTOCOL/verify_carc_split.py

python3 scripts/train_mlc.py \
  --data_dir data/split_seed_1860 --data_file_name systematicity_seed_1860 \
  --checkpoint_dir models/split_seed_1860 --wandb_dir artifacts/wandb \
  --wandb_name carc-v4 --plot_dir artifacts/plots --plot_freq 0 \
  --batch_size 200 --nepochs 40 --seed 1860 \
  2>&1 | tee logs/train.log

python3 scripts/eval_mlc_model.py \
  --checkpoint_path models/split_seed_1860/last.ckpt \
  --data_dir data/split_seed_1860 --data_file_name systematicity_seed_1860 \
  --output_dir artifacts/carc --batch_size 200 --test_queries -1 --seed 1860 \
  2>&1 | tee logs/evaluate.log

python3 REDUCTION_PROTOCOL/extract_carc_metric.py artifacts/carc/model_accuracy.json METRICS.json
