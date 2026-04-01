from __future__ import annotations
from typing import Any, Optional
import os, json, time

def _ensure(p: str) -> None:
    if p:
        os.makedirs(p, exist_ok=True)

class CheckpointManager:
    """Very small JSON / (optional) torch checkpoint helper."""
    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        _ensure(self.root)

    def save_json(self, obj: Any, name: str) -> str:
        path = os.path.join(self.root, f"{name}.json")
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)
        return path

    def save_torch(self, module_like: Any, name: str) -> Optional[str]:
        try:
            import torch  # noqa
            state = module_like.state_dict()
            path = os.path.join(self.root, f"{name}.pt")
            torch.save(state, path)
            return path
        except Exception:
            return None

    def stamp(self, prefix: str) -> str:
        return os.path.join(self.root, f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}")