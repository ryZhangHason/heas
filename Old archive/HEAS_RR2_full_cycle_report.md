# Full R&R Round 2 — Complete Cycle Report
## HEAS WSC 2026 — Sub-Agent Driven Workflow

---

## Final Outcome: **MINOR REVISIONS → Submission-Ready**

**Final paper:** `HEAS_WSC_V6_submission_ready.tex` (888 lines)

---

## All Sub-Agents Deployed (12 total)

| Phase | Agent | Verdict / Output |
|---|---|---|
| Phase 1b | Supervisor | REVISE — choose design-by-contract lane |
| Phase 2 | Student | Revised RQ + abstract + §1.2 + §1.1 |
| Phase 2b | Supervisor | APPROVED |
| Phase 3 | R1 (Content) | Major Revisions |
| Phase 3 | R2 (Methods) | Major Revisions |
| Phase 3b | Chief Editor | Major Revisions — #1 critical = controlled experiment |
| Phase A | Student | Ran experiment + applied 8 tex edits |
| Phase B | Peer 1 | Ceiling effect concern — add Stage 2 stochastic test |
| Phase B | Peer 2 | Meyer/DbC imprecise — use "single-source-of-truth" |
| Phase C | Supervisor | PATCH FIRST — Stage 2 + terminology fix mandatory |
| Phase C patch | Student | Stage 2 τ=1.0 all conditions + Meyer removed |
| Phase D | R1 | **Minor Revisions** |
| Phase D | R2 | Major Revisions (2 narrow gaps) |
| Phase D | R3 (fresh) | **Minor Revisions** |
| Phase E | Chief Editor | **Minor Revisions** — 2/3 vote, R2 concern #1 already addressed |
| Phase F | Author A+B | Applied 2 final changes → submission-ready |

---

## Key Intellectual Evolution Across the Cycle

### Starting point (V5 depacked)
- Claimed to "eliminate silent divergence" empirically
- No controlled experiment
- Design-by-contract not invoked
- Meyer never cited
- Tournament results as primary evidence

### After Research Group (Supervisor ruling)
- Reframe: "prevent by construction" not "eliminate empirically"
- Choose one lane: design pattern OR empirical — chose design pattern
- Terminology locked: "silent aggregation inconsistency"

### After Round 1 Reviews (Major Revisions)
- Critical gap: no before/after demonstration that inconsistency exists and HEAS fixes it
- R1 + R2 both demanded controlled experiment
- Editor: "This is the non-negotiable revision"

### After Controlled Experiment + Patch
- HEAS: 0% rank reversals (95% CI: 0%–20.4%)
- Ad-hoc-Step: 5.6% reversals (Cohen's h=0.476, medium effect)
- Stage 2 (stochastic robustness): τ=1.0 all conditions → inconsistency is systematic, not stochastic
- Meyer reference dropped; "single-source-of-truth metric framework" adopted
- Structural vs. semantic distinction added to Threats section

### After Round 2 Reviews (Minor Revisions)
- R1: Minor (W1/W2/W6 resolved)
- R2: Major but both concerns already addressed in paper — editorial correction issued
- R3: Minor (two clarification requests)
- Final two changes: OOD random-policy baseline sentence + practical stakes paragraph

---

## What Changed in the Paper (V5 → V6)

| Section | Change |
|---|---|
| Abstract | Kept V5 abstract (already strong); minor inline updates |
| §1.2 Contributions | "single-source-of-truth metric framework" (dropped design-by-contract/Meyer); C1-C4 as "infrastructure not separate contributions"; two-claim evaluation structure |
| §2 Related Work | Added Table 2: HEAS vs DEAP/Optuna/EMAworkbench/Mesa/Ax on 4 criteria; added 2 positioning sentences |
| §5.1 Evaluation | Operational definition of aggregation inconsistency (Kendall τ < 1); primary/secondary evidence structure; falsification criteria; statistical methods statement |
| §5.2 (NEW) | Controlled aggregation experiment: 3 conditions × 15 runs; rank reversal table; Cohen's h CIs; Stage 2 stochastic test |
| §5.3–§5.7 | Renumbered from §5.2–§5.6 |
| §5.5 OOD | Added Wilson CI [0.94, 1.0]; added random-policy baseline sentence (~50% vs 100%) |
| §5.6 Heatmap | Added Bonferroni correction note (α=0.0056); exploratory framing |
| Threats to Validity | Added: "framework prevents structural inconsistency, not semantic consistency" |
| Conclusion | Added: practical stakes paragraph + ODE extension boundary statement |

---

## What the Paper Now Claims (V6)

**One primary contribution:** A single-source-of-truth metric framework that prevents aggregation inconsistency in ODE-style and tabular ABM policy search.

**Validated by two claims:**
1. **Sufficiency by construction:** Controlled experiment shows HEAS 0% rank reversals vs. 5.6% in ad-hoc pipeline (Cohen's h=0.476, Stage 2 confirms inconsistency is systematic not stochastic)
2. **Portability:** Same contract used without framework modification across ecological, enterprise, and Wolf-Sheep case studies

**Secondary supporting evidence:**
- Coupling code reduction: 160→5 LOC (97% vs Mesa), 42→5 (88% vs utility baseline)
- Tournament stability: 100% voting-rule agreement (with near-tie sensitivity study)
- EA convergence: NSGA-II d=1.39 at 1000-step scale
- OOD robustness: 32/32 wins, Wilson CI [0.94, 1.0], substantially above ~50% random baseline

---

## Files Produced This Session

| File | Location |
|---|---|
| **Final submission-ready paper** | `heas/HEAS_WSC_V6_submission_ready.tex` |
| Revised paper (in-progress) | `HEAS_WSC/heas/V4 submission/HEAS_WSC_V5_revised.tex` |
| Controlled experiment code | `HEAS_WSC/heas/experiments/agg_consistency_experiment.py` |
| Stage 1 results | `HEAS_WSC/heas/experiments/agg_consistency_results.json` |
| Stage 2 results | `HEAS_WSC/heas/experiments/agg_consistency_results_stage2.json` |
| Author A revision plan | `HEAS_WSC/AUTHOR_A_REVISION_PLAN.md` |
| Author B prose revisions | `HEAS_WSC/AUTHOR_B_PROSE_REVISIONS.md` |
| Round 2 R&R report | `heas/HEAS_RR2_session_report.md` |

---

## Remaining Open Items (for actual submission)

1. **Fill real citation keys** for Plesser (2018) — currently `\cite{TOCHECK-plesser}` placeholder in some versions; check `references.bib`
2. **Compile PDF** and verify page count ≤ 8 pages
3. **Verify figure references** — several figures referenced (fig4_large_scale_showdown, fig8_noise_stability, etc.) need to exist in `figs/` folder
4. **Fill in real author names/affiliations** — currently ZHANG, NIE, ZHAO placeholders
5. **Write cover letter to R2** pointing to Cohen's d full specification at line 621–625

---

*Full R&R cycle completed. 12 sub-agents across 8 phases. Final decision: Minor Revisions accepted → Submission-ready.*
