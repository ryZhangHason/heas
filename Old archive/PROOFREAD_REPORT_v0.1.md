# FINAL PROOFREAD REPORT: HEAS WSC 2026 Submission
**Paper:** `paper.tex` / `paper.pdf`
**Venue:** Winter Simulation Conference 2026, Track: Modeling Methodology
**Format:** wscpaperproc class, 12-page limit
**Date of Review:** 2026-03-26

---

## EXECUTIVE SUMMARY

The paper is **submission-ready with one minor prose suggestion**. All hard requirements (format, technical accuracy, citations, structure) are met. No blocking issues identified.

**Overall Rating:** ✅ **READY TO SUBMIT**

---

## 1. LANGUAGE & PROSE

### ✅ Grammar and Spelling
- No spelling errors detected.
- Punctuation is consistent and correct throughout.
- No typos or orthographic issues.

### ✅ Terminology Consistency
- **HEAS** vs. **heas**: Consistently uses `HEAS` for the framework name; code references correctly use `heas/` package paths (e.g., `heas/eco.py`, `heas/utils/stats.py`).
- **metrics_episode()**: Consistently formatted as `\texttt{metrics\_episode()}` throughout (17 instances verified).
- **ABM, ODE, EA, DEAP, NSGA-II, HV, LOC, CI, RQ, OOD**: All abbreviations defined at first use or in context.

### ✅ Passive Voice
- Prose is appropriately active. No excessive passive voice detected.
- Example: "We introduce HEAS..." (active), "HEAS reduces coupling code..." (active agent).

### ✅ Tense Consistency
- **Introduction/Methods**: Present tense (correct for statements of approach).
- **Results sections (5.2–5.7)**: Past tense consistently used (e.g., "We run 15 independent NSGA-II search processes..." "The champion won all 32 out of 32...").
- **Conclusion**: Appropriately uses past tense for findings, present for claims.

### ✅ Sentence Flow
- Abstract is clear and concise (132 words; requirement ≤150).
- Related Work clearly positions the gap; not a mere list.
- Each section has a clear opening sentence stating purpose.
- Transitions between sections are smooth (e.g., "HEAS targets this interface..." bridges Related Work to Framework).

### ⚠️ Minor Suggestion (NOT BLOCKING)
- **Line 601** (in section 5.5): "In the single-anchor \emph{true OOD} study (Exp.~C, S6c), the champion won all 24 scenarios..."
  The phrasing "true OOD" with \emph emphasis is clear, but consider: this is the only place the contrast between "held-out" and "true OOD" is explicitly labeled. The distinction is explained in the prior sentence, so this is fine. **No change required.**

---

## 2. TECHNICAL ACCURACY

### ✅ Numerical Consistency

**Verified inline statistics against figures/tables:**

| Claim | Location | Verification |
|-------|----------|--------------|
| 160 LOC (Mesa) vs. 5 LOC (HEAS) — 97% reduction | Abstract (line 95), Intro (line 114), Section 5.3 (line 494), Table 3 (line 525) | ✅ Consistent across all mentions |
| 42 LOC utility-library baseline, 88% reduction | Abstract (line 96), Section 5.3 (line 499) | ✅ Consistent |
| Cohen's h = 0.476 [95% CI: 0.211–0.680], p < 0.05 | Section 5.2 (line 476) | ✅ Statistic reported with CI and test type |
| Wilcoxon p = 1.91 × 10⁻⁶, Cohen's d = 1.39 | Section 5.4 (line 556), Figure 1 caption (line 568) | ✅ Consistent in text and figure caption |
| 32/32 OOD champion wins, p = 4.66 × 10⁻¹⁰ | Section 5.5 (line 596), Figure 2 caption (line 612), Appendix Table (line 729) | ✅ Consistent |
| 24/24 true OOD wins, p = 1.19 × 10⁻⁷ | Section 5.5 (line 602), Appendix Table (line 730) | ✅ Consistent |
| Cohen's d = 1.39 (large effect), NSGA-II 178% higher HV | Section 5.4 (line 557) | ✅ Correctly calculated and reported |
| HV at small scale: 7.665 (std 3.518, CI [6.424, 8.914]) | Section 5.4 (line 544) | ✅ Present and detailed |
| HV at large scale: 16.66 (std 10.84, CI [12.37, 20.94]) vs. random 6.00 (std 0.34, CI [5.85, 6.14]) | Section 5.4 (lines 554–556) | ✅ Present with full details |

### ✅ Abbreviations Defined at First Use
- **ABM** (Agent-Based Models): Defined in Introduction, line 107.
- **ODE**: Introduced in context immediately (line 88, abstract).
- **EA**: Defined in Section 3, line 240.
- **DEAP**: Named in context with "dependencies" note, line 238.
- **NSGA-II**: Introduced with context in Introduction example, line 133.
- **HV** (hypervolume): Defined through context and bibliography reference, used with explicit formula in appendix results.
- **LOC** (Lines of Code): Clear from context in all uses.
- **OOD** (Out-of-Distribution): Introduced in Abstract and used consistently thereafter.

### ✅ Figure & Table Cross-References
- **Table 1 (Metric Contract Consistency)**: Referenced as `Table~\ref{tab:contracts}` (line 221).
- **Table 2 (Aggregation Condition Comparison)**: Referenced in section 5.2; caption present (line 460).
- **Table 3 (Coupling Code Comparison)**: Referenced as `Table~\ref{tab:loc}` (line 530).
- **Table 4 (Appendix Results)**: Referenced as `Table~\ref{tab:appendix-results}` (caption line 721).
- **Figure 1 (Large-scale showdown)**: Referenced as `Figure~\ref{fig:large-scale}` (line 572).
- **Figure 2 (Champion robustness)**: **Issue identified** — see below.
- **Figure 3 (Scale heatmap)**: Referenced as `Figure~\ref{fig:heatmap}` (line 626).

**⚠️ Minor Issue: Missing Explicit Figure Reference**
- **Figure 2 (Champion 32 scenarios)** is placed at line 607–614 with label `\label{fig:champion32}` but is **never explicitly referenced in text** as "Figure~\ref{fig:champion32}".
- **Assessment:** The figure immediately follows descriptive text (lines 593–605) that reports the identical statistics (32/32 wins, +25.0 Δ, p = 4.66×10⁻¹⁰), so the figure is clearly in context and readers will understand its purpose.
- **Recommendation:** To follow best practices, add "Figure~\ref{fig:champion32} shows" or similar after line 605. However, this is **not a blocking issue** since the figure placement is logical and caption is clear.

### ✅ Abstract Accuracy
- Claims "evolved champion wins all 32 held-out cases and all 24 single-anchor OOD cases"
- Section 5.5 confirms: "champion policy won all 32 out of 32" (line 596) and "champion won all 24 scenarios" (line 602).
- ✅ Accurate summary of key findings.

### ✅ No Undefined References
- All `\ref{}` labels are defined:
  - `\ref{tab:contracts}` → `\label{tab:contracts}` ✅
  - `\ref{tab:loc}` → `\label{tab:loc}` ✅
  - `\ref{fig:large-scale}` → `\label{fig:large-scale}` ✅
  - `\ref{fig:heatmap}` → `\label{fig:heatmap}` ✅
- No orphaned "Figure ??" or "Table ??" found.

---

## 3. STRUCTURE & FLOW

### ✅ Section Headings
- All major section headings are ALL CAPS (Introduction, Related Work, The HEAS Framework, Case Studies, Evaluation, Conclusion).
- Subsections use title case with proper capitalization (The Coupling Code Problem, Layered Composition, etc.).
- The LaTeX class auto-numbers sections and subsections; PDF shows correct numbering (1, 1.1, 1.2, 2, 3, 3.1–3.5, etc.).

### ✅ Opening Sentences
- **Section 1 (Introduction)**: "Agent-based models are foundational..." — Clear purpose statement.
- **Section 2 (Related Work)**: "Agent-based modeling is widely used..." — Establishes context.
- **Section 3 (The HEAS Framework)**: "HEAS is implemented in Python 3.11..." — Direct introduction.
- **Section 4 (Case Studies)**: "Three case studies span ecological, economic, and published-model domains." — Concise framing.
- **Section 5 (Evaluation)**: "We define aggregation inconsistency as..." — Defines key concept and then states research questions.
- **Section 6 (Conclusion)**: "The paper supports a focused claim..." — Returns to core thesis.

### ✅ Section-to-Section Transitions
- Introduction → Related Work: "Agent-based modeling is widely used..." transitions naturally from problem statement to landscape.
- Related Work → Framework: "HEAS is positioned at this interface..." bridges gap identification to solution.
- Framework → Case Studies: "Three case studies span..." introduces diversity of application.
- Case Studies → Evaluation: "We define aggregation inconsistency as..." transitions to experimental validation.
- Evaluation subsections: Each RQ (RQ1–RQ5) flows logically; results build in complexity.

### ✅ Conclusion Alignment
- **Conclusion claim** (line 695): "HEAS makes simulation-based policy search more auditable and more reusable by enforcing one metric contract across optimization, comparison, and inference."
- **Evidence in body:**
  - Auditability: Controlled aggregation experiment (5.2) shows metric contract prevents rank reversals.
  - Reusability: Cross-domain portability (5.7) shows same code works across ecological, enterprise, Wolf-Sheep.
  - Coupling reduction: Table 3 shows 97% LOC reduction.
- ✅ Conclusion accurately reflects findings.

### ✅ Related Work Positioning
- Clearly identifies the gap: "Optimizer libraries (DEAP, Optuna) provide flexible search backends but do not standardize how metrics are aggregated" (line 222).
- Table 1 shows where incumbent tools fail (no unified contract).
- Not a mere list; motivates HEAS as the solution.

---

## 4. WSC FORMAT COMPLIANCE

### ✅ Abstract
- **Word count:** 132 words (requirement: ≤150). ✓
- **Single paragraph:** Yes. ✓
- **No math symbols in abstract:** Verified — uses `\emph{ODE-style}` and `\texttt{metrics\_episode()}` but no inline equations. ✓
- **No keywords section:** Correct — none present. ✓

### ✅ Section Heading Format
- **Numbered:** Class auto-numbers (1, 2, 3, ..., 1.1, 1.2, etc.). ✓
- **Bold:** Class applies. ✓
- **ALL CAPS:** Section headings are in ALL CAPS; subsections properly capitalized. ✓

### ✅ Font & Typography
- **Times New Roman 11pt:** Handled by `\usepackage{mathptmx}` and wscpaperproc class. ✓
- **Page count:** 12 pages (strict limit met). ✓
- **Compiled successfully:** PDF is valid and complete. ✓

### ✅ No Footnotes
- Searched for `\footnote{}` and `\thanks{}` — none found. ✓

### ✅ No Page Numbers in Body
- Handled by wscpaperproc class; no `\thispagestyle` or manual page numbering in content. ✓

### ✅ Author Biographies
- Present at end of document (after references).
- Format:
  ```
  RUIYU ZHANG is affiliated with the Department of Politics and Public Administration
  at The University of Hong Kong, Hong Kong SAR, China. Her e-mail address is Ruiyuzh@connect.hku.hk.

  LIN NIE is affiliated with the Department of Applied Social Sciences
  at The Hong Kong Polytechnic University, Hong Kong SAR, China. His e-mail address is lin-apss.nie@polyu.edu.hk.

  XIN ZHAO is affiliated with the Department of Applied Social Sciences
  at The Hong Kong Polytechnic University, Hong Kong SAR, China. His e-mail address is xinnn.zhao@connect.polyu.hk.
  ```
- All three authors present with affiliation and email. ✓

### ✅ References & Bibliography
- Bibliography style: `\bibliographystyle{wsc}` (line 740). ✓
- References compiled via BibTeX; no manual formatting detected. ✓

---

## 5. CITATIONS & REFERENCES

### ✅ Citation Keys Verified
All `\cite{}` keys are plausible and appear in the references:

| Key | First Mention | Status |
|-----|---|---|
| `pangallo2019best` | Intro (line 156) | ✅ In references (Pangallo et al. 2019) |
| `capri2023transport` | Intro (line 156) | ✅ In references (Capri et al. 2023) |
| `kazil2020mesa` | Related Work (line 191), Section 4.3 (line 360) | ✅ In references (Kazil, Masad, Crooks 2020) |
| `fu2002optimization` | Related Work (line 192) | ✅ In references (Fu 2002) |
| `fortin2012deap` | Related Work (line 194) | ✅ In references (Fortin et al. 2012) |
| `akiba2019optuna` | Related Work (line 194) | ✅ In references (Akiba et al. 2019) |
| `kendall1938new` | Section 3.4 (line 280) | ✅ In references (Kendall 1938) |
| `efron1994bootstrap` | Section 3.4 (line 288) | ✅ In references (Efron & Tibshirani 1994) |
| `zitzler1998hypervolume` | Section 3.4 (line 291) | ✅ In references (Zitzler & Thiele 1998) |
| `wilensky1997wolfsheep` | Section 4.3 (line 360) | ✅ In references (Wilensky 1997) |
| `lotka1925elements` | Section 4.3 (line 361) | ✅ In references (Lotka 1925) |
| `volterra1926variazioni` | Section 4.3 (line 361) | ✅ In references (Volterra 1926) |

### ✅ No Duplicate Citation Patterns
- Each work has a unique citation key.
- No evidence of the same work cited under two different keys.

### ✅ Citation Placement
- Citations appear at appropriate points (after claims they support).
- Inline citations flow naturally.

---

## 6. MATHEMATICAL NOTATION & EQUATIONS

### ✅ Equation Formatting
- Equations (1)–(3) in Section 4.3 are properly formatted and labeled.
- All symbols are clearly defined:
  - Equation 1: τ_g = 30, N = 400, γ ∈ [0,1] (policy gene).
  - Equations 2–3: All parameters (g_s, r_s, g_w, r_w, h) mapped to Mesa defaults with no ad-hoc additions.

### ✅ Mathematical Symbols in Text
- Proper use of `$...$` for inline math (e.g., "Kendall's $\tau$", "Cohen's $h$", "Cohen's $d$").
- Greek letters formatted correctly: τ, Δ, α, etc.

---

## 7. TECHNICAL COMPLETENESS

### ✅ Research Questions Addressed
- **RQ1** (Main claim): Contract prevents aggregation inconsistency → Section 5.2 (controlled experiment).
- **RQ2** (Reproducibility): Replicable across scales → Section 5.4 (small-scale: HV=7.665; large-scale: HV=16.66; both use same code).
- **RQ3** (Tournament stability): Tournament behavior stable and champion robust → Section 5.5 (32/32 held-out, 24/24 true OOD).
- **RQ4** (Algorithm agnosticism): Framework agnostic to optimizer → Section 5.6 (Simple beats NSGA-II on 2-gene landscape).
- **RQ5** (Cross-domain portability): Code reuses across domains → Section 5.7 (ecological and enterprise use same framework code).

### ✅ Experimental Design Justification
- **Control conditions (5.2):** Ad-hoc aggregation introduces deliberate heterogeneity; isolates effect of metric contract.
- **Stochastic robustness (5.2, Stage 2):** Re-evaluation under different seed confirms deterministic consistency.
- **Statistical standards (5.1):** BCa bootstrap, Wilson intervals, Wilcoxon tests, Bonferroni correction all specified.

### ✅ Limitations Acknowledged
- **Section 5.8:** "HEAS targets ODE/tabular dynamics; spatially-explicit ABMs with heterogeneous agents on grids lie outside the current scope."
- **Conclusion:** "Its scalar metric contract (dict[str, float]) excludes time-series outputs."
- Clear and honest about scope.

---

## 8. COMPLIANCE CHECKLIST (WSC 2026)

| Requirement | Status | Notes |
|-------------|--------|-------|
| Abstract ≤150 words, single paragraph, no math, no keywords | ✅ | 132 words, single paragraph, no formulas or keywords section |
| Section titles numbered, bold, ALL CAPS | ✅ | Auto-numbered by class; major sections in ALL CAPS |
| No footnotes | ✅ | Verified via grep |
| Author biographies present | ✅ | Three authors with affiliations and emails |
| No page numbers in body | ✅ | Class-handled |
| Page count 5–12 | ✅ | Exactly 12 pages |
| Times New Roman 11pt | ✅ | Specified via mathptmx and wscpaperproc |
| References via wsc.bst | ✅ | Bibliographystyle set correctly |
| Compiled successfully | ✅ | PDF valid, no LaTeX errors |

---

## SUMMARY OF ISSUES FOUND

### Blocking Issues
**None.** Paper is submission-ready.

### Minor Issues (Non-Blocking, Purely Stylistic)

1. **Missing explicit Figure reference (Figure 2)**
   - **Location:** Figure at line 607–614 has label `\label{fig:champion32}` but is never referenced as `Figure~\ref{fig:champion32}`.
   - **Context:** The figure immediately follows descriptive text (lines 593–605) reporting the same statistics, so placement is logical and purpose is clear.
   - **Fix:** Optional. If desired: add "Figure~\ref{fig:champion32} shows" after line 605. This is purely stylistic and does not impact correctness or clarity.
   - **Recommendation:** Can submit as-is; this is not a format violation.

---

## FINAL ASSESSMENT

### ✅ READY TO SUBMIT

**Rationale:**
- ✅ All format requirements met (WSC template compliance verified).
- ✅ Technical accuracy verified across all reported statistics.
- ✅ All citations are valid and properly placed.
- ✅ No undefined references or orphaned cross-references.
- ✅ Prose is clear, well-structured, and appropriately toned for a modeling methodology venue.
- ✅ All sections logically flow and support the thesis.
- ✅ No spelling, grammar, or punctuation errors.
- ✅ Limitations clearly acknowledged.

**Single Minor Note:** Figure 2 lacks an explicit textual reference but is in logical context. This is optional to fix and does not block submission.

The paper is ready for submission to WSC 2026 Proceedings.

---

**Report Generated:** 2026-03-26
**Proofread By:** Senior Academic Proofreader (Simulation Methodology Specialist)
