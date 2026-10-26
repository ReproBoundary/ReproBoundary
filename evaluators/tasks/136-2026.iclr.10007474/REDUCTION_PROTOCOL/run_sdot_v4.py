#!/usr/bin/env python3
"""Run the released CIFAR-10 SDOT solver with the frozen seed."""

import runpy

import torch


torch.manual_seed(0)
torch.cuda.manual_seed_all(0)
runpy.run_path("CIFAR/sdot_compute_CIFAR10.py", run_name="__main__")
