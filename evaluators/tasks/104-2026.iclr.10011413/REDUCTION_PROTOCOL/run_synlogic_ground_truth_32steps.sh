#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts logs checkpoints/qwen-logic-ground-truth-v4
python3 -m src.main_dapo \
  data.train_files=data/synlogic/train_easy_v4_1024.parquet \
  data.val_files=data/synlogic/test_easy.parquet \
  data.prompt_key=prompt \
  data.truncation=left \
  data.max_prompt_length=2048 \
  data.max_response_length=4096 \
  data.gen_batch_size=16 \
  data.train_batch_size=16 \
  +data.seed=20260903 \
  actor_rollout_ref.rollout.n=8 \
  +actor_rollout_ref.rollout.seed=20260903 \
  algorithm.adv_estimator=grpo \
  algorithm.use_kl_in_reward=False \
  algorithm.kl_ctrl.kl_coef=0.0 \
  algorithm.filter_groups.enable=True \
  algorithm.filter_groups.max_num_gen_batches=2 \
  algorithm.filter_groups.metric=seq_final_reward \
  actor_rollout_ref.actor.use_kl_loss=False \
  actor_rollout_ref.model.path=Qwen/Qwen2.5-1.5B \
  actor_rollout_ref.model.use_remove_padding=True \
  actor_rollout_ref.model.enable_gradient_checkpointing=True \
  actor_rollout_ref.actor.optim.lr=1e-6 \
  actor_rollout_ref.actor.optim.lr_warmup_steps=4 \
  actor_rollout_ref.actor.optim.weight_decay=0.1 \
  actor_rollout_ref.actor.ppo_mini_batch_size=8 \
  actor_rollout_ref.actor.use_dynamic_bsz=True \
  actor_rollout_ref.actor.ppo_max_token_len_per_gpu=6144 \
  actor_rollout_ref.rollout.log_prob_use_dynamic_bsz=True \
  actor_rollout_ref.rollout.log_prob_max_token_len_per_gpu=6144 \
  actor_rollout_ref.ref.log_prob_use_dynamic_bsz=True \
  actor_rollout_ref.ref.log_prob_max_token_len_per_gpu=6144 \
  actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
  actor_rollout_ref.rollout.gpu_memory_utilization=0.80 \
  actor_rollout_ref.rollout.max_num_batched_tokens=6144 \
  actor_rollout_ref.rollout.temperature=1.0 \
  actor_rollout_ref.rollout.top_p=1.0 \
  actor_rollout_ref.rollout.top_k=-1 \
  actor_rollout_ref.rollout.val_kwargs.temperature=1.0 \
  actor_rollout_ref.rollout.val_kwargs.top_p=0.7 \
  actor_rollout_ref.rollout.val_kwargs.top_k=-1 \
  actor_rollout_ref.rollout.val_kwargs.do_sample=True \
  actor_rollout_ref.rollout.val_kwargs.n=8 \
  actor_rollout_ref.actor.fsdp_config.param_offload=False \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=False \
  actor_rollout_ref.ref.fsdp_config.param_offload=False \
  reward_model.reward_manager=dapo \
  reward_model.score_type=acc_with_think_format \
  trainer.logger='["console"]' \
  trainer.project_name=Model-Task-Alignment-RL-v4 \
  trainer.experiment_name=qwen15b-logic-ground-truth-32steps \
  trainer.n_gpus_per_node=1 \
  trainer.nnodes=1 \
  trainer.val_before_train=True \
  trainer.test_freq=8 \
  trainer.save_freq=32 \
  trainer.total_training_steps=32 \
  trainer.default_local_dir=checkpoints/qwen-logic-ground-truth-v4 \
  trainer.resume_mode=disable 2>&1 | tee logs/synlogic-ground-truth-v4.log
python3 REDUCTION_PROTOCOL/extract_synlogic_metric.py \
  logs/synlogic-ground-truth-v4.log artifacts/synlogic-easy-accuracy.json \
  artifacts/synlogic-validation-source-counts.json
