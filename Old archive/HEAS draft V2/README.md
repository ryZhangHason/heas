# HEAS Draft V2 — Paper Preparation Folder

**Target venue**: Winter Simulation Conference (WSC)
**Category**: Simulation Methodology / Framework Paper
**Submission type**: Full paper (up to 12 pages, IEEE format)

## Folder Contents

| File | Purpose |
|---|---|
| `00_OUTLINE.md` | Full section plan, argument map, page budget |
| `01_abstract.md` | Abstract (200 words) |
| `02_introduction.md` | Introduction — hook, gap, contribution, roadmap |
| `03_related_work.md` | Mesa, NetLogo, Repast, ABIDES — precise positioning |
| `04_framework.md` | HEAS architecture — Layer/Stream/Arena, metric contract, EA, tournament |
| `05_case_studies.md` | Eco + enterprise — composability demonstrations |
| `06_evaluation.md` | All experimental results with WSC-appropriate framing |
| `07_conclusion.md` | Conclusion + future work |
| `08_reviewer_qa.md` | Anticipated reviewer questions with responses |
| `09_tables_figures.md` | Paper-ready tables, figure captions, data |
| `10_writing_notes.md` | Framing guidance, words to avoid, WSC conventions |

## Key Framing Rules (do not violate)

1. **Never lead with domain numbers** (+176% welfare, +2% biomass). These are *evidence of pipeline correctness*, not domain findings. Frame every result as: *"HEAS's pipeline identified / validated / converged to..."*

2. **The Mesa comparison is the centerpiece argument**. Every reviewer will ask "why not just use Mesa?" Answer first: 97% LOC reduction, zero divergence risk, zero boilerplate for EA+tournament+CI.

3. **Case studies are demonstrations, not scientific claims**. The ecological and enterprise models are *vehicles for demonstrating composability*. Never claim biological or economic validity.

4. **Simple outperforming NSGA-II is a feature, not a bug**. It demonstrates that HEAS is algorithm-agnostic — researchers swap optimizers without framework changes.

5. **Tournament noise stability is a positive result**. τ=1.0 at σ=1, graceful degradation — report this as a quantified reliability bound, not a limitation.
