# Section 7 — Conclusion

## Draft

### 7.1 Summary of Contributions

We presented HEAS, a Python framework for hierarchical agent-based simulation
that eliminates the coupling code required to connect simulation dynamics to
multi-objective evolutionary search and tournament-based policy evaluation.
Our four architectural contributions address a gap unmet by existing frameworks:

**C1 — Layered Composition**: The `Layer`/`Stream`/`Arena` triad provides a
formal, composable abstraction for multi-level agent hierarchy. Layers declare
their own state, step logic, and metric contracts; Streams group layers with
shared routing; Arenas orchestrate multi-episode execution. This structure
enables independent testing of subsystems and structural reuse across case
studies without copy-paste proliferation.

**C2 — Uniform Metric Contract**: Every `Layer` exposes `metrics_episode()`
returning `dict[str, float]` with namespaced keys. This single interface is
consumed identically by the EA fitness function, tournament scorer, and
statistical CI pipeline — eliminating the three-independent-code-path problem
that makes Mesa-based policy search brittle. Metric additions propagate
automatically to all consumers with no additional synchronization.

**C3 — Native Multi-Objective EA**: `run_optimization_simple()` provides a
single-call interface to NSGA-II with per-run seeding, parallel episode
evaluation, Pareto front output, and hypervolume tracking. The researcher
defines the objective function in terms of the metric contract; all other
infrastructure is provided by the framework.

**C4 — Tournament Evaluation**: The `Tournament` class provides four voting
rules (argmax, majority, Borda, Copeland), sample complexity certification,
and noise stability analysis as framework-level primitives — turning
multi-scenario policy comparison from a bespoke script into a reproducible,
statistically grounded operation.

### 7.2 Empirical Validation Summary

Against a competent Mesa 3.3.1 reimplementation, HEAS reduces coupling code
by 97% (5 lines vs. 160). Adding a second optimization objective requires one
line in one file under HEAS versus six lines across three files in Mesa — with
HEAS providing structural consistency guarantees and Mesa providing none.

Two case studies validated across 30 independent runs each confirm framework
correctness and reproducibility. Tournament evaluation with 4 voting rules
shows 100% agreement under well-separated participants; noise stability analysis
confirms τ > 0.94 for realistic measurement variance levels.

The algorithm ablation demonstrates that HEAS's optimizer-agnostic interface
allows the researcher to select the algorithm appropriate to the search landscape
— simple hillclimbing for 2-gene continuous problems, NSGA-II for higher-dimensional
policy spaces — without any framework modifications.

### 7.3 Limitations

**Sequential episode evaluation**: The current `run_many()` implementation
provides parallel execution via `ProcessPoolExecutor`, but for lightweight ODE
simulations (< 0.01 s/episode), process startup overhead (~9 s) dominates and
parallel evaluation provides no runtime benefit. For agents requiring > 0.1 s
per episode (e.g., spatially explicit ABMs, neural network policies), the
`n_jobs` parameter delivers linear speedup. Researchers using HEAS with
lightweight models should use `n_jobs=1`.

**Grid and spatial simulation**: HEAS is designed for ODE-style and tabular
agent simulations, not spatial grid simulations. For spatially-explicit models
with agent movement, collision, and neighborhood interaction, Mesa remains the
appropriate choice. HEAS's architecture is not a replacement for Mesa's grid
and scheduler infrastructure.

**No online learning or gradient-based optimization**: HEAS targets gradient-free
evolutionary search over episode-level fitness. For differentiable simulation
objectives or online learning with agent feedback loops, reinforcement learning
frameworks (e.g., RLlib, Stable Baselines) are more appropriate. HEAS and RL
frameworks address complementary problem formulations.

**Reference point sensitivity**: Hypervolume computation requires a reference
point that dominates all Pareto front members. The `auto_reference_point()`
utility computes this from the union of all 30 runs' fronts; for single-run
studies, users must specify a reference point manually. This is a known
difficulty in multi-objective benchmarking, not specific to HEAS.

### 7.4 Future Work

**Mesa integration**: The most impactful near-term extension is a
`MesaLayerAdapter` that wraps a Mesa `Model` as a HEAS `Layer`, exposing
`DataCollector` reporters as `metrics_episode()` keys. This would make
HEAS's EA and tournament primitives available to existing Mesa models without
rewriting the simulation code — the best-of-both-worlds architecture for
researchers with existing Mesa investments.

**MLP weight evolution at scale**: The ecological case study includes a
preliminary MLP policy experiment (4-input, 2-output, two hidden layers of 16
units). The 290-dimensional weight space is feasible for NSGA-II with
population 100 and 50 generations, but the computational budget grows linearly
with `n_eval_episodes`. Future work will characterize the scaling curve for
MLP-weight policy search and identify the episode-budget regime where
neural policy search outperforms trait-parameter optimization.

**Adaptive reference point**: The current hypervolume computation requires a
fixed reference point computed post-hoc from all runs. A streaming reference
point estimator that adapts across generations would enable online hypervolume
tracking during optimization and early stopping when HV converges.

**Tournament scenario generation**: The current `ScenarioSet` is manually
specified by the researcher. Automated scenario generation — covering the
scenario space with a space-filling design (e.g., Latin Hypercube Sampling)
or learned from domain structure — would reduce the scenario specification
burden and improve coverage of edge cases.

**Distributed execution**: For simulation-heavy policy search (> 1 s/episode,
> 100 population, > 50 generations), the current `ProcessPoolExecutor`-based
parallelism becomes a bottleneck. A Ray or Dask backend for `run_many()` would
extend HEAS to HPC cluster settings without API changes — the framework's
metric contract is already independent of execution topology.

---

## Writing Notes

### Limitations must be honest and specific

WSC reviewers penalize vague limitations ("future work could explore X").
The parallelism limitation (9s startup cost for lightweight ODE models) is a
real limitation discovered during experiments — state it explicitly.
The Mesa grid limitation is real — do not claim HEAS replaces Mesa for spatial
simulations.

### Future work: MesaLayerAdapter is the killer application

If HEAS adopts Mesa models as first-class layers, it becomes the optimization
shell around the existing Mesa ecosystem rather than a competing framework.
This is the positioning that makes HEAS useful to WSC reviewers who already
use Mesa.

### Length: 0.5 pages

Conclusion should be tight. The contributions are already in the introduction;
do not repeat them verbatim. Use the conclusion to:
1. Confirm the contributions were validated (empirical summary paragraph)
2. Be honest about limitations
3. Point to the most impactful future direction (MesaLayerAdapter)

### The word "novel" is banned

Use "four architectural contributions" not "four novel contributions."

### Last sentence of paper

Candidate: "HEAS is available as an open-source Python package at [repo]; the
experiments in this paper are fully reproducible from the experiment scripts
in the repository."

This is important: WSC papers are expected to be reproducible, and stating
this explicitly addresses reproducibility concerns proactively.
