# Section 3 — Related Work

## Draft

### 3.1 Agent-Based Simulation Frameworks

**Mesa** (Kazil et al., 2020; v3.3, 2025) is the dominant Python ABM framework,
providing grid and network spaces, agent scheduling, `DataCollector` for
per-step data logging, and `SolaraViz` for browser-based visualization. Mesa is
the right tool for exploratory, spatially-oriented single-run modeling. Its
`DataCollector` is a *pull-based logger* — reporters are declared at
initialization and queried at each step, producing a time-series DataFrame.
This design couples metric collection tightly to the model's internal state:
each downstream consumer (EA, tournament, statistics) must write its own
extraction function, and there is no framework mechanism to verify that these
functions compute the same quantity. Mesa provides `batch_run` for parameter
sweeps but no gradient-free optimization or Pareto front output. HEAS
complements rather than replaces Mesa: for spatial ABMs with rich agent
interactions and visualization needs, Mesa remains the preferred choice.

**NetLogo** (Wilensky, 1999) provides BehaviorSpace for parameter sweeps over a
discrete grid of configurations. BehaviorSpace records reporter values for each
parameter combination, enabling sensitivity analysis. It does not support
continuous gradient-free optimization over gene spaces, produces no Pareto
front, and cannot be used for multi-scenario tournament comparison. NetLogo's
Java-based runtime is not directly composable with Python statistical pipelines.

**Repast4Py** (Collier et al., 2022) targets high-performance distributed ABM
on HPC systems using MPI and GPU acceleration. It provides sophisticated agent
movement and communication primitives but no native support for evolutionary
optimization, tournament evaluation, or statistical CI computation. Repast's
contribution is scalability; HEAS's contribution is composability.

**ABIDES** (Byrd et al., 2020) provides a financial market simulation framework
with message-passing agent interactions calibrated to real exchange data. It
is domain-specific and not designed for policy parameter optimization or
multi-scenario comparison.

### 3.2 Optimization over Simulations

**SimOpt** (Pasupathy and Henderson, 2011; Hong et al., 2015) provides a
testbed of simulation optimization problems and comparison of gradient-free
algorithms, but does not provide an ABM runtime or tournament evaluation.

**PyGMO / Pagmo** (Biscani and Izzo, 2020) provide high-performance
multi-objective optimization with population-based algorithms. They accept
any Python callable as the objective function, making them compatible with
Mesa simulations — but this integration must be written by hand for each
project, reproducing the coupling code that HEAS eliminates.

**Optuna** (Akiba et al., 2019) and similar hyperparameter optimization
frameworks support simulation objectives but are designed for single-objective
or multi-run Bayesian optimization, not multi-objective Pareto search with
tournament evaluation.

**DEAP** (Fortin et al., 2012), which HEAS uses internally, provides
population-based evolutionary algorithms including NSGA-II. DEAP requires the
user to define the fitness function, individual representation, and all
operator wiring. HEAS wraps DEAP's NSGA-II with per-run seeding, parallel
episode evaluation, Pareto front extraction, and hypervolume tracking,
exposing a single-call interface (`run_optimization_simple()`) that requires
no DEAP knowledge.

### 3.3 Policy Search in Agent-Based Models

Several domain-specific works have combined ABMs with evolutionary search:

- Pangallo et al. (2019) apply genetic algorithms to a macroeconomic ABM
  (Mark-0) using custom fitness extraction code — a representative example
  of the coupling code pattern HEAS eliminates.

- Zheng et al. (2022) learn tax policies in the AI Economist using deep RL
  over a multi-agent simulation. This approach requires a differentiable
  simulation or policy gradient estimators; HEAS targets the complementary
  setting where simulation is stochastic, non-differentiable, and
  episodic — gradient-free Pareto search is the appropriate method.

- Caprì et al. (2023) use NetLogo + external Python scripts to evaluate
  transportation policy scenarios, manually maintaining metric consistency
  between the NetLogo reporter and the Python evaluation script — the exact
  divergence risk that HEAS's metric contract prevents.

### 3.4 Gap Summary

| Framework | Hierarchy | Metric Contract | Native EA | Tournament | Repro CI |
|---|---|---|---|---|---|
| Mesa 3.x | ❌ flat | ❌ pull-log | ❌ external | ❌ | ❌ |
| NetLogo | ❌ flat | ❌ reporters | ❌ BehaviorSpace | ❌ | ❌ |
| Repast4Py | ❌ flat | ❌ manual | ❌ external | ❌ | ❌ |
| ABIDES | ❌ message-passing | ❌ | ❌ | ❌ | ❌ |
| PyGMO + Mesa | — | ❌ manual | ✅ external | ❌ | ❌ |
| **HEAS** | ✅ Layer/Stream/Arena | ✅ namespaced | ✅ native NSGA-II | ✅ 4 rules | ✅ bootstrap |

HEAS's contribution is not any one feature in isolation — DEAP already provides
NSGA-II, Mesa already provides agents, scipy already provides bootstrap CI.
The contribution is their *integration under a uniform metric contract* that
eliminates coupling code and prevents metric divergence structurally.

---

## Writing Notes

### Citations needed (fill in before submission)

- Kazil et al. (2020) — Mesa paper: "Utilizing Python for Agent-Based Modeling:
  The Mesa Framework" (WSC 2020) — *already a WSC paper, ideal to cite*
- Wilensky (1999) — NetLogo
- Collier et al. (2022) — Repast4Py paper
- Byrd et al. (2020) — ABIDES
- Fortin et al. (2012) — DEAP: "DEAP: Evolutionary Algorithms Made Easy"
- Biscani and Izzo (2020) — Pagmo2
- Akiba et al. (2019) — Optuna
- Pangallo et al. (2019) — macro ABM + GA
- Zheng et al. (2022) — AI Economist

### Tone guidance for related work
- Be precise, not dismissive. "Mesa is the right tool for spatial ABM" —
  this acknowledges Mesa's strengths and is honest
- Don't say any framework has "limitations" — say what it was designed for
  and what it does not provide
- The gap table should be the punchline of Section 3, not buried

### Length
- Target 0.8 pages. Current draft is long — cut §3.2 to 2–3 sentences each
  for the non-DEAP tools. Keep Mesa and DEAP discussions detailed.

### Positioning sentence (1 sentence at end of section)
"HEAS occupies the intersection of these lines of work: it provides an
ABM runtime with layered hierarchy, connects it to evolutionary search via
a uniform metric contract, and adds tournament evaluation and statistical
CI as framework-level primitives — a combination not available in any
existing tool."
