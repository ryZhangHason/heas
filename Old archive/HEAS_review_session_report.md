# Academic Paper Review Session — Final Report
## HEAS: A Hierarchical Evolutionary Agent-Based Simulation Framework for Multi-Objective Policy Search

---

## Session Overview

- **Writing skill used:** `single-line-narrative-writing` (paragraph-level rhetorical structure; sentence-duty sequencing; gap-and-niche contribution framing)
- **Total rounds completed:** 3
- **Final verdict:** **Conditional Accept**
- **Starting external review:** WSC 2026 BORDERLINE REJECT
- **Final reviewer panel:** R1 (Content/Theory), R2 (Methods/Empirics), R3 (Continuing Fresh), R4 (Round 3 Fresh)
- **Mesa+utility-library baseline:** Implemented (`experiments/mesa_eco_util.py`) — 42 actual LOC vs ~38 estimated

---

## Round-by-Round History

### Round 1
**Reviewers:** R1 (Content) + R2 (Methods/Empirics) + External WSC Reviewer
**Verdicts:** R1 Major Revisions, R2 Reject, External Borderline Reject
**Decision:** Major Revisions

**Key argument changes (Author A):**
- Introduction reframed: "specific integration failure" vs vague "recurring problem"
- Contributions rewritten: HEAS as validated design pattern, twofold methodology claim
- EMAworkbench (Kwakkel 2017) + Ax/BoTorch paragraph added to Related Work
- Evaluation §5.1: RQs partitioned into Framework Verification (RQ1, RQ5) vs Domain Validation (RQ2–4)

**Key prose changes (Author B):**
- Table 1: all `(est)` estimates replaced with actual measured LOC (42 for Mesa+Util)
- Abstract: both 97% (vs Mesa) and 88% (vs Mesa+Util) reductions stated
- Scalar contract limitation expanded: 4-sentence discussion including Gini specifics
- RQ4 Wolf-Sheep: explicit mechanistic explanation (1D Pareto front, diversity counterproductive)
- RQ3: champion gene-values inline artifact `[0.000107, 0.9335]` removed

**Experimental work:**
- Implemented `experiments/mesa_eco_util.py` — Mesa+utility-library baseline
- Actual LOC count: 42 lines (vs ~38 estimated). 88% reduction vs HEAS confirmed.

---

### Round 2
**Reviewers:** R1 (Content), R2 (Methods/Empirics), R3 (Fresh — new)
**Verdicts:** R1 Major Revisions, R2 Minor Revisions ↑ (from Reject), R3 Major Revisions
**Decision:** Major Revisions (Round 2 mandatory)

**Key changes:**
- §1.1: Concrete silent divergence example (tournament reads final-step biomass; EA reads episode mean → volatile-peak champion)
- §3.5 new "Design Constraints and Trade-offs": justifies `dict[str,float]` (composability), names losses (time-series, agent-level distributions), bounds them for policy-ranking, justifies NSGA-II (WSC precedent, replaceable)
- §5.1: RQ1/RQ5 falsification criteria added
- §5.3: 100% agreement caveat (likely clear dominance on low-dimensional problems)
- Noise stability: explicitly labeled as synthetic proxy
- n=20 large-scale: justified by computational cost, variance robust per S2c
- OOD d=0.17: explained as near-deterministic scores; win rate more informative
- §5.5: Explicit scope limitation — ODE/tabular family only; spatially-explicit/network ABMs = future work
- Artifact: double-blind compliant placeholder + GitHub/Zenodo promise on acceptance

---

### Round 3
**Reviewers:** R1 (Content), R2 (Methods), R3 (Continuing), R4 (Fresh — new)
**Verdicts:** R1 Major Revisions, R2 Minor Revisions, R3 Minor Revisions, R4 Major Revisions
**Threshold:** 2/4 (50%) at Minor Revisions or better → **Conditional Accept**
**Decision:** Conditional Accept

**Final camera-ready changes applied:**
- Abstract: explicitly scoped to "ODE-style and tabular simulation-based policy search"
- Introduction: "ODE-style or tabular ABM" stated in opening sentence
- Contributions: C1–C4 labeling for four separable components (each independently useful)
- HV reference point for RQ4 scale heatmap added: `mean_biomass = -200, CV = 0.5`
- Opening framing: "The framework's four core components (C1–C4) are independently useful"

---

## Final Draft

**Location:** `HEAS draft V3/paper.tex` (in-place revision) and `HEAS_WSC_V4_final.tex` (copy)
**Lines:** 843 (up from 707 in original V3)

---

## Chief Editor's Final Conditions for Acceptance

**Camera-ready must-do (all applied):**
1. ✅ Explicit ODE/tabular domain framing in abstract and introduction
2. ✅ HV reference-point documentation across all RQs (§5.2, §5.4)
3. ✅ Clarified four-component structure (C1–C4 labeled, each described as independently useful)

**Items noted for future journal submission (not required for WSC):**
- Independent external case study (external collaborator adopting framework)
- User study comparing Mesa vs HEAS task completion time and error rates
- Comparison baselines vs EMAworkbench, PyMOO, Optuna in empirical evaluation
- Ablation study justifying dict[str,float] vs richer contracts empirically

---

## Changes Summary Table

| Category | V3 → V4 Change |
|---|---|
| Abstract | Added ODE/tabular scope; 88% vs utility-library; C1–C4 framing |
| Introduction | Reframed as specific integration failure; concrete divergence example added |
| Contributions | C1–C4 labeled; twofold methodological contribution explicit |
| Related Work | EMAworkbench + Ax/BoTorch added with gap-and-niche positioning |
| Framework §3 | New §3.5 Design Constraints and Trade-offs (dict[str,float] + NSGA-II) |
| Evaluation §5.1 | RQs partitioned; falsification criteria stated |
| §5.2 RQ2 | HV reference point specified; n=20 justification added |
| §5.3 RQ3 | 100% agreement caveat; noise = synthetic proxy labeled |
| §5.4 RQ4 | HV reference point added; RQ4 mechanistic explanation |
| §5.4 OOD | d=0.17 effect size explicitly discussed |
| §5.5 RQ5 | Scope limitation (ODE/tabular only) explicit |
| Table 1 | All estimates replaced with measured LOC (42 for Mesa+Util) |
| Conclusion | Scalar contract expanded to 4-sentence discussion; artifact placeholder |
| New file | `experiments/mesa_eco_util.py` — Mesa+utility-library actual implementation |

---

## Key Quantitative Improvements

- Coupling code baseline: `~38 (est)` → `42 (measured)` for Mesa+Util
- HEAS reduction: 97% vs Mesa, 88% vs Mesa+Util (both now clearly stated)
- All `(est)` markers in Table 1 removed

---

*Session completed: 3 rounds, Conditional Accept. Final paper at `HEAS draft V3/paper.tex`.*
