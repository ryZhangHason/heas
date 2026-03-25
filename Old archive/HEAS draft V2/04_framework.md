# Section 4 — The HEAS Framework

## Draft

HEAS is implemented in Python 3.11 and is available open-source. It depends on
DEAP for evolutionary algorithms, NumPy for numerical computation, and SciPy for
statistical utilities. All components are designed to be replaceable: the EA
algorithm, the voting rule, and the statistical estimator can each be swapped
without changing the simulation or metric contract code.

### 4.1 Layered Composition

The fundamental abstraction is the `Layer`, a unit of simulation logic with a
formal four-method contract:

```python
class Layer:
    def step(self) -> None:
        """Advance state by one discrete timestep."""

    def metrics_step(self) -> dict[str, float]:
        """Per-timestep metrics: fed to dashboards and loggers."""

    def metrics_episode(self) -> dict[str, float]:
        """End-of-episode aggregates: fed to EA, tournament, and CI."""

    def reset(self) -> None:
        """Reset to initial conditions for a new episode."""
```

The contract separates *what a layer computes* from *how its outputs are used*.
Any downstream component — EA fitness function, tournament scorer, statistical
analysis — reads the same `metrics_episode()` dictionary using the same key
string. This is the metric contract: the single source of truth enforced by
the interface, not by convention.

Layers compose into **Streams**, named groups of layers that form a coherent
sub-simulation (e.g., prey population dynamics, climate forcing, policy
enforcement). Streams compose into an **Arena**, which orchestrates step
ordering, inter-stream signal routing, and episode-level aggregation.

The naming convention `stream_name.metric_name` (e.g., `agg.mean_biomass`,
`prey.final_prey`) ensures that metric keys remain globally unambiguous
regardless of how many streams the Arena contains.

### 4.2 Why Hierarchy Matters

Existing ABM frameworks represent agents as flat objects sharing a global
model state. When a researcher adds climate forcing, spatial fragmentation,
and an aggregation layer to a predator-prey model, these appear as attributes
of the Mesa `Model` class — invisible to the framework and therefore impossible
to reuse, test in isolation, or compose into a new study.

In HEAS, the same model is a 5-stream Arena:

```
EcoArena
 ├── ClimateStream    — temperature forcing, shock events
 ├── LandscapeStream  — spatial fragmentation, patch quality
 ├── PreyStream       — logistic growth, dispersal
 ├── PredStream       — predation, mortality
 └── AggStream        — cross-stream aggregator
      → agg.mean_biomass, agg.cv, agg.extinct
```

Each stream can be developed, validated, and replaced independently.
Swapping the climate model (stochastic shock → AR(1) process) requires
only modifying `ClimateStream.step()` — the EA, tournament, and AggStream
see no change because they interact only through the metric contract.

### 4.3 Native Multi-Objective EA Integration

HEAS provides `run_optimization_simple()`, a single-call wrapper that
connects DEAP's NSGA-II to any objective function defined via the metric
contract:

```python
result = run_optimization_simple(
    objective_fn=eco.trait_objective,   # reads agg.mean_biomass, agg.cv
    n_genes=2,
    gene_bounds=[(0.0, 1.0), (0.0, 1.0)],
    pop_size=20,
    n_generations=10,
    seed=42,
)
# result["hof_fitness"]  — Pareto front (list of objective tuples)
# result["hv"]           — hypervolume indicator
# result["log"]          — per-generation statistics
```

The wrapper handles DEAP's creator/toolbox registration, crossover and
mutation wiring, hallof-fame management, and hypervolume computation.
A researcher adding NSGA-II to a new simulation writes only the objective
function — typically 5–10 lines reading from `run_many()` results —
and calls `run_optimization_simple()`. No DEAP knowledge is required.

`run_many()` executes `n_episodes` of the simulation in parallel using
`ProcessPoolExecutor`, with per-episode seeds derived deterministically
from a base seed. The same base seed always produces the same evaluation
result, making individual fitness function calls reproducible.

### 4.4 Tournament Evaluation

Comparing candidate policies is formalized as a Tournament: a cross product
of participants and scenarios, evaluated for `n_episodes` each, aggregated
using one of four voting rules.

```
Tournament(
  participants = [champion, reference, contrarian],
  scenarios    = [8 fragmentation × shock combinations],
  n_episodes   = 50,
  voting_rule  = argmax | majority | borda | copeland
)
```

**Argmax**: the participant with the highest total score across all episodes.
**Majority voting**: for each (participant_i, participant_j) pair, the winner
of more than half the episodes wins the pairwise contest; the participant
winning the most pairwise contests is declared overall winner.
**Borda count**: each participant receives points equal to the number of
other participants they beat in each episode; totals are summed.
**Copeland**: pairwise win/loss matrix; participant with most net wins wins.

HEAS reports the **agreement matrix** — the fraction of (scenario, repeat)
pairs where each pair of voting rules selects the same winner — and the
**sample complexity curve** P(correct winner) as a function of n_episodes.
A Kendall's τ vs. noise level (σ) curve quantifies ranking stability under
measurement perturbation, establishing reliability bounds.

### 4.5 Statistical Infrastructure

`heas/utils/stats.py` provides:
- `summarize_runs(values)` — mean, std, median, BCa bootstrap 95% CI
- `wilcoxon_test(a, b)` — two-sample Wilcoxon signed-rank test
- `cohens_d(a, b)` — effect size
- `kendall_tau(ranking_a, ranking_b)` — rank correlation with bootstrap CI

`heas/utils/pareto.py` provides:
- `hypervolume(pareto_front, ref_point)` — DEAP-backed HV computation
- `auto_reference_point(fronts)` — reference point from dominated nadir

These utilities are used by all experiment scripts (`eco_stats.py`,
`ent_stats.py`, `tournament_stress.py`) and require no configuration —
they accept lists of floats and return structured dicts.

---

## Writing Notes

### Code snippet placement
Two code snippets belong in the paper text:
1. The Layer contract (4 methods) — ~10 lines, small enough to fit inline
2. The `run_optimization_simple()` call — 8 lines, fits inline
Both are more convincing than any prose description.

### Figure placement
The Arena diagram (stream graph) should be Figure 1.
Keep it simple — ASCII style works for WSC proceedings format.
Do NOT try to show eco and enterprise in the same figure — too busy.

### 4.1 vs 4.2 balance
Section 4.1 explains *what* the Layer is.
Section 4.2 explains *why it matters* (vs Mesa flat model).
This two-part structure is important: reviewers who know Mesa will
appreciate the explicit contrast; those who don't will understand the
abstraction from §4.1 alone.

### Avoid implementation minutiae
Don't describe `__init__` signatures, type hints, inheritance — this is not
a software documentation section. Keep it at the design level.

### The "pluggable EA" point
Add one sentence: "The EA algorithm is itself replaceable — `run_ea()` also
accepts CMA-ES and single-objective hillclimbing, and our ablation study
shows simple hillclimbing outperforms NSGA-II on a 2-gene landscape,
confirming that algorithm-agnosticism is not just an architectural claim
but a practical benefit (§5.4)."

This pre-empts the reviewer who might say "why NSGA-II specifically?"

### Page budget: 2.5 pages
Current draft: ~700 words = ~1.0 page. Need ~1.5 more pages.
Add:
- Parallelism paragraph (ProcessPoolExecutor, n_jobs)
- Seed management paragraph (per-run seeding, determinism)
- Short paragraph on extensibility (adding layers to existing Arena)
