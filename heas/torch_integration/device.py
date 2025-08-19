
from __future__ import annotations
import random, os
import numpy as np
import torch
from contextlib import contextmanager

def pick_device(prefer_gpu: bool=True) -> torch.device:
    if prefer_gpu and torch.cuda.is_available():
        return torch.device("cuda")
    if prefer_gpu and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def seed_torch(seed: int=42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

@contextmanager
def autocast_enabled(device: torch.device):
    if device.type == "cuda":
        with torch.cuda.amp.autocast():
            yield
    else:
        # no-op
        yield
