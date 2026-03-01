# Section 2 — Introduction

## Draft

Agent-based models (ABMs) have become a primary tool for studying emergent
behavior in complex adaptive systems — from ecological communities and financial
markets to public health interventions and regulatory policy design. The appeal
is clear: ABMs can represent heterogeneous actors, local interactions, and
nonlinear feedback in ways that equation-based models cannot. But using an ABM
for *policy search* — finding the configuration of agent parameters or
institutional rules that optimizes a multi-dimensional objective — requires
infrastructure that no general-purpose ABM framework currently provides.

### 1.1 The Coupling Code Problem

Consider a researcher using Mesa to study regulatory policy in a multi-firm
economy. She wants to (1) evolve a Pareto-optimal tax regime using NSGA-II,
(2) compare the evolved regime against a reference policy across 32 independent
economic scenarios using tournament voting, and (3) report 30-run bootstrap
confidence intervals to establish statistical credibility.

Each of these three steps requires reading simulation output — specifically,
the same welfare metric computed by the same model. Yet in Mesa, each step is
an independent code path:

- The **DEAP fitness function** extracts welfare from the model's `DataCollector`
  after the run
- The **tournament scorer** extracts welfare from a separate episode-evaluation
  function, possibly using different aggregation (mean vs. final value)
- The **bootstrap CI** extracts welfare from a third data collection loop

When the researcher decides to add a second objective — say, inequality of
welfare distribution — she must edit the `DataCollector` reporter, the DEAP
fitness function, the tournament scorer, and the CI extraction loop, keeping
all four in sync manually. The framework provides no enforcement. A silent
divergence — the EA uses mean welfare while the tournament uses final-step
welfare — can persist undetected for weeks and invalidate a publication.

This pattern, which we call *coupling code*, appears in every ABM-based policy
search project we are aware of. It is not a failure of Mesa or NetLogo — these
frameworks were designed for exploratory, single-run agent modeling. But as
ABMs are increasingly deployed for *optimization and evaluation* tasks, the
coupling code burden has become a significant source of research friction,
reproducibility failures, and silent bugs.

### 1.2 What Existing Frameworks Provide

Mesa 3.x provides `DataCollector` for per-step logging, `batch_run` for
parameter sweeps, and `SolaraViz` for browser-based visualization. It has no
native support for multi-objective EA, Pareto front output, tournament voting,
or bootstrap CI.

NetLogo's BehaviorSpace supports grid-based parameter sweeps, not continuous
gradient-free optimization. Its reporting mechanism is tightly coupled to the
NetLogo runtime and cannot be consumed by external statistical tools without
custom export scripts.

Repast4Py targets high-performance distributed ABM on HPC clusters. It provides
no EA integration or tournament evaluation, and its metric collection requires
manual logging code.

ABIDES, designed for financial market simulation, provides agent message-passing
but no policy search infrastructure and is domain-specific in its abstractions.

### 1.3 Our Contributions

We present **HEAS** (Hierarchical Evolutionary Agent Simulation), a Python
framework that addresses the coupling code problem through four architectural
commitments:

**C1 — Layered Composition**: The `Layer`/`Stream`/`Arena` triad formalizes
multi-level hierarchy as a first-class abstraction. Layers declare what they
own; Streams declare how they couple. This makes hierarchy visible to the
framework, enabling reuse and independent testing that monolithic Mesa `Model`
classes cannot support.

**C2 — Uniform Metric Contract**: Every `Layer` implements `metrics_episode()`,
returning a `dict[str, float]` of namespaced keys (e.g., `agg.mean_biomass`).
This dict is the *single source of truth* consumed identically by the EA
fitness function, tournament scorer, and statistical CI pipeline. Adding a
metric is a one-line change in one file, propagating to all consumers with no
additional synchronization.

**C3 — Native Multi-Objective EA**: `run_optimization_simple()` wraps DEAP's
NSGA-II with per-run seed management, parallel episode evaluation, Pareto front
output, and hypervolume tracking. The connection to the simulation uses the
metric contract, not ad-hoc state extraction.

**C4 — Tournament Evaluation**: The `Tournament` class implements four voting
rules (argmax, majority, Borda, Copeland), sample complexity certification, and
noise stability analysis as first-class operations — turning comparative policy
evaluation from a bespoke script into a reproducible, statistically-certified
primitive.

### 1.4 Paper Organization

Section 2 surveys related work. Section 3 describes the HEAS framework
architecture. Section 4 presents two case studies demonstrating composability
across structurally different domains. Section 5 reports experimental evaluation
including a direct Mesa comparison, 30-run reproducibility studies, and
tournament validation. Section 6 concludes.

---

## Writing Notes

### Paragraph on "coupling code" — make this concrete
The 160 vs 5 LOC comparison belongs in the introduction (as a forward reference),
not held until Section 5. WSC reviewers decide in the first two paragraphs
whether the paper addresses a real problem. The coupling code problem must be
*vivid* — a concrete scenario with named steps is better than an abstract claim.

### Don't say "novel"
WSC reviewers deduct for "our novel framework" style claims. Instead: describe
the architectural decision and let the contrast with Mesa speak for itself.

### The word "glue code" is informal — use "coupling code" or "integration overhead"

### Framing of case studies
In the intro, case studies should be described as *validation vehicles*:
"We demonstrate HEAS's composability on two case studies that differ
structurally — one with stochastic spatial dynamics, one with multi-stakeholder
economic interactions — not as domain models making scientific claims about
ecology or economics."

This pre-empts the reviewer who asks "is the ecological model biologically
realistic?" Answer: it doesn't need to be. It's a composition demonstration.

### Page budget for intro: 1.0 pages
Current draft is ~800 words = ~1.0 page at IEEE single-column. Good.
May need to cut §1.2 to ~3 sentences each if tight.

### First sentence options (hook alternatives)

Option A (problem-first):
"Every simulation-based policy search project rewrites the same infrastructure:
fitness extraction, tournament scoring, and statistical CI — three independent
code paths maintaining the same metric by hand."

Option B (contrast-first):
"Mesa and NetLogo have made agent-based modeling accessible to thousands of
researchers. Making those models the substrate for rigorous multi-objective
policy search remains, in 2026, an exercise in bespoke integration."

Option C (quantitative-first, bold but risky):
"160 lines of coupling code — that is the overhead a competent Mesa programmer
writes to connect a predator-prey simulation to NSGA-II, tournament comparison,
and bootstrap confidence intervals. HEAS reduces this to 5 lines."

**Recommendation**: Option C for a conference paper audience (engineers who
appreciate concrete numbers), softened to Option A if reviewers are more
theoretically inclined. Use Option C.
