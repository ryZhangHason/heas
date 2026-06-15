---
title: 'HEAS: Hierarchical Evolutionary Agent Simulation Framework for Multi-Objective Policy Search'
tags:
  - Python
  - agent-based modeling
  - evolutionary computation
  - multi-objective optimization
  - policy simulation
  - social simulation
authors:
  - name: Ruiyu Zhang
    orcid: 0000-0000-0000-0000  # TODO: replace with real ORCID
    corresponding: true
    affiliation: 1
  - name: Lin Nie
    orcid: 0000-0000-0000-0000  # TODO: replace with real ORCID
    affiliation: 2
  - name: Xin Zhao
    orcid: 0000-0000-0000-0000  # TODO: replace with real ORCID
    affiliation: 2
affiliations:
  - index: 1
    name: Department of Politics and Public Administration, The University of Hong Kong, Hong Kong SAR, China
  - index: 2
    name: Department of Applied Social Sciences, The Hong Kong Polytechnic University, Hong Kong SAR, China
date: 12 June 2026
bibliography: paper.bib
---

# Summary

HEAS (Hierarchical Evolutionary Agent Simulation) is a Python framework for
building agent-based models (ABMs), coupling them to evolutionary search, and
evaluating candidate policies through structured arena tournaments. It also
ships a browser-based Web Playground at
<https://ryzhanghason.github.io/heas/> for interactive simulation without a
local Python installation. HEAS targets researchers in computational social
science, ecology, economics, and organizational science who need to identify
robust policy regimes from simulation-based multi-objective search.

The framework is organized around three composable modules: a **hierarchy
runtime** that builds simulations from layered streams; an **evolutionary
tuner** that wraps DEAP [@deap2012] to run single- or multi-objective search;
and a **game module** that evaluates candidate policies across structured
scenarios and aggregates outcomes through a configurable voting protocol. A
central design principle---the *metric contract*---ensures that the optimizer,
tournament evaluator, and statistical validation engine all compute the same
outcome metric through a single shared callable, eliminating a class of silent
validity threats documented in the accompanying methodology paper
[@zhang2025mad]. HEAS also ships a browser-based playground (Pyodide runtime,
no backend required), a command-line interface for batch workflows, and
reproducible export bundles with full configuration and result metadata.

# Statement of Need

Agent-based models are increasingly used to search for and rank policy regimes
across ecology, economics, and organizational science. The standard workflow
links an ABM simulator to a multi-objective evolutionary algorithm (MOEA)---
typically NSGA-II [@deb2002]---then validates the "winning" policy using
held-out statistical tests. Three separate code paths (optimizer, tournament
evaluator, inference engine) must each compute the same outcome metric from a
simulation run, yet general-purpose ABM frameworks such as Mesa [@mesa2020]
and NetLogo [@wilensky1999] do not enforce consistency across these paths.

When researchers write this coupling code by hand, the three paths silently
diverge: a controlled experiment comparing HEAS to ad-hoc aggregation found
that 50% of policy rankings reversed depending solely on which code path
computed the metric [@zhang2025mad]. This *metric aggregation divergence* is
difficult to detect because it does not raise exceptions---it simply changes
which policy wins. The bespoke coupling code required to link an existing ABM
to an evolutionary optimizer is also substantial: a reference integration
against Mesa 3.3.1 required approximately 160 lines of scaffolding code,
compared to 5 lines when using HEAS's metric contract interface.

Consider a concrete scenario: a public administration researcher wants to
evaluate regulatory tax policies across a multi-firm economy using
evolutionary search. She needs to (1) evolve Pareto-optimal tax regimes
balancing welfare and inequality, (2) compare the evolved regime against
baseline policies across economic scenarios using tournament voting, and
(3) report bootstrap confidence intervals. Each step reads the same welfare
metric, yet in Mesa each is an independent code path---the DEAP fitness
function extracts welfare from the model's DataCollector, the tournament
scorer extracts it from a separate evaluation function, and the CI loop
extracts it from a third data collection loop. Silent divergence can persist
undetected for weeks and invalidate a publication.

HEAS addresses both problems. The hierarchy runtime makes it straightforward
to compose layered ABMs without framework-specific boilerplate. The metric
contract provides a single callable that all pipeline stages share, so
divergence is structurally impossible. The game module standardizes arena and
tournament evaluation so that researchers can compare candidate policies across
scenario ensembles without writing custom aggregation logic.

HEAS is intended for researchers who build simulation-based policy pipelines
and need reproducible, auditable results---particularly in computational social
science, public administration, and ecological modeling.

# Software Description

## Hierarchy Runtime

HEAS simulations are built from **layers** and **streams**. Each stream owns a
`step()` method and reads/writes to a shared context dictionary. Layers group
streams and control execution order. This design allows arbitrarily complex
agent interactions to be composed from independently testable units without
subclassing framework-specific agent classes. The layer graph is inspectable at
runtime: researchers can query which streams exist, what metrics they produce,
and how data flows between layers. A naming convention
(`stream_name.metric_name`) ensures globally unambiguous metric keys regardless
of arena size, so components can be added or removed without breaking downstream
consumers.

## Evolutionary Tuner

The tuner wraps DEAP [@deap2012] to run single- or multi-objective evolutionary
search over simulation parameters. It supports any DEAP-compatible operator set
and exposes a hall-of-fame of Pareto-optimal solutions. Multi-objective search
uses NSGA-II [@deb2002] by default, but the pluggable `run_ea()` interface
allows substitution with MOEA/D [@zhang2007moead] or custom algorithms. The
exploration-exploitation balance is controlled through population size and
mutation parameters, with checkpointing at configurable intervals for long
runs. Parallel episode execution via `ProcessPoolExecutor` accelerates
evaluation, with per-episode seeds derived deterministically for
reproducibility.

## Game Module

The game module defines **scenarios** (parameter configurations), runs
**arenas** (simulation $\times$ scenario cross-products), and aggregates episode
scores through a **tournament** with configurable voting. Four voting rules are
supported: **argmax** (highest mean score wins), **majority** (most-often-best
across episodes), **Borda count** (rank-weighted aggregation), and **Copeland**
(pairwise majority comparison). The choice of voting rule reveals whether
rankings are robust to aggregation method; universal agreement indicates clear
dominance, while disagreement diagnoses competitive structure. This separates
the policy-evaluation logic from the search logic, allowing researchers to
inspect which policy wins under which conditions without re-running the full
optimizer.

## Minimal Example

The following instantiates a two-layer simulation, runs evolutionary search,
and evaluates the best candidate in a two-scenario arena:

```python
from heas.hierarchy import LayerSpec, StreamSpec, make_model_from_spec
from heas.evolution import run_ea
from heas.config import Experiment, Algorithm

# Define a two-layer model
spec = [
    LayerSpec(streams=[StreamSpec(name="ecology", factory=EcologyStream,
                                  kwargs={"growth_rate": 0.1})]),
    LayerSpec(streams=[StreamSpec(name="policy", factory=PolicyStream,
                                  kwargs={"tax_rate": 0.05})]),
]
model_factory = make_model_from_spec(spec, seed=42)

# Configure and run evolutionary search
exp = Experiment(model_factory=model_factory, steps=100, episodes=10, seed=42)
algo = Algorithm(objective_fn=fitness, pop_size=50, ngen=20,
                 strategy="nsga2", genes_schema=schema, out_dir="runs/heas")
result = run_ea(exp, algo)
```

The CLI provides equivalent functionality: `heas run --config config.yaml`
executes a full pipeline from configuration file, and `heas export` generates
a reproducible bundle containing the model specification, evolved parameters,
and all raw results.

## Web Playground and CLI

HEAS ships a browser-based playground (Pyodide runtime, no backend required)
at <https://ryzhanghason.github.io/heas/> that allows researchers to configure
and run simulations, inspect Pareto fronts, compare scenarios, and export
publication-ready bundles without a local Python installation. The CLI provides
equivalent functionality for batch workflows, including reproducible export
with full configuration and result metadata.

# Case Studies

Three case studies validate that HEAS's composable architecture holds across
distinct domain logics. Each uses an independent `metrics_episode()`
implementation; the framework code is shared and unchanged across all three.

**Ecological population management.** A predator-prey arena with a 2-gene
policy (`risk`, `dispersal`) and two objectives (mean biomass, coefficient of
variation). Five streams model climate forcing, landscape quality, prey growth,
predator dynamics, and cross-stream aggregation. Eight
fragmentation$\times$shock scenarios form the evaluation grid. The evolved
champion is subjected to a 32-scenario out-of-distribution robustness test.

**Enterprise regulatory design.** A four-layer regulatory arena with a 4-gene
policy (`tax_rate`, `audit_intensity`, `subsidy`, `penalty_rate`) and two
objectives (total welfare, Gini coefficient). Firms maximize per-step profit
against a stochastic demand schedule; the regulator, government, and welfare
layers implement enforcement, redistribution, and aggregation. The Pareto
trade-off is explored across 32 governance scenarios.

**Wolf-Sheep ODE.** A mean-field Lotka-Volterra formulation parameterized
identically to the canonical Mesa Wolf-Sheep model. The 4-layer arena required
zero additional coupling code beyond the `metrics_episode()` implementation.
This case confirms that the metric contract operates correctly even on narrow
landscapes where evolutionary search provides limited advantage over random
search.

# Evaluation Highlights

A controlled experiment (n=30) isolates the metric contract effect by comparing
HEAS to ad-hoc aggregation on an otherwise identical ecological model. HEAS
reduces rank reversals by 50% relative to ad-hoc aggregation (Cohen
h=0.215)---the HEAS champion wins all 32 held-out ecological scenarios, a
null-safety result that would be uninterpretable under aggregation divergence.
The contract also reduces coupling code by 97% (160 to 5 lines) relative to a
reference Mesa 3.3.1 integration. Cross-domain validation at scale confirms
that the framework composes correctly across ecological, enterprise, and ODE
dynamics without modification. Full experimental methodology and results are
reported in the accompanying paper [@zhang2025mad].

# Comparison with Similar Tools

Mesa [@mesa2020] and NetLogo [@wilensky1999] are the most widely used ABM
frameworks. Mesa is Python-based and extensible but does not include
evolutionary search or structured policy evaluation. NetLogo provides a GUI and
a large model library but is not designed for programmatic integration with
external optimizers. AgentPy [@agentpy2021] offers a clean Python API for
agent-based modeling with some built-in parameter sweeping, but without
multi-objective evolutionary search or tournament evaluation. DEAP [@deap2012]
is a mature evolutionary computation library; HEAS uses DEAP internally and
adds the ABM runtime, metric contract, and game module as a unified layer above
it. No existing framework provides framework-level metric-contract enforcement
that prevents aggregation divergence across optimization, tournament, and
inference stages.

# Acknowledgements

This work was supported by the Department of Politics and Public Administration
at The University of Hong Kong and the Department of Applied Social Sciences
at The Hong Kong Polytechnic University. We thank the HEAS user community for
feedback on earlier versions of the framework.

# References
