from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_playground_module():
    module_path = Path(__file__).resolve().parents[1] / "py" / "playground.py"
    spec = importlib.util.spec_from_file_location("heas_docs_playground", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load playground module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestPlaygroundRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg = _load_playground_module()

    def test_run_sim_is_deterministic_for_same_seed(self) -> None:
        config = {
            "steps": 6,
            "episodes": 2,
            "seed": 123,
            "layers": [
                [{"name": "L1", "type": "Climate", "params": {"amp": 0.4, "period": 12, "shock_prob": 0.1}}],
                [{"name": "L2", "type": "PreyRisk", "params": {"x0": 40, "r": 0.55, "K": 120, "risk": 0.55, "betaF": 0.3, "gammaV": 0.2}}],
                [{"name": "L3", "type": "Aggregator", "params": {"ext_thresh": 1.0}}],
            ],
        }
        first = self.pg.run_sim(config)
        second = self.pg.run_sim(config)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
