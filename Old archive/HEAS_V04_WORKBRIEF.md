# HEAS v0.4 Work Brief
**Supervisor: Project Lead | Date: 2026-03-26**

---

## EXECUTION OVERVIEW

35 coordinated changes across text, experiments, and references.
Critical path: PART A (text) → PART B (experiments) → PART C (references) → Sign-off.
Estimated effort: ~15.5 hours total (text ~6h, experiments ~8h, references ~30min).

---

## PART A — TEXT-ONLY EDITS (14 items, execute immediately)

### ABSTRACT

**A1. Replace "independently written code"**
- Old: "...recompute the same outcome metric...with independently written code..."
- New: "...recompute the same outcome metric...using independently implemented aggregation logic at each pipeline stage..."

---

### §1 INTRODUCTION

**A2. Delete first sentence of §1.2 (Contributions)**
- Locate and DELETE the opening sentence of §1.2 that verbatim repeats the abstract contribution claim.

**A3. Add structural vs. semantic paragraph in §1.2**
- Insert after the core contribution claims:
> "HEAS enforces structural consistency: the same dispatch-time metric contract is verified across all pipeline stages. It does not enforce semantic validity: an incorrect but consistently applied metrics_episode() will pass contract verification. Semantic correctness—whether the metric computation is logically sound for the scientific question—remains the modeller's responsibility."

---

### §2 RELATED WORK

**A4. Replace Janssen lineage closing paragraph in §2**
- Replace the current closing paragraph (which references Janssen 2008) with:
> "The documentation contract tradition evolved as follows: ODD (Grimm et al. 2006) established author-declared compliance—static and non-verifiable at execution time. Thiele & Grimm (2015) formalized replication as community enforcement, but detection of failure remains post-hoc. Grimm & Railsback (2012) extended contracts to outcome pattern matching, yet this too is researcher-driven and post-hoc. Each framework advanced the contract tradition while remaining prescriptive and external to the execution engine. Our approach closes this gap."

**A5. Add new §2.2 subsection: "The Contract-as-Methodology Tradition in ABM" (~400 words)**
- Insert as a new subsection after §2.1.
- Four paragraphs:
  1. ODD (Grimm et al. 2006) — documentation contract, author-declared, non-machine-verifiable at execution time
  2. Thiele & Grimm (2015) — replication as community enforcement, but post-hoc only, cannot prevent divergence during a run
  3. POM / Grimm & Railsback (2012) — outcome specification, researcher-driven and post-hoc; divergent run completes before inconsistency detected
  4. Closing: "Each framework advanced the contract tradition while remaining prescriptive. HEAS closes the final gap: by encoding the metric contract as a type-checked callable signature verified at dispatch time, divergence becomes provably impossible on all contract-verified execution paths—not by documentation obligation, but by construction."

---

### §3 FRAMEWORK

**A6. Add clarification sentence to §3.5 Pydido paragraph**
- At end of Pydido paragraph, add:
> "Pydido provides a prototype implementation of contract-based aggregation design; however, the Pydido framework itself is not evaluated in this paper."

---

### §4 CASE STUDIES

**A7. Reframe §4.3 Wolf-Sheep title and opening**
- New title: "Wolf-Sheep: A Methodological Composition Vehicle for Contract Enforcement Under Performance Degradation"
- New opening sentence before existing content: "The Wolf-Sheep predator-prey model serves as a methodological composition vehicle demonstrating contract enforcement in scenarios where algorithmic performance degrades — specifically, where the optimization landscape favours simpler search strategies over NSGA-II."

---

### §5 EVALUATION

**A8. Add RQ→Section mapping table in §5.1**
- Insert after RQ definitions (now reduced to 3):

| Research Question | Evaluation Section |
|---|---|
| RQ1: Does the metric contract prevent aggregation divergence? | §5.4 Controlled Aggregation Experiment |
| RQ2: Is the framework reproducible across scales and domains? | §5.6 Multi-Scale + §5.9 Cross-Domain |
| RQ3: Does the champion policy generalize out-of-distribution? | §5.7 OOD Champion Robustness |

**A9. Fix RQ label in §5.6 opening**
- Change whatever RQ label is used (currently wrong) to: "For RQ2, we test whether..."

**A10. Fix RQ label in §5.7 opening**
- Change to: "Building on RQ2, we validate out-of-distribution champion robustness (RQ3)..."

**A11. Fix RQ label in §5.8 opening**
- Change to: "We test whether framework usefulness depends on any single optimizer (a secondary validation question not assigned a primary RQ)..."

**A12. Add Bonferroni pre-specification in §5.5 or §5.8** *(flag for PART B values)*
- Insert before comparison results:
> "Multiple comparisons were pre-specified at α = 0.05 (FWER). Bonferroni correction threshold: α_corrected = 0.05 / [N] = [value]. Results report both raw p-values and Bonferroni-corrected significance."
- [N] and [value] to be filled in after PART B re-run.

**A13. Add hierarchical unit structure declaration in §5.4**
- Insert before CI results:
> "Unit structure: [X] optimization runs × [Y] tournament evaluation stages × [Z] statistical validation cohorts = [n_total] total comparisons."
- Fill in actual values from experiment protocol.

---

### §6 CONCLUSION

**A14. Replace verbatim opening in §6 with synthesis**
- Old: verbatim repeat of abstract/§1.2 contribution claim
- New: "The controlled aggregation experiment with the tabular ecological model provides direct evidence that runtime-enforceable metric contracts prevent silent aggregation divergence across non-deterministic execution stages. HEAS reduces coupling code by 97% relative to Mesa-based baselines, eliminates rank reversals in the controlled experiment, and transfers across ecological, enterprise, and mean-field ODE domains without rewriting framework logic."

---

## PART B — EXPERIMENT RE-RUNS (2 items)

**Execute ONLY after PART A is complete and paper compiles cleanly.**

**B1. REDESIGN STAGE 2 — Non-Deterministic Aggregation**
- Problem: Current Stage 2 forces τ=1.0 (determinism). Both HEAS and ad-hoc achieve τ=1.000, proving determinism prevents divergence — not contracts.
- Fix: Re-run Stage 2 with τ_tournament = τ_optimization (same non-zero stochasticity as Stage 1).
- Expected result: Contracts reduce divergence even when results vary by seed.
- After re-run: Replace §5.4 Stage 2 paragraph with new results.
- Time: ~4–6 hours.

**B2. BONFERRONI CORRECTION RE-RUN**
- Count all pairwise comparisons in results (n = ?).
- Set α_corrected = 0.05 / n.
- Re-report all p-values as: raw p + Bonferroni-corrected significance.
- Fill in [N] and [value] placeholders from A12.
- Time: ~1–2 hours (mostly recalculation and table updates).

---

## PART C — REFERENCES.BIB UPDATES (4 items)

**C1. Add Thiele & Grimm (2015)**
```bibtex
@article{thiele2015replicating,
  author  = {Thiele, Jan C. and Grimm, Volker},
  title   = {Replicating and breaking models: good for you and good for ecology},
  journal = {Oikos},
  year    = {2015},
  volume  = {124},
  number  = {6},
  pages   = {691--696},
  doi     = {10.1111/oik.02170}
}
```

**C2. Add/verify Grimm & Railsback (2012)**
```bibtex
@article{grimm2012pattern,
  author  = {Grimm, Volker and Railsback, Steven F.},
  title   = {Pattern-oriented modelling: a 'multi-scope' for predictive systems ecology},
  journal = {Philosophical Transactions of the Royal Society B},
  year    = {2012},
  volume  = {367},
  pages   = {298--310},
  doi     = {10.1098/rstb.2011.0180}
}
```
- Check if already present under another key before adding.

**C3. Verify Janssen (janssen2008towards)**
- Search paper body after §2 for any Janssen citation.
- If NOT cited after §2: remove janssen2008towards from references.bib.
- If cited elsewhere: keep.

**C4. Full compile check**
- Run: `pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper`
- All citations must resolve. No missing-citation warnings.

---

## SUPERVISOR SIGN-OFF CHECKLIST

Submit v0.4 only when ALL of these pass:

### PART A complete
- [ ] A1: Abstract uses "independently implemented aggregation logic at each pipeline stage"
- [ ] A2: §1.2 first verbatim sentence deleted
- [ ] A3: §1.2 structural vs. semantic paragraph present
- [ ] A4: §2 lineage closing replaced (ODD→Thiele & Grimm→POM→HEAS)
- [ ] A5: §2.2 subsection present (~400 words, 4 paragraphs, 3 citations)
- [ ] A6: §3.5 Pydido clarification sentence added
- [ ] A7: §4.3 title and opening reframed to "methodological composition vehicle"
- [ ] A8: §5.1 RQ→section mapping table present
- [ ] A9–A11: §5.6, §5.7, §5.8 RQ labels corrected
- [ ] A12: §5.5 or §5.8 Bonferroni pre-specification statement (with filled-in values from B2)
- [ ] A13: §5.4 hierarchical unit structure declared
- [ ] A14: §6 opens with synthesis, not verbatim repeat

### PART B complete
- [ ] B1: Stage 2 re-run with non-deterministic τ; new results in §5.4
- [ ] B2: All p-values report raw + Bonferroni-corrected; pre-specified in text

### PART C complete
- [ ] C1: Thiele & Grimm 2015 in references.bib
- [ ] C2: Grimm & Railsback 2012 in references.bib (or confirmed existing)
- [ ] C3: Janssen status verified
- [ ] C4: Clean compile, no citation warnings

### Final quality
- [ ] Paper compiles to ≤12 pages
- [ ] No verbatim abstract/§1.2 repeats remain anywhere
- [ ] Tone is professional and measured — no overclaiming
- [ ] All tables and figures numbered and referenced correctly

---

## TIMELINE

| Phase | Items | Est. Time |
|-------|-------|-----------|
| PART A (text) | A1–A14 | 6 hours |
| PART B (experiments) | B1, B2 | 8 hours |
| PART C (references) | C1–C4 | 30 min |
| Final compile + review | Checklist | 1 hour |
| **Total** | | **~15.5 hours** |

**Begin PART A immediately. Report to Supervisor when PART A is compiled clean.**
