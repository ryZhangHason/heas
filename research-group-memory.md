# Research Group Memory
**Project:** HEAS WSC 2026 — Hierarchical Evolutionary Agent-Based Simulation Framework
**Last session:** 2026-03-26

## Current State
- **Active phase:** Improvement / revision (post-proofread, pre-v0.2)
- **Research question:** Does enforcing a single metrics_episode() → dict[str,float] contract at the framework level prevent silent aggregation inconsistency in multi-objective ABM policy search?
- **Contribution claim:** Single-source-of-truth metric framework that prevents structural aggregation inconsistency by construction (not by detection), reducing coupling code 97% vs Mesa.
- **Design:** Three case studies (ecological, enterprise, Wolf-Sheep ODE) + controlled aggregation experiment + LOC comparison + OOD tournament validation.

## Phase Log
- Phase 1: APPROVED — RQ: does uniform metric contract prevent aggregation divergence?
- Phase 2: APPROVED — Controlled experiment (n=15, 8 scenarios, 4 voting rules) + case studies as composition vehicles.
- Phase 3: APPROVED — HEAS 0% rank reversals vs Ad-hoc 6.7%, Cohen's h=0.476, 97% LOC reduction, 32/32 OOD wins.
- Phase 4: APPROVED — v0.1 at 12 pages, clean compile, final proofread passed 2026-03-26.
- **Current:** v0.1 improvement session. 13-task TODO produced and Supervisor-approved.

## Key Decisions
- "Single-source-of-truth" = STRUCTURAL consistency (one implementation shared across stages), not semantic correctness (developer's responsibility). §1.2 language must reflect this.
- Case studies are ARCHITECTURAL EVIDENCE (composition vehicles), not domain-calibrated models. Frames as positive design choice, not limitation.
- Figure 2 (champion 32-scenario bar chart): REMOVED in v0.2. Replaced with inline consolidation sentence — all stats already in text, zero-surprise result.
- Scalar contract (dict[str,float]): minimalism is the mechanism that prevents divergence. Richer contracts reintroduce per-stage aggregation choices.
- Stage 2 τ=1.0 for all conditions: reframed as "inconsistency is systematic/architectural, not stochastic."

## Supervisor's Standing Concerns
1. **Causal loop not closed**: Paper must explicitly connect 32/32 OOD validation back to §1.2 coupling-code problem. NEW TASK A addresses this.
2. **§3.5 risk of over-explanation**: Do NOT expand Design Constraints — streamline instead. The mechanism is demonstrated empirically; prose should not defend it.
3. **SSOT language precision**: "single-source-of-truth" must be qualified to structural only at §1.2 line 165–166.

## Next Step
Execute HEAS_V01_TODO.md in the listed order (TASK 1 first, then TASKS 2+A, then 4/10/5, then 9, 3, 7+8, B, 11/12). Recompile after all changes. Verify 12 pages. Tag result as v0.2.
