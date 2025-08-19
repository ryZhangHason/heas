
from __future__ import annotations
from typing import Any, Dict, Iterable
import csv, os
from ..utils.io import ensure_dir

class CsvLogger:
    def __init__(self, path: str, fieldnames: Iterable[str]):
        ensure_dir(os.path.dirname(path))
        self.path = path
        self.fieldnames = list(fieldnames)
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def log(self, row: Dict[str, Any]) -> None:
        with open(self.path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow(row)
