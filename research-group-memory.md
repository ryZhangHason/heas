# Research Group Memory
**Project:** HEAS WSC 2026 — Hierarchical Evolutionary Agent-Based Simulation Framework
**Last session:** 2026-03-30

## Current State
- **Active phase:** v0.6 internally reviewed → Supervisor APPROVED → v0.7 fix plan in progress
- **Contribution claim (LOCKED for WSC):** "Metric contracts provide runtime-enforceable guarantees against aggregation divergence in non-deterministic execution stages of loosely-coupled ABM pipelines, where determinism alone cannot apply."
- **Strategic reframe (ADOPTED 2026-03-30):** "Metric divergence is a hidden confound in champion selection. Contracts remove the confound → better generalization (32/32 OOD). Frame as overfitting prevention, not just divergence avoidance."
- **Paper:** v0.6 clean, 12 pages. v0.7 in progress (~30 hrs / 10 days).

## Phase Log
- Phase 1–3: APPROVED — all experiments complete and integrated
- Phase 4 v0.6 internal review: COMPLETE (2026-03-30) → Supervisor APPROVED → proceed v0.7

## Experiment Results (all in §5)
- Stage 1 (n=15): HEAS 0% vs Ad-hoc-Step 6.7%; h=0.476 [NOW LABELED EXPLORATORY — underpowered]
- Stage 2 (n=30, pre-specified): HEAS 6.1% vs Ad-hoc-Step 12.2%; h=0.215, p=0.0067
- τ-sweep: semantic h=0.72–1.14, syntactic h=0.32–0.66, near-uniform |h|<0.07
- Multi-optimizer: h>0 in 36/36 conditions; KW significant at 5/6 τ levels (optimizer-conditional)
- 32/32 OOD wins; 24/24 single-anchor extrapolation wins [NOW: null-safety / confound-removal framing]

## Key Decisions (updated 2026-03-30)
- Drop ODD→POM→HEAS lineage — forced; replace with Thiele & Grimm honest connection
- Acknowledge metric contract = schema validation / interface spec (weaker than Meyer's DbC)
- Stage 1 (n=15) → reframe as exploratory; add post-hoc power analysis
- Apply Bonferroni α=0.0056 (~9 tests); downgrade results where needed
- OOD (32/32) → "null-safety / confound-removal result," NOT domain transfer
- "Provably impossible" → "infeasible under the contract constraints we define"
- Wolf-Sheep → appendix or explicit scope-boundary test (not "composition vehicle")
- Case study isomorphism: acknowledge in §4 as design choice, not domain-diversity claim
- Coupling code: add §1 paragraph on structural motivations (modularity/cognitive/tooling)
- Bonferroni family was 2 (Stage 2 only); now expanded to ~9 tests across all §5 sections

## Supervisor's Standing Concerns
1. Confound-removal claim: draft Limitations first; show mediation gap explicitly before writing §5
2. Ad-hoc-Step must be fully auditable: Appendix B pseudocode + which operations are contract-verifiable
3. "Provably impossible" → "infeasible under contract constraints" — make this move explicit in §1
4. Dunn post-hoc tests after KW: show which optimizer pairs differ at each τ level

## v0.7 Fix List (prioritized)
CRITICAL: power analysis (Stage 1 exploratory), Ad-hoc-Step pseudocode (Appendix B),
Bonferroni re-analysis, OOD null-safety reframe, Research Contribution Type section (§1)
IMPORTANT: ablation to §5 with results, Dunn tests, drop ODD lineage, DbC disclaimer,
motivate coupling code problem, acknowledge isomorphism, Wolf-Sheep scope boundary,
Threats mitigation strategies, confound-removal framing in §2 + §5
STRATEGIC: "infeasible under constraints" language, Wolf-Sheep → appendix option

## Next Step
Build v0.7: start with Limitations section (test confound-removal reframe), then Appendix B
(Ad-hoc-Step pseudocode), then Bonferroni re-analysis, then §1 Research Contribution Type insert.
Do not touch §5 evaluation narrative until Limitations is solid.
