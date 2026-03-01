# Abstract

## Draft 1 (submitted version candidate)

Agent-based simulation frameworks such as Mesa and NetLogo excel at modeling
spatially distributed agents but provide no native support for the three-step
pipeline that policy research demands: multi-objective evolutionary search over
agent parameters, multi-scenario tournament comparison of candidate policies,
and statistically rigorous multi-run validation. Researchers connecting these
steps manually write between 100 and 200 lines of coupling code per project —
code that is brittle, non-reusable, and prone to silent metric divergence when
objectives evolve during a study.

We present HEAS (Hierarchical Evolutionary Agent Simulation), a Python
framework that eliminates this coupling overhead through four architectural
commitments: (1) a Layer/Stream/Arena composition model that formalizes
multi-level hierarchy; (2) a uniform metric contract in which every Layer
publishes namespaced metrics consumed identically by the EA, tournament, and
statistical analysis; (3) a native NSGA-II integration that produces Pareto
fronts from any objective defined via the metric contract; and (4) a Tournament
primitive supporting four voting rules with sample complexity and noise
stability certification.

We validate HEAS on two case studies — ecological population management and
enterprise regulatory design — each evaluated across 30 independent runs with
bootstrap confidence intervals. Against a competent Mesa 3.3 reimplementation
of the same ecological model, HEAS requires 5 lines of coupling code where Mesa
requires 160 (97% reduction). Adding a second optimization objective requires
editing one file and one line in HEAS versus three files and six lines in Mesa,
with no structural guarantee of consistency in Mesa and a structural guarantee
in HEAS.

**Keywords**: agent-based simulation, multi-objective optimization, evolutionary
algorithms, simulation framework, policy search, tournament evaluation

---

## Draft 2 (shorter, punchier — for tight word count)

Multi-objective policy search over agent-based simulations requires connecting
simulation dynamics to evolutionary search, multi-scenario tournament
evaluation, and statistical validation — work that researchers currently
implement as bespoke coupling code in each new project.

HEAS (Hierarchical Evolutionary Agent Simulation) provides this pipeline as a
composable framework. Its Layer/Stream/Arena architecture formalizes multi-level
hierarchy; a uniform metric contract ensures that EA fitness, tournament
scoring, and bootstrap confidence intervals all consume the same simulation
output without synchronization code. Native NSGA-II integration and a
four-rule Tournament primitive complete the stack.

Compared to Mesa 3.3 on a matched ecological simulation, HEAS requires 97%
fewer coupling lines (5 vs. 160). Adding a second objective takes one line in
HEAS versus three files in Mesa, with HEAS providing structural consistency
guarantees that Mesa cannot. Two case studies validated across 30 independent
runs each confirm framework correctness and reproducibility.

---

## Draft Notes

- "coupling code" is the key term — define it clearly in intro
- Don't say "eliminates glue code" — "eliminates coupling overhead" is more precise
- The 97% figure is the headline statistic — it needs to appear in abstract
- Keep biological/economic result numbers OUT of abstract — they invite the wrong reading
- "structural guarantee" vs "best practice" — this is the philosophical distinction
  that separates HEAS from "just using Mesa carefully"
