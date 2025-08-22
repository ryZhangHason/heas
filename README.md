# HEAS — Hierarchical Evolutionary Agent Simulation

**HEAS** is a framework for building **hierarchical agent simulations**, running **evolutionary search**, comparing strategies via **scenarios × participants** (arena & tournament), and generating **clean visualizations**.

* **Hierarchy runtime.** Compose simulations from **layers** of **streams**; each stream owns a `step()` and writes to a shared context.
* **Evolutionary tuner.** Single or multi‑objective; hall‑of‑fame and stats out of the box.
* **Game module.** Define scenarios, run arenas, score episodes, and **vote** winners.
* **Torch‑friendly.** Drop in `nn.Module` policies; convenient flatten/unflatten & device helpers.
* **Visualizations.** Plot per‑step traces, Pareto fronts, tournament outcomes, and draw the layer/stream graph.
* **CLI.** One command to run sims, tune, evaluate, play tournaments, and export plots.



![HEAS Architecture](https://ryZhangHason.github.io/images/HEAS_Plot1.png)

*Figure. Abstract Stream–layer Architecture in HEAS.*

---

## Install

```bash
pip install heas
```

---

## Quickstart — 5 minutes

### 1) Minimal hierarchical sim (2 layers, 2 streams)

```python
from typing import Dict, Any
import random

from heas.hierarchy import Stream, StreamSpec, LayerSpec, make_model_from_spec
from heas.config import Experiment
from heas.api import simulate

# Producer: writes price into the shared context
class Price(Stream):
    def __init__(self, name, ctx, start=100.0, drift=0.03, noise=0.05):
        super().__init__(name, ctx)
        self.p=float(start); self.drift=float(drift); self.noise=float(noise)
    def step(self):
        self.p += self.drift + random.gauss(0, self.noise)
        self.ctx.data[f"{self.name}.price"] = self.p
    def metrics_step(self):  return {"price": self.p}
    def metrics_episode(self): return {"final_price": self.p}

# Consumer: reads price and trades a tiny position
class Policy(Stream):
    def __init__(self, name, ctx, alpha=0.05, x_key="L1.price"):
        super().__init__(name, ctx)
        self.alpha=float(alpha); self.key=x_key
        self.pos=0.0; self.pnl=0.0; self.prev=None
    def step(self):
        x = float(self.ctx.data.get(self.key, self.prev if self.prev is not None else 100.0))
        if self.prev is not None:
            sig = x - self.prev
            self.pos += self.alpha * sig
            self.pnl  += self.pos * (x - self.prev)
        self.prev = x
        self.ctx.data[f"{self.name}.pnl"] = self.pnl
    def metrics_step(self):  return {"pos": self.pos, "pnl": self.pnl}
    def metrics_episode(self): return {"final_pos": self.pos, "final_pnl": self.pnl}

# Spec → model_factory → simulate
def spec(alpha=0.05, drift=0.03, noise=0.05):
    return [
        LayerSpec([StreamSpec("L1", Price,  dict(start=100.0, drift=drift, noise=noise))]),
        LayerSpec([StreamSpec("L2", Policy, dict(alpha=alpha, x_key="L1.price"))]),
    ]

def make_model(kwargs: Dict[str, Any]):
    return make_model_from_spec(spec(alpha=kwargs.get("alpha", 0.05),
                                     drift=kwargs.get("drift", 0.03),
                                     noise=kwargs.get("noise", 0.05)),
                                seed=kwargs.get("seed", 123))({})

exp = Experiment(model_factory=make_model, steps=20, episodes=1, seed=123)
sim = simulate(exp)
print(sim["episodes"][0]["episode"])  # {"L1.final_price": ..., "L2.final_pnl": ...}
```

### 2) Evolutionary optimization (single objective)

```python
from heas.schemas.genes import Real
from heas.config import Algorithm
from heas.api import optimize
from heas.agent.runner import run_episode
from heas.hierarchy import make_model_from_spec

# Evolve 'drift' to maximize final PnL → minimize negative PnL
from heas.agent.runner import run_episode
from heas.hierarchy import make_model_from_spec

def objective(genome):
    drift = float(genome[0])
    mf = make_model_from_spec(spec(alpha=0.05, drift=drift, noise=0.05), seed=123)
    out = run_episode(mf, steps=40, seed=123)
    pnl = out["episode"]["L2.final_pnl"]
    return (-pnl,)  # minimize negative PnL

SCHEMA = [Real("drift", -0.05, 0.10)]
algo = Algorithm(objective_fn=objective, genes_schema=SCHEMA, pop_size=16, ngen=4, strategy="nsga2", out_dir="runs/demo")
opt = optimize(Experiment(model_factory=lambda kw: None, steps=1, episodes=1, seed=123), algo)
print("Top solutions:", opt["best"][:3])
```

### 3) Scenarios × participants (Arena & Tournament)

```python
from heas.game import make_grid, Tournament

# Scenarios
a = make_grid({"region": ["A","B"], "gov": ["Central","Federal"]}).scenarios
participants = ["TeamA","TeamB"]

# Build a model from (scenario, participant)
from heas.hierarchy import make_model_from_spec

def build_model(scenario, participant, ctx):
    drift = 0.02 if scenario.params["region"]=="A" else 0.04
    alpha = 0.05 if participant=="TeamA" else 0.08
    return make_model_from_spec(spec(alpha=alpha, drift=drift, noise=0.05), seed=ctx.get("seed", 0))

# Score: final PnL
def score_fn(ep_row, participant):
    return float(ep_row.get("final_pnl", ep_row.get("L2.final_pnl", 0.0)))

T = Tournament(build_model)
play = T.play(a, participants, steps=25, episodes=5, seed=123,
              score_fn=score_fn, voter="argmax")
print(play.per_episode.head())
print(play.votes.head())
```

### 4) Visualize

```python
# pip install matplotlib
from heas.vis import plot_steps, plot_votes_matrix, plot_tournament_overview, plot_architecture

# Per-step traces (faceted by scenario, colored by participant)
plot_steps(play.per_step, x="t", y_cols=["L2.pnl"], facet_by="scenario", hue="participant",
           title="PnL over time by scenario × participant")

# Votes matrix
plot_votes_matrix(play.votes)

# Scores (mean ± std) per scenario
plot_tournament_overview(play.per_episode)

# Architecture diagram (from a spec or a live model)
plot_architecture(spec(alpha=0.05, drift=0.03, noise=0.05), edges=[("L1","L2")])
```

---

## Torch policies (optional)

```python
import torch
from torch import nn
from heas.torch_integration.policies import MLPPolicy
from heas.torch_integration.params import flatten_params, unflatten_params
from heas.torch_integration.device import pick_device

DEV = pick_device(prefer_gpu=True)

class TorchPolicy(Policy):
    def __init__(self, name, ctx, policy: nn.Module, x_key="L1.price", pos_scale=0.1):
        super().__init__(name, ctx, alpha=0.0, x_key=x_key)
        self.net = policy.to(DEV)
        self.pos_scale = float(pos_scale)
    def step(self):
        x = float(self.ctx.data.get(self.key, self.prev if self.prev is not None else 100.0))
        if self.prev is not None:
            with torch.no_grad():
                obs = torch.tensor([[x, 1.0]], dtype=torch.float32, device=DEV)
                delta = float(self.net(obs).squeeze().item())
            self.pos += self.pos_scale * delta
            self.pnl += self.pos * (x - self.prev)
        self.prev = x
        self.ctx.data[f"{self.name}.pnl"] = self.pnl

net = MLPPolicy(in_dim=2, out_dim=1, hidden=(16,)).to(DEV)

def spec_torch(noise=0.05):
    return [
        LayerSpec([StreamSpec("L1", Price, dict(start=100.0, drift=0.03, noise=noise))]),
        LayerSpec([StreamSpec("L2", TorchPolicy, dict(policy=net, x_key="L1.price", pos_scale=0.1))]),
    ]
```

---

## CLI cheat sheet

HEAS ships a single executable: `heas`

```bash
# 1) Run a model factory
heas run --factory path/to/module.py:make_model --steps 20 --episodes 2 --seed 123

# 2) Run a graph/spec/model (auto-coerced)
heas run-graph --graph heas.examples.hierarchy_example:make_model --steps 20 --episodes 1

# 3) Evolutionary tuning
heas tune --objective mypkg.objectives:objective --schema mypkg.schemas:SCHEMA \
          --pop 32 --ngen 6 --strategy nsga2 --out runs/demo

# 4) Evaluate genotypes
heas eval --objective mypkg.objectives:objective --genotypes genotypes.json

# 5) Arena (scenarios × participants)
heas arena run \
  --builder mypkg.builders:build_model \
  --scenarios '{"grid":{"region":["A","B"],"gov":["Central","Federal"]}}' \
  --participants "TeamA,TeamB" \
  --steps 20 --episodes 3 --seed 123 --save-dir out/

# 6) Tournament with scoring + voting
heas tournament play \
  --builder mypkg.builders:build_model \
  --scenarios '{"grid":{"region":["A","B"],"gov":["Central","Federal"]}}' \
  --participants ["TeamA","TeamB"] \
  --score mypkg.scoring:score_fn --voter argmax \
  --steps 25 --episodes 5 --seed 123 --save-dir out/

# 7) Visualizations from saved tables/JSON
heas viz steps  --file out/per_step.csv   --x t --facet scenario --hue participant --save out/steps.png
heas viz votes  --file out/votes.csv      --save out/votes.png
heas viz arch   --graph mypkg.graphs:SPEC --save out/arch.png
heas viz log    --file runs/demo/log.json --save out/log.png
heas viz pareto --file runs/demo/pareto.json --title "Pareto" --save out/pareto.png
```

---

## Project layout

```
heas/
  api.py                 # simulate(), optimize(), evaluate()
  config.py              # Experiment, Algorithm, Evaluation
  hierarchy/             # layers, streams, graph & orchestrator
  agent/                 # generic runner utilities (step episodes)
  evolution/             # evolutionary toolbox & algorithms
  game/                  # scenarios, arena, tournament, artifacts, voting
  torch_integration/     # policies, params flatten/unflatten, device helpers
  vis/                   # plotting utilities (steps, votes, Pareto, architecture)
  cli/                   # 'heas' CLI entrypoint
  examples/              # runnable examples
```

---

## Concepts

* **Stream**: A modular process implementing step() and optional metrics_step() / metrics_episode(), using ctx.data.
* **Layer**: An ordered collection of streams; layers execute sequentially.
* **Graph / Model**: The simulation composed of layers, orchestrated with a clock and shared context.
* **Experiment**: Defines the model factory, number of steps, episodes, and RNG seed.
* **Algorithm**: Manages evolutionary search logic, including objectives, gene schemas, and optimization parameters.
* **Arena/Tournament**: Evaluates different participant models across scenarios, with scoring and voting for outcome determination.

### Metric hooks

* `metrics_step(self) -> dict`: per-step metrics (merged into the per-step table).
* `metrics_episode(self) -> dict`: final metrics (merged into the episode summary).

### Seeding & reproducibility

* `Experiment.seed` sets the episode seed.
* Build your own RNGs inside streams if you need independent streams.

---

## Configuration objects

```python
from heas.config import Experiment, Algorithm, Evaluation
```

* **Experiment**: `model_factory`, `steps`, `episodes`, `seed`.
* **Algorithm**: `objective_fn`, `genes_schema`, `pop_size`, `ngen`, `strategy`, `cx_prob`, `mut_prob`, `out_dir`.

  * **Multi‑objective**: set `algo.fitness_weights = (-1.0, -1.0, ...)` to declare objectives (negative = minimize).
* **Evaluation**: batch evaluate a list of genotypes with an objective.

Gene schemas live in `heas.schemas.genes` (e.g., `Real`, `Int`, `Bool`, `Cat`).

---

## Visualizations

`heas.vis` provides ready plots:

* `plot_steps(df, x, y_cols, facet_by, hue)` — per-step traces.
* `plot_tournament_overview(per_episode)` — score bars by scenario.
* `plot_votes_matrix(votes)` — episode winners by scenario.
* `plot_logbook_curves(logbook)` — min/avg/max over generations.
* `plot_pareto_front(points)` — scatter of two objectives.
* `plot_architecture(spec_or_model, edges=None)` — layer/stream diagram.

All functions return a Matplotlib figure.

---

### Citation
If you use **HEAS** in your research, please cite our paper:

Zhang, R., Nie, L., Zhao, X. (2025). HEAS: Hierarchical Evolutionary Agent Simulation Framework for Cross-Scale Modeling and Multi-Objective Search. arXiv preprint arXiv:2508.15555

```bibtex
@article{zhang2025heas,
    title={HEAS: Hierarchical Evolutionary Agent Simulation Framework for Cross-Scale Modeling and Multi-Objective Search},
    author={Zhang, Ruiyu and Nie, Lin and Zhao, Xin},
    journal={arXiv preprint arXiv:2508.15555},
    year={2025},
}
```

---

## License

© 2025. Released under the GNU Lesser General Public License v3.0.  

