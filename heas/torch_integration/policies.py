
from __future__ import annotations
from typing import Optional, Tuple
import torch
from torch import nn

class MLPPolicy(nn.Module):
    """Simple MLP policy with configurable hidden sizes.

    Use with continuous or discrete heads in your project as needed.
    """
    def __init__(self, in_dim: int, out_dim: int, hidden: Tuple[int, ...]=(64,64), activation: nn.Module=nn.ReLU):
        super().__init__()
        layers = []
        last = in_dim
        for h in hidden:
            layers += [nn.Linear(last, h), activation()]
            last = h
        layers.append(nn.Linear(last, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def act(self, obs: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return self.forward(obs)

