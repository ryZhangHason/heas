# Multi-Algorithm Contract Invariance — Pre-Specification
**Locked:** 2026-03-28 (before any code execution or result observation)

## Hypothesis

H0: Contract enforcement efficacy (divergence reduction) is invariant to optimizer choice.
H1: Efficacy differs across optimizers.

Expected outcome: **non-significant** Kruskal-Wallis (p > 0.05) = contract is optimizer-invariant.
If significant: report honestly; interpret as boundary condition of the contract guarantee.

## Design

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Optimizers | NSGA-II, MOEA/D, Random search | Span competence levels and topological structures |
| τ levels | [0.05, 0.10, 0.15, 0.20, 0.25, 0.30] | Same as τ-sweep (pre-specified 2026-03-28) |
| n_runs | 20 per optimizer per τ level | 360 total experiment runs |
| n_policies | 12 (Pareto front size) | Same as τ-sweep |
| n_scenarios | 18 (evaluation scenarios) | Same as τ-sweep |
| Arena | MockArena — identical to tau_sweep_boundary.py | Same stochastic environment |

## Optimizer Hyperparameters (locked)

**Random search:** Uniform sampling over (risk, dispersal) ∈ [0,1]²; no selection pressure; n_policies policies returned directly.

**NSGA-II (simplified):**
- Population size: 60
- Objectives: (mean biomass, trajectory entropy) — both maximised
- Non-dominated sort → Pareto front selection by crowding distance
- Evaluation: N_SCENARIOS // 2 = 9 scenarios during optimization
- No crossover/mutation: single-generation selection from initial pool

**MOEA/D (simplified):**
- Weight vectors: n_policies = 12, evenly spaced on [0,1] (λ₁ = i/11, λ₂ = 1 − λ₁)
- Candidate grid: 12 × 12 = 144 candidates over [0.05, 0.95]²
- Scalarization: λ₁ · mean_norm + λ₂ · entropy_norm
- Per-run perturbation: Gaussian noise σ = 0.05 on selected policy coordinates
- Evaluation: N_SCENARIOS // 2 = 9 scenarios during optimization

## Dependent Variable

Primary DV: **divergence_reduction** = ad-hoc_reversal_rate − HEAS_reversal_rate (per run)

Two conditions:
- Semantic: HEAS vs Ad-hoc-Entropy (entropy vs mean — different objective class)
- Syntactic: HEAS vs Ad-hoc-Step (final vs mean — different summary of same objective)

## Primary Statistical Test

**Kruskal-Wallis H-test** (nonparametric; DV ∼ optimizer)
- Groups: random, nsga2, moead
- Significance threshold: α = 0.05 (exploratory — not Bonferroni-corrected; confirmatory tests remain Stage 1/2 family)
- Pass criterion: p > 0.05 at each τ level → contract is optimizer-invariant at that τ

Secondary: One-way ANOVA (parametric check); Cohen's h per optimizer vs τ-sweep baseline.

## Reporting Rule

- Report ALL τ levels regardless of direction
- If any τ level fails (p < 0.05): report as boundary condition, not experiment failure
- No re-tuning of any hyperparameter after observing results
- Per-optimizer Cohen's h values compared against τ-sweep Step and Entropy baselines

## Paper Integration (conditional on results)

If ≥ 4/6 τ levels pass Kruskal-Wallis:
→ Integrate as §5.5 "Algorithm-Invariance Validation" in v0.5
→ Compress §5.1–5.2 ablation by ~0.5pp to stay within 12-page limit
→ Contribution claim stays locked (robustness validation frame, not upgrade)

If < 4/6 τ levels pass:
→ Report as boundary finding; defer to journal; submit v0.4 as-is

## Integrity Statement

No code has been executed at the time of this document's creation.
No results have been observed. All parameters are set independently of outcomes.
Signed: Research Group, 2026-03-28.
