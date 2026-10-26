#!/usr/bin/env python3
"""Run the frozen one-seed MCC-E ShapeX training and full saliency evaluation."""

from pathlib import Path

from omegaconf import OmegaConf

from exp_saliency_general import ShapeXPipline


root = str(Path.cwd())
config = OmegaConf.create({
    "base": {"root_dir": root},
    "dataset": {"name": "mcce", "meta_dataset": "default"},
    "mcce": {"num_classes": 2, "seq_len": 1400, "proto_len": 100, "num_prototypes": 2},
})
pipeline = ShapeXPipline(config)
pipeline.args.is_training = 1
pipeline.args.saliency = True
pipeline.args.train_epochs = 10
pipeline.args.itr = 1
pipeline.args.seed = 41
pipeline.args.num_workers = 1
pipeline.train_shapex()
pipeline.eval_shapex()
