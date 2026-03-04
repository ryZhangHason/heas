# Abstract

## FINAL ABSTRACT — WSC submission (≤150 words, single paragraph, no keywords)

Agent-based frameworks provide no native support for the pipeline that policy
research demands: multi-objective evolutionary search, multi-scenario tournament
comparison, and statistically rigorous multi-run validation. Researchers bridge
this gap with bespoke coupling code—100–200 lines per project—that is
non-reusable and prone to silent metric divergence. HEAS (Hierarchical
Evolutionary Agent-based Simulation) eliminates this overhead through four
architectural commitments: a Layer/Stream/Arena composition model; a uniform
metric contract consumed identically by the evolutionary algorithm, tournament
scorer, and bootstrap CI pipeline; native NSGA-II integration with Pareto front
output and hypervolume tracking; and a Tournament primitive with four voting
rules, sample complexity certification, and noise stability analysis. Against a
competent Mesa 3.3.1 reimplementation of an ecological model, HEAS requires 5
lines of coupling code versus 160 (97% reduction). Two case studies validated
across 30 independent runs confirm framework correctness and reproducibility.

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
