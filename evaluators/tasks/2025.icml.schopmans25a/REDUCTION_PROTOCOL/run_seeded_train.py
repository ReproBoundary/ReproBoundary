#!/usr/bin/env python3
"""Seeded wrapper for the unmodified official TA-BG Hydra entrypoint."""

import os
import random
import runpy
import sys
from pathlib import Path

import numpy as np
import torch


SEED = 0
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

project_root = Path(__file__).resolve().parents[1]
entrypoint = project_root / "annealed_bg" / "train.py"
os.chdir(project_root / "annealed_bg")
sys.path.insert(0, str(project_root))
sys.argv[0] = str(entrypoint)
runpy.run_path(str(entrypoint), run_name="__main__")
