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
    orcid: 0000-0002-0883-4574
    corresponding: true
    affiliation: 1
  - name: Lin Nie
    orcid: 0000-0002-0275-117X
    affiliation: 2
  - name: Xin Zhao
    orcid: 0009-0005-7399-109X
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
building agent-based models, coupling them to evolutionary search, and
evaluating candidate policies through structured arena tournaments. It targets
researchers in computational social science, ecology, and economics who need
to identify robust policy regimes from simulation-based multi-objective search.
The framework is organized around three composable modules---a **hierarchy
runtime** that builds simulations from layered streams, an **evolutionary
tuner** that wraps DEAP [@deap2012] for single- or multi-objective search,
and a **game module** that evaluates policies across scenario ensembles via
configurable voting protocols. A central design principle---the *metric
contract*---ensures that the optimizer, tournament evaluator, and validation
engine all compute the same outcome metric through a single shared callable,
eliminating a class of silent validity threats documented in the accompanying
methodology paper [@zhang2025mad].

# Statement of Need

Agent-based models are increasingly linked to multi-objective evolutionary
algorithms (MOEAs) to search for and rank policy regimes. The standard
workflow couples an ABM simulator to NSGA-II [@deb2002], then validates
winning policies with held-out statistical tests. Three code paths---optimizer,
tournament evaluator, inference engine---must each compute the same outcome
metric, yet general-purpose frameworks such as Mesa [@mesa3_2025] and NetLogo
[@wilensky1999] do not enforce this consistency. When researchers write
coupling code by hand, the paths silently diverge: a controlled experiment
found that 50% of policy rankings reversed depending solely on which path
computed the metric [@zhang2025mad]. This *metric aggregation divergence* does
not raise exceptions---it simply changes which policy wins. The bespoke
coupling code is also substantial: a reference Mesa integration required ~160
lines of scaffolding versus 5 lines with HEAS's metric contract[^1].

[^1]: The 160-line Mesa integration is documented in the accompanying
methodology paper [@zhang2025mad, Section 4.2].

HEAS addresses both problems through its three-module design. The hierarchy
runtime composes layered ABMs without framework-specific boilerplate. The
metric contract provides a single callable shared across all pipeline stages,
making divergence structurally impossible. The game module standardizes
arena and tournament evaluation so researchers can compare policies across
scenario ensembles without custom aggregation logic.

# Software Description

## Hierarchy Runtime

Simulations are built from **layers** and **streams**. Each stream implements
a `step()` method and reads/writes to a shared context dictionary. Layers
group streams and control execution order. This allows arbitrarily complex
agent interactions to be composed from independently testable units.

```python
from heas.hierarchy import LayerSpec, StreamSpec, make_model_from_spec

spec = [
    LayerSpec(streams=[
        StreamSpec(name="climate", factory=ClimateStream,
                   kwargs={"amp": 0.4, "shock_prob": 0.1}),
    ]),
    LayerSpec(streams=[
        StreamSpec(name="ecology", factory=EcologyStream,
                   kwargs={"growth_rate": 0.1}),
        StreamSpec(name="policy", factory=PolicyStream,
                   kwargs={"risk": 0.3, "dispersal": 0.5}),
    ]),
]
model_factory = make_model_from_spec(spec, seed=42)
```

The layer graph is inspectable at runtime: researchers can query which streams
exist, what metrics they produce, and how data flows between layers. A naming
convention (`layer.metric`) ensures globally unambiguous metric keys regardless
of arena size.

## Evolutionary Tuner

The tuner wraps DEAP [@deap2012] for single- or multi-objective evolutionary
search over simulation parameters. NSGA-II [@deb2002] is the default strategy,
with a pluggable `run_ea()` interface for MOEA/D [@zhang2007moead] or custom
algorithms. Parallel episode execution via `ProcessPoolExecutor` accelerates
evaluation, with deterministic per-episode seeds for reproducibility.

```python
from heas.evolution import run_ea
from heas.config import Experiment, Algorithm
from heas.schemas.genes import Real

schema = [
    Real(name="risk", low=0.0, high=1.0),
    Real(name="dispersal", low=0.0, high=1.0),
]

exp = Experiment(model_factory=model_factory, steps=100, episodes=10, seed=42)
algo = Algorithm(objective_fn=fitness, pop_size=50, ngen=20,
                 strategy="nsga2", genes_schema=schema, out_dir="runs/heas")
result = run_ea(exp, algo)
```

A hall-of-fame stores Pareto-optimal solutions, with checkpointing at
configurable intervals for long runs.

## Game Module

The game module defines **scenarios** (parameter configurations), runs
**arenas** (simulation $\times$ scenario cross-products), and aggregates
episode scores through a **tournament** with configurable voting. Four rules
are supported: **argmax**, **majority**, **Borda count**, and **Copeland**
pairwise majority. The choice of voting rule reveals whether rankings are
robust to aggregation method; universal agreement indicates clear dominance,
while disagreement diagnoses competitive structure.

```python
from heas.game import Tournament, make_grid
from heas.schemas.genes import Real

scenarios = make_grid(
    regime=["coop", "compete"],
    base_demand=[80, 120],
    audit_prob=[0.1, 0.3],
)
tournament = Tournament(build_model=my_build_fn)
result = tournament.play(
    scenarios=scenarios, participants=["policy_A", "policy_B"],
    steps=100, episodes=10, seed=42,
    score_fn=score_welfare, voter="majority",
)
```

This separates policy-evaluation logic from search logic, allowing researchers
to inspect which policy wins under which conditions without re-running the
optimizer.

## Web Playground and CLI

HEAS ships a browser-based playground (Pyodide, no backend required) at
<https://ryzhanghason.github.io/heas/> for configuring and running simulations,
inspecting Pareto fronts, and exporting publication-ready bundles. The CLI
provides equivalent batch functionality via `heas run --config config.yaml`
and `heas export` for reproducible bundles.

The project follows open-source best practices with a `CONTRIBUTING.md`
guide, a `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1), and automated
tests (56 functional tests) ensuring reliability.

Source code is available at <https://github.com/ryZhangHason/heas> under the
LGPL-3.0 license, with installation via `pip install heas`. The public
repository metadata and release-facing citation currently point to the arXiv
preprint DOI (<https://arxiv.org/abs/2508.15555>), while the package release
workflow and browser playground provide the practical software access points.

## Software Evidence

The manuscript's central software claims are inspectable in the framework
interfaces shown above rather than only in the companion methodology paper.

| Claim | Inspectable evidence in HEAS |
| --- | --- |
| Shared metric contract across pipeline stages | The hierarchy example defines a reusable `model_factory`, `run_ea()` consumes that factory for search, and `Tournament.play()` accepts the same style of explicit score callable for evaluation. This exposes the contract at the framework boundary rather than in ad-hoc post-processing code. |
| Low-boilerplate coupling | The search example instantiates `Experiment` and `Algorithm` directly from the model factory and gene schema, showing the intended coupling surface in a few lines; the companion paper quantifies the 160-to-5-line reduction against a reference Mesa integration [@zhang2025mad]. |
| Cross-case-study reuse | The case studies below keep the hierarchy, evolution, and tournament interfaces fixed. Only stream definitions, gene schemas, scenarios, and `metrics_episode()` implementations vary across domains. |

## Design Rationale

The three-module architecture reflects a deliberate separation of concerns.
The **hierarchy runtime** isolates simulation logic from optimization logic,
allowing researchers to develop and test ABMs independently of the search
algorithm. The **evolutionary tuner** wraps DEAP rather than reimplementing
evolutionary algorithms, leveraging a battle-tested library while adding
domain-specific integration (deterministic seeds, parallel episode execution).
The **game module** separates policy evaluation from policy search, enabling
researchers to inspect which policies win under which conditions without
re-running the optimizer. The **metric contract** enforces consistency across
all three modules through a single shared callable, making aggregation
divergence structurally impossible rather than relying on developer discipline.

![HEAS Framework Architecture](figures/architecture.png){#fig:architecture}

*Figure 1: HEAS three-module architecture. The Hierarchy Runtime composes simulations from layers and streams, the Evolutionary Tuner performs multi-objective search (NSGA-II/MOEA/D), and the Game Module evaluates policies across scenario ensembles. The Metric Contract ensures all three modules compute the same outcome metric through a single shared callable, eliminating aggregation divergence.*

# Case Studies

Three case studies validate the software interfaces rather than merely the
application domains. Across all three, the hierarchy runtime, evolutionary
tuner, tournament API, and metric-contract boundary remain unchanged; only the
domain-specific stream factories, gene schemas, scenarios, and
`metrics_episode()` definitions are replaced.

**Ecological population management** uses the standard HEAS interfaces to
assemble a predator-prey arena with five streams, a 2-gene policy
(`risk`, `dispersal`), and fragmentation $\times$ shock scenarios. The
important software result is that the same model-construction and evaluation
surface supports both evolutionary search and a held-out 32-scenario
robustness check.

**Enterprise regulatory design** reuses the same framework contracts for a
four-layer regulatory arena with a 4-gene policy
(`tax_rate`, `audit_intensity`, `subsidy`, `penalty_rate`). The domain logic
changes substantially, but the search and tournament wiring do not: the same
interfaces carry a different objective pair, different streams, and a larger
scenario ensemble.

**Wolf-Sheep ODE** keeps the framework interfaces fixed while swapping the
underlying model family from an agent simulation to a mean-field
Lotka-Volterra system. This case is the clearest software portability test:
the 4-layer arena required no additional framework-side coupling beyond a new
`metrics_episode()` implementation, confirming that the contract extends to a
non-Mesa, non-stochastic system with the same HEAS pipeline.

![Ecological Arena Results](figures/pareto_front.png){#fig:pareto}

*Figure 2: Example outputs from the ecological arena case study. Left: Pareto front showing the trade-off between mean biomass (higher is better) and coefficient of variation (lower is better). The star marks the champion policy selected by HEAS. Right: Tournament voting summary showing how different policies perform across scenario conditions, with majority threshold indicated.*

# Evaluation Highlights

A controlled experiment ($n=30$) isolates the metric contract effect by
comparing HEAS to ad-hoc aggregation on an otherwise identical ecological
model. HEAS reduces rank reversals by 50% (Cohen $h=0.215$, a small effect
size per Cohen's conventions)---the HEAS champion wins all 32 held-out
ecological scenarios, a null-safety result that would be uninterpretable
under aggregation divergence. The contract also reduces coupling code by 97%
(160 to 5 lines) relative to a reference Mesa 3.3.1 integration. Cross-domain
validation confirms that the framework composes correctly across ecological,
enterprise, and ODE dynamics without modification. Full methodology and
results are in the accompanying paper [@zhang2025mad].

# Comparison with Similar Tools

Mesa [@mesa3_2025] and NetLogo [@wilensky1999] are the most widely used ABM
frameworks. Mesa is Python-based and extensible but lacks evolutionary search
or structured policy evaluation. NetLogo provides a GUI and large model
library but is not designed for programmatic integration with external
optimizers. AgentPy [@agentpy2021] offers a clean Python API with built-in
parameter sweeping, but without multi-objective evolutionary search or
tournament evaluation. DEAP [@deap2012] is a mature evolutionary computation
library; HEAS uses DEAP internally and adds the ABM runtime, metric contract,
and game module as a unified layer. Among the tools compared here, HEAS is the
only framework that exposes metric-contract enforcement as a first-class
interface spanning optimization, tournament evaluation, and validation, rather
than leaving consistency to project-specific coupling code.

# Acknowledgements

This work was supported by the Department of Politics and Public Administration
at The University of Hong Kong and the Department of Applied Social Sciences
at The Hong Kong Polytechnic University.

# AI Usage Disclosure

The authors used AI-assisted tools (GitHub Copilot, Claude) for code
development and editing. No generative AI tools were used in the
preparation of this manuscript.

# References
