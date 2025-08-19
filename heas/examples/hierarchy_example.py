from __future__ import annotations
from typing import Dict, Any, List
import random

from heas.hierarchy import Stream, StreamSpec, LayerSpec, make_model_from_spec

# ----- Example streams -----

class PriceStream(Stream):
    def __init__(self, name, ctx, start=100.0, drift=0.05, noise=0.1):
        super().__init__(name, ctx, start=start, drift=drift, noise=noise)
        self.p = float(start)
        self.drift = float(drift)
        self.noise = float(noise)

    def step(self):
        self.p += self.drift + random.gauss(0, self.noise)

    def metrics_step(self):
        return {"price": self.p}

    def metrics_episode(self):
        return {"final_price": self.p}

class PolicyABM(Stream):
    def __init__(self, name, ctx, alpha=0.05, price_key="L1.price"):
        super().__init__(name, ctx, alpha=alpha, price_key=price_key)
        self.alpha = float(alpha)
        self.pos = 0.0
        self.pnl = 0.0
        self.prev_price = None
        self.price_key = price_key  # where upstream wrote price in metrics_step

    def step(self):
        # read last step price from context.data or metrics written by upstream
        # fallback: if upstream stream is named "L1", we store price into ctx.data["L1.price"]
        price = self.ctx.data.get(self.price_key)
        if price is None:
            # nothing published yet this step; keep previous price
            price = self.prev_price if self.prev_price is not None else 0.0
        if self.prev_price is not None:
            signal = price - self.prev_price
            self.pos += self.alpha * signal
            self.pnl += self.pos * (price - self.prev_price)
        self.prev_price = price

    def metrics_step(self):
        return {"pos": self.pos, "pnl": self.pnl}

    def metrics_episode(self):
        return {"final_pos": self.pos, "final_pnl": self.pnl}

# ----- Build a spec with two layers: price -> policy -----

def SPEC(drift=0.03, noise=0.05, alpha=0.05):
    return [
        LayerSpec(streams=[
            StreamSpec(name="L1", factory=PriceStream, kwargs=dict(start=100.0, drift=drift, noise=noise)),
        ]),
        LayerSpec(streams=[
            StreamSpec(name="L2", factory=PolicyABM, kwargs=dict(alpha=alpha, price_key="L1.price")),
        ]),
    ]

# ----- Model factory for HEAS Experiment -----

def make_model(kwargs: Dict[str, Any]):
    # allow overrides via kwargs (e.g., passed from heas runner)
    drift = kwargs.get("drift", 0.03)
    noise = kwargs.get("noise", 0.05)
    alpha = kwargs.get("alpha", 0.05)
    spec = SPEC(drift=drift, noise=noise, alpha=alpha)

    # aggregator that also stores L1 price into ctx.data for downstream convenience
    def aggregator(ctx, per_step):
        # publish price under a well-known key so streams can read it in .step()
        if "L1.price" in per_step:
            ctx.data["L1.price"] = per_step["L1.price"]
        out = dict(per_step)
        out["t"] = ctx.t
        out["G.pnl"] = per_step.get("L2.pnl")
        out["G.price"] = per_step.get("L1.price")
        return out

    factory = make_model_from_spec(spec, seed=kwargs.get("seed", 0), aggregator=aggregator)
    return factory(dict())  # build a CompositeHeasModel

# At bottom of hierarchy_example.py

def make_model_instance():
    """Zero-arg convenience: return a ready CompositeHeasModel instance."""
    return make_model({})  # reuse your existing model_factory

GRAPH_SPEC = SPEC()  # if you want to expose the spec directly too