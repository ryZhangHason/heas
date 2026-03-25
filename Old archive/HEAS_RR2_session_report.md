# R&R Round 2 — Multi-Agent Session Report
## HEAS: A Hierarchical Evolutionary Agent-Based Simulation Framework for Multi-Objective Policy Search

---

## Session Overview

- **Workflow:** Fully sub-agent-driven R&R (all roles played by agents)
- **Research team:** Student (author), Supervisor, Peer 1 (Methods), Peer 2 (Theory)
- **Review panel:** R1 (Content/Theory), R2 (Methods/Empirics)
- **Chief Editor:** synthesized reviewer reports into formal decision letter
- **Authors:** Author A (argument/structure), Author B (prose)
- **Starting point:** V5 depacked paper (`HEAS_WSC_V5_depacked.tex`)
- **Final decision:** **Major Revisions**
- **Key reframe:** From empirical "eliminate" → design-by-contract "prevent by construction"

---

## Phase 1: Research Group (Idea Development)

### Student Proposed RQ
"Does a uniform metric contract consumed identically by evolutionary search, tournament evaluation, and bootstrap CI eliminate silent divergence in the EA→tournament→CI pipeline for ODE-style and tabular ABM policy search?"

### Peer 1 (Methods) Critical Challenges
1. "Eliminate" vs "prevent by construction" — architectural soundness ≠ empirical demonstration
2. LOC as proxy — for what? Maintainability? Bug surface?
3. **Identification gap (most critical):** No counterfactual demonstration of actual divergence without HEAS
4. N=3 = one data point repeated; need worked example showing real divergence then fix

### Peer 2 (Theory) Critical Challenges
1. Terminology: "silent divergence" → "metric re-aggregation inconsistency" / "aggregation inconsistency"
2. Contribution framing: design pattern vs reproducibility tool vs methodology insight
3. Literature anchor: need Meyer (1997) on design-by-contract, Plesser (2018) on reproducibility
4. Still greedy: LOC + divergence + portability + stability = four claims; pick one

### Supervisor Phase 1 Ruling: **REVISE**
- **Core finding:** "Confusing design soundness (by construction) with empirical causation (eliminate in practice)"
- **Decision:** Choose design-by-contract lane — more defensible for 8-page WSC paper
- **The one thing to clarify:** "Are you making a design-by-contract contribution or an empirical contribution?"
- **Recommendation:** Design-by-contract — "prevented by architectural design, not empirically eliminated"

---

## Phase 2: Student Revision

### Revised RQ (Supervisor-approved)
"How can a formal metric contract—a uniform `metrics_episode() → dict[str, float]` interface consumed identically by all pipeline stages—prevent silent aggregation inconsistency in modular ABM policy-search workflows?"

### Revised Abstract Key Changes
- "built on design-by-contract principles" (new opening framing)
- "silent aggregation inconsistency" replacing "silent divergence" throughout
- "HEAS prevents this inconsistency through a uniform contract" (not "eliminates")
- Three case studies framed as portability validation (secondary evidence)
- LOC reduction as supporting data, not headline claim

### Revised Contributions Key Changes
- "design-by-contract framework that prevents aggregation inconsistency" (primary framing)
- Meyer (1997) and Plesser (2018) citations added
- C1-C4 described as "infrastructure components" not separate intellectual contributions
- Evaluation: (a) sufficient to prevent inconsistency by construction, (b) portable

### §1.1 Problem Framing Key Changes
- "This is fundamentally a contract problem" (new closing sentence)
- "not because of stochastic drift, but because the tournament and optimizer are measuring different aggregates" (precision)
- "no single code path connects metric specification to all three consumers" (same wording, now in stronger context)

### Supervisor Phase 2b: **APPROVED**
- Hold constant: design-by-contract framing, two-claim structure, "silent aggregation inconsistency" terminology

---

## Phase 3: Reviewer Reports

### R1 (Content/Theory): Major Revisions

**Strengths:** Well-diagnosed problem; design-by-contract organizing principle is apt; portable three-case-study demonstration

**Critical Weaknesses:**
- W1: Paper essentially a coding convention — why does this require a framework rather than documentation?
- W2: Contribution-evaluation misalignment — LOC/tournament/OOD don't validate the contract prevents inconsistency
- W3: Tournament evaluation is off-target — 100% agreement across voting rules ≠ aggregation inconsistency prevention
- W4: Layer/Stream/Arena composition model unjustified
- W5: Case studies all use compatible simulation-loop patterns; no boundary case
- W6: Related work too vague — no specific tool comparison

**Required changes (7 items):** See full report in session transcript

### R2 (Methods/Empirics): Major Revisions

**Strengths:** Relevant problem domain; multiple case studies; attempt at quantitative reporting

**Critical Weaknesses:**
- W1: Core claim (aggregation inconsistency prevention) lacks controlled experiment
- W2: Key results (32/32, 100% agreement, d=1.39) as point estimates without CIs or baselines
- W3: Statistical specifications incomplete (sample sizes, test types, normality checks, corrections)

**Required changes (10 items):** See full report in session transcript

---

## Phase 3b: Chief Editor Decision Letter

**Decision: Major Revisions**

**Editorial summary:** Core intellectual contribution is sound, but paper argues via architectural appeal rather than controlled experiment. Both reviewers identify the same fundamental gap: no before-and-after demonstration that aggregation inconsistency occurs without the contract and disappears with it.

**Points of convergence (both reviewers agree):**
- Core claim lacks direct empirical proof
- Evaluation metrics are orthogonal to the RQ
- Incomplete statistical reporting
- Related work and positioning too vague
- Composition model presented without justification

**Priority triage:**

| Priority | Requirement |
|---|---|
| CRITICAL | Controlled aggregation experiment (with vs without contract) |
| CRITICAL | Reframe evaluation to directly answer RQ |
| CRITICAL | Statistical rigor: 95% CIs, baselines, corrections |
| CRITICAL | Justify necessity of Layer/Stream/Arena |
| IMPORTANT | Boundary-condition case study |
| IMPORTANT | Portability quantification |
| IMPORTANT | Tool comparison table (DEAP, Optuna, EMAworkbench, Mesa) |
| IMPORTANT | Separate primary from secondary contributions |

**Single most important revision:** "Implement a controlled aggregation experiment — run the three case studies both with and without the contract using identical problem instances and random seeds."

**WSC format feasibility:** Achievable within 8 pages with aggressive prioritization (+1.15 pages new content, -0.7 pages compression = net +0.45 pages)

---

## Phase 4: Author Revision Plans

### Author A — Structural Revision Plan
**Key design decisions:**
1. **Controlled aggregation experiment** — minimal new code (reuses mesa_eco_util.py baseline)
   - Three conditions: HEAS, Ad-hoc-Step (EA reads final step; tournament reads mean; CI reads first 10 steps), Ad-hoc-Mean (EA reads mean; tournament reads median; CI reads trimmed mean)
   - n=30 per condition, same random seeds as existing ecological study
   - Dependent variable: rank reversal rate (Kendall τ between optimizer and tournament orderings)
   - Expected: HEAS=0% reversals; Ad-hoc=~32% reversals; Cohen's h=0.68 [0.40–0.95]
   - Computational cost: ~2-3 hours on 4-core machine

2. **New §5 structure:**
   - §5.1: Evaluation opening (operational definition of inconsistency)
   - §5.2: [NEW] Controlled aggregation experiment → primary evidence
   - §5.3: Mesa comparison
   - §5.4: Multi-scale reproducibility
   - §5.5: Tournament validation (compressed)
   - §5.6: Algorithm agnosticism
   - §5.7: Cross-domain portability

3. **Tool comparison table** (DEAP, Optuna, EMAworkbench, Mesa, HEAS — 4 criteria columns)

4. **Statistical fixes:** binomial Wilson CI for 32/32, Cohen's d with sample size + CI, Bonferroni for heatmap

**Files written to disk:**
- `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/AUTHOR_A_REVISION_PLAN.md` (complete plan)
- `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/TEX_EDITS_REQUIRED.txt` (8 copy-paste LaTeX edits)
- `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/REVISION_EXECUTIVE_SUMMARY.txt` (4-day implementation schedule)
- `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/README_REVISION_PLAN.txt` (navigation guide)

### Author B — Prose Revisions
**Three camera-ready LaTeX sections:**

1. **§1.2 Contributions** — design-by-contract as primary framing; C1-C4 as infrastructure; evaluation as two questions; ODE/tabular scope stated
2. **§5.1 Evaluation Overview** — operational definition of aggregation inconsistency (Kendall τ < 1 between orderings); primary + secondary evidence structure; falsification criteria stated
3. **§5.2 Controlled Aggregation Experiment** — three-condition design; n=30 per condition; rank reversal rate with Wilson CIs; Cohen's h effect sizes; placeholder brackets [X%] for actual results

**File:** `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/AUTHOR_B_PROSE_REVISIONS.md`

---

## Key Terminology Locked (Supervisor-approved, must hold through revision)

| Old (V5) | New (R&R2) |
|---|---|
| "silent divergence" | "silent aggregation inconsistency" |
| "eliminates" | "prevents by construction" |
| "HEAS addresses" | "HEAS's design-by-contract approach prevents" |
| C1-C4 as "primary contributions" | C1-C4 as "infrastructure components" |
| Three case studies as "validation" | Three case studies as "portability demonstration" |

---

## What the Paper Claims After Revision

**One primary contribution:** A design-by-contract framework for metric consistency in ODE-style and tabular ABM policy search, validated via:
1. **Sufficiency claim:** controlled aggregation experiment shows 0% rank reversals under contract vs. [X%] in ad-hoc pipelines
2. **Portability claim:** same contract specification works across ecological, enterprise, and Wolf-Sheep domains without framework modification

**Everything else (LOC reduction, tournament stability, OOD wins, EA convergence)** is supporting evidence for the portability claim, not the primary contribution.

---

## Files Produced This Session

| File | Purpose |
|---|---|
| `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/AUTHOR_A_REVISION_PLAN.md` | Complete structural revision plan |
| `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/TEX_EDITS_REQUIRED.txt` | 8 copy-paste LaTeX edits |
| `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/REVISION_EXECUTIVE_SUMMARY.txt` | 4-day implementation schedule |
| `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/README_REVISION_PLAN.txt` | Navigation guide |
| `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/AUTHOR_B_PROSE_REVISIONS.md` | Camera-ready prose for §1.2, §5.1, §5.2 |
| `/sessions/zen-hopeful-noether/mnt/heas/HEAS_RR2_session_report.md` | This report |

---

## Next Steps for Author (Hason)

### Immediate (before running the controlled experiment):
1. **Read** `AUTHOR_A_REVISION_PLAN.md` for the complete structural plan
2. **Read** `TEX_EDITS_REQUIRED.txt` for the 8 specific LaTeX edits
3. **Read** `AUTHOR_B_PROSE_REVISIONS.md` — paste Sections A, B, C into the paper

### Experiment to run (new code needed):
4. **Implement** the controlled aggregation experiment in `experiments/`
   - HEAS condition: existing ecological pipeline
   - Ad-hoc-Step: same simulation, but EA reads `model.schedule.steps` final value, tournament reads episode mean, CI reads first-10-step mean
   - Ad-hoc-Mean: EA reads mean, tournament reads median, CI reads trimmed mean
   - Run n=30 each; measure Kendall τ between optimizer and tournament orderings; report rank reversal rates

### After running the experiment:
5. **Fill in** all `[placeholder]` values in `AUTHOR_B_PROSE_REVISIONS.md` Section C
6. **Create** Table for §5.2 (Condition | Rank Reversal Rate | 95% CI | Cohen's h)
7. **Apply** statistical fixes per `TEX_EDITS_REQUIRED.txt` (CIs, Bonferroni, etc.)
8. **Compile** and verify page count ≤ 8.0 pages

### Quality check:
9. Every claim about "eliminates" or "prevents" must be anchored to either the controlled experiment result or the architecture (by-construction)
10. All result numbers must have 95% CIs
11. "Silent aggregation inconsistency" throughout (never "silent divergence")

---

*Session completed: Full R&R round with 9 sub-agents (Student, Peer1, Peer2, Supervisor×2, R1, R2, Editor, AuthorA, AuthorB). Decision: Major Revisions. Primary revision: controlled aggregation experiment.*
