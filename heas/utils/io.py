
from __future__ import annotations
import os, json

def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def save_json(path: str, obj) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def load_json(path: str):
    with open(path) as f:
        return json.load(f)
