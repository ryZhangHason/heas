
from __future__ import annotations
import random
import numpy as np
import torch

def seed_everything(seed: int=42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        # torch is optional
        pass
