
from __future__ import annotations
from typing import List, Tuple
import torch

def flatten_params(module: torch.nn.Module) -> torch.Tensor:
    """Flatten module parameters to a 1D tensor."""
    vec = []
    for p in module.parameters():
        vec.append(p.detach().reshape(-1))
    return torch.cat(vec) if vec else torch.empty(0)

def unflatten_params(module: torch.nn.Module, vector: torch.Tensor) -> None:
    """Load flattened params back into the module in place."""
    idx = 0
    for p in module.parameters():
        n = p.numel()
        with torch.no_grad():
            p.copy_(vector[idx:idx+n].reshape_as(p))
        idx += n
    if idx != vector.numel():
        raise ValueError("Vector length does not match parameter count.")
