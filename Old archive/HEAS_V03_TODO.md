# HEAS v0.3 TODO LIST
**Produced by Research Group (10-round, 2-meeting session)**
**Date:** 2026-03-26
**Status:** CONDITIONALLY APPROVED by Supervisor

---

## SUPERVISOR'S 3 CONDITIONS BEFORE WORK BEGINS
1. Draft concrete examples of dispatch signature validation (for §3) BEFORE writing
2. Agree on noise-reporting plan for τ-sweep BEFORE running experiments
3. Get abstract approved by group lead BEFORE rewriting §1.2

---

## CRITICAL (blocks submission)

**TASK C1 — ABSTRACT: Problem-first reframe**
- Section: Abstract (≤150 words)
- Change: Open with problem (silent aggregation divergence as structural risk), not tool description
- Remove: "Wolf-Sheep mean-field reimplementation of a published Mesa model" → replace with "Wolf-Sheep ecological scenario"
- Add placeholder: "A controlled τ-sweep and policy-ablation experiment confirm..." (finalize once results in)
- Keep: 97% LOC reduction, 32/32 OOD wins, ≤150 words
- Addresses: WSC Editor ("contribution not clear from abstract"), Reviewer ("reimplementation not validated")

**TASK C2 — §1.2 CONTRIBUTIONS: World-claim opener**
- Section: §1.2 Contributions (first paragraph)
- Delete: "This paper's primary contribution is a single-source-of-truth metric framework..."
- Replace with:
  > "Agent-based model optimization pipelines often couple loosely: evolutionary search, tournament selection, and statistical analysis each recompute metrics independently, risking silent aggregation divergence. We identify this as a structural risk and propose metric contracts—a composable, runtime-enforceable design pattern that makes divergence provably impossible on all contract-verified execution paths—by construction, not validation. Semantic correctness—whether metrics_episode() correctly captures domain intent—remains the modeller's responsibility, not the framework's."
- Replace all instances of "provably eliminates divergence" → "provably impossible on all contract-verified execution paths"
- Replace all instances of "runtime invariant" → "verifiable contract enforced at dispatch time via signature validation"
- Addresses: WSC Editor ("software engineering not methodology"), Reviewer A (overclaiming)

**TASK C3 — §2 RELATED WORK: Replace closing paragraph**
- Section: §2 Related Work (last paragraph, currently starting "Unlike per-model utility wrappers...")
- Delete: current closing paragraph
- Replace with:
  > "The contract-as-methodology tradition in ABM runs deep: ODD established observation contracts for model transparency, Janssen's replication protocol formalized initialization and parameter contracts, and POM extended this to outcome measurement contracts. Each defined consistency requirements at a different lifecycle stage. However, none enforced metric-stage consistency at execution time—a gap particularly visible in ensemble frameworks. EMAworkbench extends ensemble management to optimization and robustness analysis; its Outcome objects define metrics per-model but do not enforce consistency across optimization, tournament, and inference stages within a shared execution contract. HEAS closes this gap by making metric consistency a verifiable contract enforced at dispatch time via signature validation, rather than a documentation obligation."
- Addresses: WSC Editor ("tendentious comparison"), Reviewer ("EMAworkbench not adequately differentiated")

**TASK C4 — §4.3 WOLF-SHEEP: Remove "reimplementation" language**
- Section: §4.3 first paragraph (currently "To demonstrate compatibility with existing published models, we re-implement...")
- Delete: entire first paragraph
- Replace with:
  > "We present a mean-field ODE formulation of predator-prey dynamics using parameters drawn from the canonical Mesa Wolf-Sheep model. This section serves two purposes: first, to demonstrate that HEAS's metrics_episode() contract composes across structurally different model types (tabular, ODE, mean-field) without restructuring the simulation kernel; second, to show that researchers familiar with Mesa's widely-used pedagogical implementation can follow the parameter mapping without requiring a separate spatial simulation. HEAS does not claim to validate or reproduce Mesa's spatial dynamics, but rather to demonstrate that a researcher can express the same ecological logic in multiple notational forms while maintaining consistent metric collection."
- Add 1 sentence: "We include Wolf-Sheep not as evidence of novelty but to demonstrate HEAS's capacity to express classical ABMs familiar to the simulation community."
- Keep: all equations (Eqs. 1–3), parameters, HEAS implementation code
- Addresses: Reviewer E ("Wolf-Sheep is a new model, not reimplementation")

**TASK C5 — TABLE 1: Narrow to structural comparison only**
- Section: §2 Related Work, Table 1
- Replace current 6-row, 5-column table with:
```latex
\begin{table}[ht]
\centering\small
\caption{Metric contract enforcement across ABM policy-search frameworks.
Only HEAS enforces a unified \texttt{metrics\_episode()} signature across
optimizer selection, tournament evaluation, and statistical inference at the
framework level. EMAworkbench provides ensemble orchestration but does not
enforce a metric-stage contract; Optuna and Mesa leave metric aggregation
entirely to per-project code.}
\label{tab:contracts}
\begin{tabular}{lc}
\toprule
\textbf{Framework} & \textbf{Metric Contract Enforced at Framework Level} \\
\midrule
HEAS         & Yes (all pipeline stages, dispatch-time) \\
EMAworkbench & No (ensemble orchestration only) \\
Optuna       & No \\
Mesa~3.3     & No \\
\bottomrule
\end{tabular}
\end{table}
```
- Addresses: WSC Editor ("Table 1 is tendentious")

**TASK C6 — §5 OPENING PARAGRAPH: Structural risk hypothesis framing**
- Section: §5 Evaluation, first paragraph
- Replace with:
  > "We test the hypothesis that silent aggregation divergence is a structural risk—persistent regardless of stochasticity parameter τ—and that metric contracts eliminate it by construction on contract-verified execution paths. RQ1 examines persistence via systematic τ-variation; RQ2 isolates the contract as the causal driver via policy-fixed ablation. RQ3–RQ5 validate scalability, OOD robustness, and cross-domain portability."
- Addresses: both evaluators (framing, claims scope)

**TASK C7 — §5 RQ RESTRUCTURE: Renumber and reframe**
- New RQ order:
  - RQ1 (NEW): τ-sweep — "Does silent aggregation divergence persist regardless of stochasticity parameter τ?" (mechanism proof)
  - RQ2 (NEW): OOD ablation — "Does the metric contract—not policy quality—drive OOD consistency?" (causal isolation)
  - RQ3: Scale (d=1.39, p<10^-6) — unchanged
  - RQ4: OOD generalization (32/32 wins) — unchanged
  - RQ5: Cross-domain portability (Eco + Enterprise, main text summary; details to appendix)
- Fold original n=15 result into τ-sweep as τ=1.0 condition; add note: "The τ=1.0 condition replicates the original n=15 tournament setup; we expand to n=50 for tighter confidence intervals."
- Addresses: Reviewer A (n=15 underpowered), Reviewer B (τ=1.0 weakens narrative), Reviewer C (OOD confound)

**TASK C8 — §5.2 (NEW RQ1): τ-sweep results section**
- Add new section after §5.1 methods: ~300 words + 1 figure (rank reversals vs. τ with 95% CIs) + 1 table (rank stability per τ level)
- Interpret: divergence persists at low τ = structural; τ=1.0 = boundary/stress condition
- Addresses: Reviewer A (CI too wide), Reviewer B (τ=1.0 weakens claim)

**TASK C9 — §5.3 (NEW RQ2): OOD ablation results section**
- Add new section: ~250 words + 1 table (Condition A vs. B: Wilcoxon p, Cohen's d, variance) + 1 figure (rank variance by scenario)
- Interpret: Condition A (contract) dominates Condition B (fragmented), d ≥ 0.5, proves causal isolation
- Addresses: Reviewer C (OOD confound: policy quality vs. metric contract)

**TASK C10 — §5.5: Compress cross-domain details to appendix**
- Move Eco + Enterprise case study details to appendix
- Keep in main text: 1-2 sentence summary per domain + forward reference to appendix
- Frees ~0.8 pages for new experiments
- Addresses: page budget (new experiments +1.9 pages; cuts needed)

**TASK C11 — §3: Add dispatch signature validation explanation**
- Section: §3 (HEAS Framework description)
- Add 2-3 sentences explaining: "Dispatch-time signature validation ensures all metric computations invoked during evolutionary search, tournament selection, and statistical analysis execute the same aggregation logic. If a stage attempts to recompute metrics via an unregistered function, the signature check fails and execution halts. This makes metric divergence provably impossible on contract-verified execution paths."
- Draft concrete examples BEFORE writing (Supervisor Condition 1)
- Addresses: Reviewer ("by construction" claim needs mechanistic support)

**TASK C12 — §4.3 Wolf-Sheep compression**
- Move detailed Wolf-Sheep ODE equations to appendix if needed for page budget
- Keep in main text: model summary paragraph, purpose statement, key parameter values
- Frees ~0.5 pages if equations moved
- Addresses: page budget

**TASK C13 — ABSTRACT final update**
- After τ-sweep and ablation results are in hand: replace placeholder with actual numbers
- Verify: ≤150 words, single paragraph, no math symbols, no citations
- Addresses: WSC format compliance

**TASK C14 — New Methods subsection for new experiments**
- Add or expand §5.1 to document:
  - τ-sweep design (τ levels, n per level, fixed scenarios/seeds, integration of original n=15)
  - OOD ablation design (frozen policy, Condition A vs. B, fragmentation method, scenario pool)
  - Computational feasibility note: "300 total τ-sweep runs (~6 hours on cluster); 1500 OOD ablation evaluations (~10 hours)"
- Addresses: reviewer reproducibility requirements

**TASK C15 — "provably eliminates" → "provably impossible on contract-verified paths" (all instances)**
- Global search-and-replace throughout paper
- Also: "prevents" → "makes impossible on contract-verified paths" where used in strong causal sense
- Addresses: Reviewer A (overclaiming)

---

## HIGH (major improvements addressing reviewer concerns directly)

**TASK H1 — Semantic-correctness disclaimer: retain and strengthen**
- Keep in §1.2: "Semantic correctness—whether metrics_episode() captures domain intent—remains the modeller's responsibility, not the framework's."
- Ensure this appears in §5 discussion as well, to prevent reviewers reading too much into the "structural risk" framing

**TASK H2 — EMAworkbench complement statement**
- Add in §2 or §1.2: "EMAworkbench is a complementary framework for deep uncertainty analysis and ensemble exploration; it does not target metric-stage consistency enforcement and is not positioned as a metric contract framework."

**TASK H3 — Wolf-Sheep pedagogical purpose clarification**
- In §4.3, after new opening paragraph, add: "We include Wolf-Sheep not as primary evidence but to demonstrate HEAS's capacity to express classical ABMs familiar to the simulation community, supporting reproducibility for Mesa practitioners."

**TASK H4 — τ=1.0 "stress test" label in §5.2**
- When presenting τ-sweep results, explicitly label τ=1.0 as "maximum-stochasticity boundary condition / stress test"
- Add footnote or parenthetical: "(The τ=1.0 condition corresponds to the exploratory experiment reported in v0.2; it serves here as a boundary condition demonstrating divergence even under maximum exploration.)"

**TASK H5 — LOC comparison: add HEAS framework cost note**
- In §5 or §1.2 where LOC comparison appears: add brief note that "The 5-line HEAS coupling code does not include HEAS framework's own implementation, which is a one-time infrastructure cost rather than per-project coupling code."
- Addresses: Reviewer D (LOC comparison omits framework cost)

---

## MEDIUM (strengthening, positioning, consistency)

**TASK M1 — Figure captions: align with structural risk narrative**
- Review all figure captions; replace any that say "inconsistency" with "structural divergence" where appropriate

**TASK M2 — Cross-references: update for new RQ numbering**
- Update all §-references throughout paper to match new RQ1/RQ2 numbering

**TASK M3 — Appendix structure: prepare for compressed content**
- Ensure appendix has clear sections: Wolf-Sheep equations, Eco case study, Enterprise case study, τ-sweep raw statistics, OOD scenario list

**TASK M4 — Notation consistency: τ defined at first use in §5**
- Define τ (temperature parameter) at its first mention in §5.1

**TASK M5 — Limitations section: add or expand**
- Add in §6 or §7: "HEAS does not replace metric design or statistical testing best practices. Metric semantics remain the modeller's responsibility. The framework enforces structural consistency, not semantic validity."

---

## LOW (nice to have if page budget allows)

**TASK L1 — Discussion: broader implications (if space)**
- If page budget allows after all cuts/additions: add 1 short paragraph on implications for RL-based policy search and Bayesian optimization pipelines

**TASK L2 — Code availability statement**
- Add: "Code, experiment scripts, scenario lists, and raw results available at [URL]."

**TASK L3 — UQ literature mention in Related Work (if space)**
- Brief mention of sensitivity analysis literature (Sobol, Morris) to position metric contracts within broader uncertainty quantification landscape

---

## NEW EXPERIMENTS

### Experiment A: τ-Sweep (supports new RQ1)
**Purpose:** Test whether rank reversals persist regardless of τ (structural) or disappear at low τ (stochastic)

**Design:**
- τ ∈ {0.05, 0.15, 0.35, 0.65, 0.95, 1.0}
- n = 50 runs per τ level → 300 total runs
- Fixed: same scenario pool, same seed sequence as original n=15 experiment
- Measures: rank reversals (count + %), Cohen's h, Kendall's τ stability per condition

**Success criteria:**
- Structural: rank reversals plateau or persist at low τ
- τ=1.0 replicates original n=15 within ±5%
- 95% CIs non-overlapping between HEAS and Ad-hoc conditions

**FALLBACK if results noisy:** Shift framing from "mechanism proof" to "mechanism evidence"; lean on OOD ablation as primary claim. Report noise honestly with CIs.

**Compute:** ~6 hours on cluster; feasible in 2-week window

---

### Experiment B: OOD Ablation (supports new RQ2)
**Purpose:** Isolate whether metric contract (not policy quality) drives OOD consistency

**Design:**
- Policy: HEAS champion (frozen weights from original tournament)
- Condition A: Single metrics_episode() throughout (contract)
- Condition B: Three separate implementations with different ordering/aggregation per stage (fragmented)
- Scenarios: 20–30 held-out OOD ecological scenarios (unseen during training)
- Test: paired Wilcoxon on rank stability; report Cohen's d and 95% CI

**Success criteria:**
- Condition A: lower variance + d ≥ 0.5 + p < 0.05
- Result holds across all OOD scenarios

**Compute:** ~10 hours on cluster; feasible in 2-week window

---

## PAGE BUDGET

| Change | Added | Cut | Net |
|---|---|---|---|
| τ-sweep (figure + table + text) | +1.2 | — | +1.2 |
| OOD ablation (table + figure + text) | +0.7 | — | +0.7 |
| Wolf-Sheep compression | — | −0.8 | −0.8 |
| Eco/Enterprise to appendix | — | −0.8 | −0.8 |
| §5 restructure/tightening | — | −0.5 | −0.5 |
| Text revisions (C1–C6, H1–H5) | ~0 | ~0 | ~0 |
| **TOTAL** | **+1.9** | **−2.1** | **−0.2** |

**Target: ~12 pages. Comfortable margin.**

---

## EXECUTION TIMELINE

**Week 1 (Days 1–3):** C2, C3, C4, C5, C6 (text changes — no experiments needed)
**Week 1 (Days 4–5):** Run Experiment A (τ-sweep, ~6 hrs compute)
**Week 1–2 (Days 5–7):** C8 (τ-sweep results section), C1 abstract draft
**Week 2 (Days 8–9):** Run Experiment B (OOD ablation, ~10 hrs compute)
**Week 2 (Days 10–11):** C9 (ablation results section), C7 (RQ restructure)
**Week 2–3 (Days 12–14):** C10–C15, H1–H5, M1–M5, final compile and page count check
