#!/usr/bin/env python3
"""Run the released Phy-SSM trainer with the frozen 80-epoch budget."""

from argparse import Namespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

import pissm_train
from config import load_pissm_train_config


args = Namespace(
    num_epochs=None,
    mini_batch_size=None,
    seed=14,
    seq_len=None,
    delta_t=None,
    data_path=None,
    norm=None,
    learning_rate=1e-3,
    weight_decay=0.01,
    patience=100,
    model="pendulum_friction",
    dropout=0.1,
    saving_epoch=None,
    kl_annealing_epochs=None,
    kl_start_af=None,
    kl_end_af=None,
    train_countries=None,
    val_countries=None,
    test_countries=None,
    checkpoints_dir="checkpoints/",
    cpu=False,
    resume=False,
    evaluate_only=False,
)
args = load_pissm_train_config(args)
args.num_epochs = 80
args.seed = 14
args.checkpoints_dir = f"checkpoints/{args.model}/PISSM/"
pissm_train.os.makedirs(args.checkpoints_dir, exist_ok=True)
pissm_train.train(args)
