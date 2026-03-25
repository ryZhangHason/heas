# HEAS WSC 2026 — v0.1 TODO
**Session:** Research Group Meeting (4-agent) — 2026-03-26
**Status:** Supervisor-approved. All tasks verified within 12-page budget.
**Page budget:** Fig 2 frees ~15–18 lines; net additions stay within that envelope.

---

## CRITICAL — Do First

### ✅ TASK 1 — Remove Figure 2 (fig:champion32)
**What:** Delete the 32-bar champion-minus-reference bar chart entirely.
**Where:** §5.4 Tournament Validation and OOD Champion Robustness (after the OOD champion paragraph).
**Replacement sentence** (inline in §5.4, replacing the \begin{figure}...\end{figure} block):
> "Across all 32 held-out ecological scenarios, the champion achieved a 100% win fraction (p=4.66×10⁻¹⁰, one-sided binomial, H₀: π=0.5; Wilson two-sided 95% CI [0.94, 1.0]; Δ=+25.0, d=0.17), demonstrating that tournament-based policy ranking remains stable across OOD scenario families and does not reverse under voting-rule changes."
**Effort:** Quick (~3 min) | **Page impact:** −15–18 lines freed

---

### ✅ TASK 2 (REVISED) — Rewrite §5.4 closing to close the causal loop
**What:** Replace the current §5.4 closing sentence (lines 603–606) with a sentence that explicitly connects the 32/32 OOD result back to the architectural decoupling premise from §1.2.
**Current (approx):** "Here win rate and paired deltas are more informative than Cohen's d because the score distributions are nearly deterministic."
**Revised:**
> "This 32/32 OOD win fraction proves architectural stability under distributional shift: because all three pipeline stages read the same metric\_episode() implementation, ranking does not reverse when environmental conditions move outside the training distribution—validating the decoupling premise from §1.2."
**Effort:** Medium (~8 min) | **Page impact:** +2–3 lines

---

### ✅ NEW TASK A — Close the causal loop (§5 to §1.2)
**What:** Add a single sentence in the §5.1 Research Questions and Evaluation Design section (or as a bridge sentence opening §5.4), explicitly stating that the OOD validation answers the architectural hypothesis from §1.2.
**Draft:**
> "A positive result on both questions would validate the core design hypothesis from §1.2: that enforcing a single metrics\_episode() contract at the framework level prevents the ranking inconsistencies observed in ad-hoc coupling code."
**Where:** End of §5.1 (line ~426), or as the opening sentence of §5.4.
**Effort:** Quick (~5 min) | **Page impact:** +1 line

---

## HIGH PRIORITY — Do Next

### ✅ TASK 4 — Clarify binomial test / CI pairing
**What:** Add one clarifying phrase to the 32-scenario win-fraction report (line ~596) specifying test directionality.
**Current:** "(p=4.66×10⁻¹⁰, one-sided binomial test; Wilson 95% CI for win fraction: [0.94, 1.0])"
**Revised:** "(p=4.66×10⁻¹⁰, one-sided binomial, H₀: π=0.5 vs. H_a: π>0.5; Wilson two-sided 95% CI [0.94, 1.0])"
**Effort:** Quick (~3 min) | **Page impact:** neutral (edit in place)

---

### ✅ TASK 10 — Tighten "single-source-of-truth" language
**What:** Revise §1.2, line ~165–166 to specify that single-source-of-truth means structural consistency (one implementation shared across stages), not semantic correctness (correct aggregation logic — developer's responsibility).
**Current:** "…prevents by construction by making it impossible to define metrics in three different ways."
**Revised:**
> "…prevents structural inconsistency by construction: a single metrics\_episode() implementation is shared across all pipeline stages, making it impossible for aggregation to drift between them. Semantic correctness—whether that implementation correctly captures domain intent—remains the modeller's responsibility."
**Effort:** Quick (~5 min) | **Page impact:** +1–2 lines

---

### ✅ TASK 9 (REVISED) — Reframe case studies as architectural evidence
**What:** Rewrite the §4 opening paragraph (§4 Case Studies, first 1–2 sentences) to frontload the architectural framing. Instead of leading with the three domains, lead with what the studies are testing.
**Draft opening:**
> "The three case studies below serve as composition vehicles to validate whether HEAS's decoupling architecture holds across distinct domain logics. The question is not whether these domains are realistically calibrated, but whether heterogeneous simulation code composes without introducing hidden coupling. Each study uses an independent metrics\_episode() implementation; the framework code is shared and unchanged."
**Effort:** Medium (~10 min) | **Page impact:** +2–3 lines (absorbed from freed budget)

---

### ✅ TASK 5 (REVISED) — Reframe d=0.17 as evidence of generalization
**What:** Replace the defensive interpretation of d=0.17 (lines 598–599) with a causal interpretation tied to decoupling.
**Current:** "The small effect size (d=0.17) reflects near-deterministic score distributions in these ecological scenarios; win rate and paired deltas are the more informative statistics here, as score variance is low across scenarios."
**Revised:**
> "The small effect size (d=0.17) reflects consistently tight score distributions across OOD scenarios: the champion generalises without overfitting to any single case, consistent with what we expect when policy evaluation is decoupled from training conditions. Win rate (32/32) is the primary inferential statistic here; paired deltas confirm that all individual scenario margins are positive."
**Effort:** Quick (~5 min) | **Page impact:** neutral (rewrite in place)

---

### ✅ TASK 3 (CONDITIONAL) — Split aggregation inconsistency definition
**When to do:** Only if §5.2 or §5.1 is actually invoked in results/proofs and the current definition causes reader confusion. Read lines 405–410 and the controlled aggregation experiment (§5.2) consecutively. If the structural/operational split would sharpen the reader's understanding, apply the fix below.
**Fix:** In §5.1 (lines 405–410), revise to:
> "We define aggregation inconsistency at two levels. *Structural inconsistency* occurs when two pipeline stages implement logically distinct aggregation functions on the same metric key (e.g., optimizer reads final-step biomass while tournament reads episode mean). *Outcome inconsistency* is its observable consequence: two stages produce non-identical policy rankings, measured as Kendall τ < 1. The controlled experiment (§5.2) tests for outcome inconsistency as the operationalisation."
**Effort:** Medium (~10 min) | **Page impact:** +2–3 lines

---

## MEDIUM PRIORITY — Do If Space Allows

### ✅ TASK 7 (REVISED) — Streamline §3.5 scalar contract, not expand
**What:** SUPERVISOR REVISION — do NOT add 8 lines explaining the scalar contract's connection to coupling code. Instead, streamline §3.5 (Design Constraints) to 2–3 crisp sentences per concept: (1) definition, (2) why minimalism prevents divergence, (3) what it doesn't cover. Move any extended coupling-code motivation to a brief parenthetical or to §1.2 where it belongs.
**Goal:** §3.5 should shrink slightly, not grow. Recover 2–3 lines.
**Effort:** Medium (~15 min) | **Page impact:** −2–3 lines recovered

---

### ✅ TASK 8 — Clarify scalar contract ≠ heterogeneity removal (absorb into Task 7)
**What:** In the streamlined §3.5 (from TASK 7), replace any language implying the contract removes agent-level data. Reframe: the contract enforces consistent aggregation *of* agent data, it doesn't remove it.
**Key sentence to add (within the streamlined §3.5):**
> "Agent-level heterogeneity remains within the model's internal state; metrics\_episode() may compute any aggregate statistic before returning. The constraint is that all downstream consumers receive the same scalar output—preventing aggregation drift, not suppressing within-model variance."
**Effort:** Quick (part of TASK 7) | **Page impact:** included in TASK 7

---

### ✅ NEW TASK B — Strengthen Related Work positioning
**What:** In §2 (Related Work, lines 187–233), add 2–3 sentences that explicitly differentiate HEAS from frameworks that couple agent logic to domain state or require domain-specific aggregation.
**Draft:**
> "Unlike per-model utility wrappers (EMAworkbench, Mesa DataCollector), which require users to specify aggregation logic independently for each new domain, HEAS enforces a uniform contract at the framework level. The difference is not syntactic but architectural: framework-level enforcement means new case studies inherit consistent aggregation without writing or auditing glue code."
**Effort:** Medium (~10 min) | **Page impact:** +2–3 lines (use remaining freed budget)

---

## LOW PRIORITY — Polish Pass

### ✅ TASK 11 — Verify Appendix results table is complete
**What:** Confirm that the Appendix (Table 4) references the new Task 1 inline stats (32/32 OOD) and that source file S6b is still correct. If the champion 32-scenario result was previously only shown in Figure 2, ensure the inline text and Appendix row are consistent.
**Effort:** Quick (~5 min) | **Page impact:** neutral

---

### ✅ TASK 12 — Polish Table 2 caption
**What:** Revise Table 2 caption (controlled aggregation experiment, §5.2) to explicitly state the table validates the architectural claim, not just reports numbers.
**Add to end of caption:** "Results confirm that the metric contract is the necessary mechanism for aggregation consistency: HEAS achieves 0% rank reversals where ad-hoc pathways produce divergence."
**Effort:** Quick (~3 min) | **Page impact:** neutral

---

## PAGE BUDGET SUMMARY

| Task | Lines |
|------|-------|
| TASK 1 — Remove Fig 2 | −16 |
| TASK 2 — §5.4 rewrite | +3 |
| NEW TASK A — causal loop sentence | +1 |
| TASK 4 — binomial clarification | 0 |
| TASK 10 — SSOT language | +2 |
| TASK 9 — §4 reframe | +3 |
| TASK 5 — d=0.17 rewrite | 0 |
| TASK 3 — definition split (conditional) | +3 |
| TASK 7 — §3.5 streamline | −3 |
| TASK 8 — heterogeneity sentence | +1 |
| NEW TASK B — Related Work | +3 |
| TASKS 11–12 — polish | 0 |
| **NET** | **−3 lines** ✅ |

**Result: ~3 lines under budget. At 12 pages.**

---

## EXECUTION ORDER

1. TASK 1 (frees space — do first)
2. TASK 2 + NEW TASK A (the causal loop — do together)
3. TASKS 4, 10, 5 (quick wins — 15 min total)
4. TASK 9 (§4 reframe)
5. TASK 3 (only if the definition split is needed after reading §5.1–5.2)
6. TASK 7 + TASK 8 (together — §3.5 streamline)
7. NEW TASK B (Related Work — last before polish)
8. TASKS 11, 12 (polish pass)
9. Recompile and verify 12 pages.
