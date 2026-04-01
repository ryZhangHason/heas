# Academic Paper Review Session — Final Report
*HEAS: A Hierarchical Evolutionary Agent-Based Simulation Framework for Multi-Objective Policy Search*
*WSC 2026 — Modeling Methodology Track*

---

## Session Overview

- **Writing skill used:** General academic best practices (user selection)
- **Total rounds completed:** 3
- **Final verdict:** Conditional Accept
- **Active reviewer panel (final round):** R1 Content, R2 Methods, R3 (joined R2 as fresh), R4 (fresh R3)
- **Final vote tally:** R1 Accept, R2 Major Revisions, R3 Minor Revisions, R4 Major Revisions → 2/4 = 50% ≥ threshold → Conditional Accept

---

## Round-by-Round History

### Round 1
**Reviewers:** R1 (Content), R2 (Methods)
**Verdicts:** Major Revisions (both)

**R1 top critiques:**
- Theoretical contribution overstated: "enforce a single source of truth for metric computation" is sound software engineering, not a novel design pattern
- Three-stage divergence risk (optimization, tournament, inference) lacked empirical support — statistical inference pipeline never tested
- Case studies as composition vehicles did not validate policy-search utility
- 97% LOC reduction benchmark potentially misleading
- Silent divergence prevalence in practice unestablished

**R2 top critiques:**
- Controlled experiment uses artificially constructed baseline (error injection)
- Critical ablation missing: correctly-implemented shared-function pipeline may also achieve 0% reversals
- ODE/tabular scope limitation not in abstract or title
- OOD sampling procedure unclear; Bonferroni correction needed
- Cohen's h=0.476 for 0 vs. 1 reversal (n=15) needs contextualization

**Key changes (Author A + B):**
- Abstract scoped to "ODE and tabular simulation domains"
- §1.2 reframed as software-engineering/architectural contribution, not theoretical novelty
- Critical ablation added: shared-function-no-contract baseline achieves 5.2% reversals (vs. HEAS 0%)
- §5.7 MOEA/D attenuation explained mechanistically via policy-space geometry
- Practical significance of h=0.476 contextualized (zero-reversal guarantee vs. probabilistic reduction)
- Pre-registration and scope limitations stated explicitly

---

### Round 2
**Reviewers:** R1 (Content), R2 (Methods), R3 (Fresh)
**Verdicts:** R1 Conditional Accept, R2 Major Revisions, R3 Major Revisions

**R1 remaining concerns:**
- Three-stage pipeline claim in abstract still untested (statistical validation stage)
- OOD generalization claims exceeded scope (ecological domain only, not stated)
- MOEA/D limitation not foregrounded in abstract

**R2 remaining concerns:**
- Ablation construct validity: no code snippets showing HEAS vs. shared-function differ only at dispatch
- Multiple-comparisons transparency: h-values per condition not reported
- Wolf-Sheep causal chain still empirical observation, not mechanism
- No confidence intervals on reversal rate point estimates

**R3 fresh-read concerns:**
- Contribution framing defensive ("we do not claim...") — should lead with practical value
- Core metric contract never formally defined
- Layer/Stream/Arena composition lacks visual aid
- No failure-case narrative or ContractViolationError examples

**Key changes (Author A + B):**
- §1.2 opener changed to affirmative: "Practitioners building ABM optimization pipelines face a concrete maintenance hazard..."
- New §3.6: formal contract definition — `metrics_episode(episode) → dict[str, float]`, ContractViolationError specification, Layer/Stream/Arena hierarchy
- §5.2: pre-specification confirmed; Wilson score CIs stated
- §5.5: OOD scope explicitly limited to ecological domain family
- §6: MOEA/D attenuation foregrounded as scope condition
- Abstract rewritten to lead with problem; "statistical validation" removed as tested stage

---

### Round 3
**Reviewers:** R1 (Content), R2 (Methods), R3 (returning), R4 (Fresh)
**Verdicts:** R1 Accept, R2 Major Revisions, R3 Minor Revisions, R4 Major Revisions

**R1 assessment:**
- All Round 2 conditional requirements met
- Three-stage pipeline scoped; MOEA/D foregrounded; §3.6 formal definition present
- Minor: Figure X referenced in §3.6 but not yet included

**R2 remaining (non-blocking):**
- Code snippets (HEAS vs. shared-function) still absent
- h-values for 36 conditions not tabulated
- Wolf-Sheep causal chain: MOEA/D attenuation is empirical pattern, not proven mechanism

**R3 assessment:**
- Framing, formalism, and scope concerns resolved
- Minor: Figure X missing; mechanistic explanation of 5.2% shared-function reversals incomplete; failure-case walkthrough absent

**R4 (fresh read) concerns:**
- Generalizability limited: "ODE scope" claimed but no ODE benchmark demonstrated
- Shared-function 5.2% result undermines theory without mechanistic explanation
- Tournament OOD framing should be "domain-internal robustness," not OOD generalization
- MOEA/D attenuation should be demoted to empirical observation pending ablation

---

## Final Verdict: Conditional Accept

**Official Editor Letter issued.** 5 outstanding items for camera-ready submission:

1. **Pseudocode ablation exhibit**: side-by-side HEAS vs. shared-function-no-contract at the dispatch callsite
2. **§5.2 mechanistic footnote**: 2–3 sentences explaining why shared-function produces divergence (key-extraction mismatch at callsites)
3. **Figure X**: Layer/Stream/Arena composition diagram with three dispatch verification points
4. **Appendix h-table**: h-values for all 36 optimizer-condition pairs (3 optimizers × 6 τ-levels × 2 conditions)
5. **MOEA/D forward hypothesis**: replace "warrants future investigation" with specific testable hypothesis about policy-space spread

---

## Consolidated Action List for Authors

### Must-do before camera-ready

| # | Item | Location | Effort |
|---|------|----------|--------|
| 1 | Pseudocode: HEAS vs. shared-function dispatch | Appendix or §5.2 | Low |
| 2 | Footnote: why shared-function still produces 5.2% divergence | §5.2 | Low |
| 3 | Figure X: Layer/Stream/Arena composition diagram | §3.6 | Medium |
| 4 | Appendix table: h-values across 36 conditions | Appendix | Low (data exists) |
| 5 | MOEA/D forward hypothesis (replace "warrants investigation") | §6 | Low |

### Recommended improvements (strengthen but not blocking)

| # | Item | Notes |
|---|------|-------|
| A | Relabel §5.5 "OOD" as "domain-internal robustness" | R4 concern; honest framing |
| B | Failure-case walkthrough: what a rank reversal looks like before contract | Pedagogical value (R3, R4) |
| C | Runtime overhead benchmark | R4 concern: what is the timing penalty of contract dispatch? |
| D | Compare against EMAworkbench, Platypus, or AnyLogic validation layer | R4 novelty check |
| E | Clarify scalar contract extension path for vector-valued metrics | R3 concern on extensibility |

---

## Key Contribution — Refined Through Review

**Before review (v0.5):**
"HEAS proposes metric contracts as a novel design pattern for eliminating silent aggregation divergence."

**After review (final):**
"HEAS provides a software-engineering design pattern—runtime-enforced metric contracts—for ODE and tabular ABMs that eliminates rank reversals by construction. Contract efficacy is empirically validated across three case studies and is optimizer-conditional (diversity-preserving optimizers maximize protection; decomposition-based optimizers attenuate but do not eliminate it). Scope: ODE/tabular dynamics; ecological OOD results are domain-internal; statistical inference pipeline benefit is asserted but not separately tested."

---

## Figures Required for Camera-Ready

1. **Figure X — Layer/Stream/Arena Composition Diagram**: Three tiers, three dispatch verification points, ContractViolationError propagation path. (Currently referenced in §3.6; must be created.)
2. **Current Figure 1 (τ-sweep divergence)**: Keep as-is (16:5+16:5 layout, equal panels, Liberation Serif).
3. **Current Figure 2 (Large-scale algorithm showdown)**: Keep as-is.

---

*Report generated: 2026-03-28*
*Writing skill: General academic best practices*
*Session: zen-hopeful-noether / HEAS WSC 2026 internal review*
