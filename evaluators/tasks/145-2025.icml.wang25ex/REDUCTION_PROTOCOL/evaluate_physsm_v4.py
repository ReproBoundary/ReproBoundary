#!/usr/bin/env python3
"""Compute the released Phy-SSM extrapolation MSE on all held-out trajectories."""

import json
from argparse import Namespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

import torch
import torch.nn.functional as F

import models
from config import load_pissm_train_config
from utils.Base_dataset import create_datasets
from utils import utils


args = Namespace(
    num_epochs=None, mini_batch_size=None, seed=14, seq_len=None, delta_t=None,
    data_path=None, norm=None, learning_rate=1e-3, weight_decay=0.01,
    patience=100, model="pendulum_friction", dropout=0.1, saving_epoch=None,
    kl_annealing_epochs=None, kl_start_af=None, kl_end_af=None,
    train_countries=None, val_countries=None, test_countries=None,
    checkpoints_dir="checkpoints/", cpu=False, resume=False, evaluate_only=True,
)
args = load_pissm_train_config(args)
utils.set_seed(args.seed)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_, _, dataset = create_datasets(args)
loader = torch.utils.data.DataLoader(dataset, batch_size=args.mini_batch_size)
model = models.__dict__["create_pissm_" + args.model]().to(device)
checkpoint_path = Path(f"checkpoints/{args.model}/PISSM/pissm_model_bt.pkl")
checkpoint = torch.load(checkpoint_path, map_location=device)
model.load_state_dict(checkpoint["model"])
model.eval()
weighted_sum = 0.0
element_count = 0
with torch.no_grad():
    for noisy, control, _latent, target, times in loader:
        noisy, control, target, times = (item.to(device) for item in (noisy, control, target, times))
        predicted, *_ = model(noisy[:, :args.seq_len], control, t=times)
        prediction = predicted[:, args.seq_len:, :]
        truth = target[:, args.seq_len:, :]
        weighted_sum += F.mse_loss(prediction, truth, reduction="sum").item()
        element_count += truth.numel()
raw_mse = weighted_sum / element_count
payload = {
    "metric": "extrapolation MSE",
    "unit": "paper table value (x10^-2 MSE)",
    "raw_mse": raw_mse,
    "value": raw_mse * 100.0,
    "test_trajectories": len(dataset),
    "extrapolation_frames": 80
}
destination = Path("artifacts/pendulum-extrapolation-mse.json")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
