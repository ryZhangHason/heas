# Section 10 — Writing Notes and Style Guide

This file contains framing rules, vocabulary choices, and WSC-specific
conventions for the HEAS paper. Read before editing any section draft.

---

## Core Framing Rules (Non-Negotiable)

### Rule 1: This is a framework paper, not a domain paper.

The ecological and enterprise case studies are *composition demonstrations*.
They show that HEAS can wire heterogeneous Streams into a reproducible pipeline
— they do not make claims about ecology or economics.

**Bad**: "HEAS-evolved policies increased ecosystem biomass by 18% compared
to the reference policy."
**Good**: "The EA pipeline identified a Pareto-dominant policy configuration;
the tournament confirmed its advantage across 32 independent scenario
instantiations."

Why: WSC reviewers are simulation methodologists. They will penalize papers
that present domain results ("+18% biomass") as if they are scientifically
validated ecological findings. The correct framing is: "This number demonstrates
that the framework's end-to-end pipeline works correctly, not that we have
discovered an ecological principle."

---

### Rule 2: "Structural guarantee" vs "best practice."

HEAS's key claim is that metric consistency is *enforced by the framework*,
not *maintained by developer discipline*.

**Bad**: "Mesa users who follow best practices can avoid metric divergence."
**Good**: "In HEAS, metric divergence is structurally impossible: both the
EA and the tournament read `ep_metrics['agg.mean_biomass']` from the same
`metrics_episode()` return value."

Use "structural guarantee" at least twice: once in the abstract, once in §6.1.
Never say "HEAS prevents metric divergence by convention" — that is what Mesa
provides.

---

### Rule 3: Never say "novel."

WSC reviewers deduct for "our novel framework." The word signals insecurity.
Instead: describe the architectural decision and let the contrast with Mesa
speak for itself.

**Bad**: "We present a novel framework for..."
**Good**: "We present HEAS, a framework that addresses the coupling code
problem through four architectural commitments: ..."

---

### Rule 4: The Mesa implementation is "not a strawman."

This phrase must appear verbatim in §6.1. Without it, reviewers will assume
the Mesa implementation was made intentionally bad.

Required sentence: "This is not a strawman — it is the implementation a
Mesa-proficient researcher would produce."

What "best practices" means in this context: DataCollector for metric logging,
a separate episode runner function, ProcessPoolExecutor for parallel evaluation,
and individual fitness and tournament scoring functions. The HEAS paper's Mesa
implementation uses ALL of these.

---

### Rule 5: Honest about limitations.

WSC is a methodology conference. Reviewers respect papers that acknowledge
where their framework does NOT apply. List Mesa's genuine strengths:

- Spatial simulation (grid, networks): Mesa wins
- Visualization (SolaraViz): Mesa wins, HEAS has nothing comparable
- Single-run exploratory modeling: Mesa wins (lower ceremony)
- Policy search + tournament + CI pipeline: HEAS wins structurally

The paper should include a sentence: "For spatially-explicit ABMs with rich
agent interactions and visualization needs, Mesa remains the preferred choice.
HEAS complements rather than replaces Mesa."

---

## Vocabulary

### Words to use:
- "coupling code" (not "glue code", "boilerplate", or "plumbing")
- "structural guarantee" (not "automatic", "built-in", "enforced")
- "metric contract" (not "interface", "API", "protocol")
- "composition demonstration" (for case studies)
- "optimizer-agnostic" (not "flexible", "extensible", "modular")
- "namespaced keys" (not "dictionary", "string keys")
- "Pareto front" (not "optimal set", "frontier")

### Words to avoid:
- "novel" (WSC reviewers penalize this)
- "glue code" (informal; use "coupling code")
- "eliminates" (too absolute; use "reduces" or "removes the need for")
- "automatically" (vague; say what is automatic and why)
- "easy" (condescending; describe the API and let simplicity speak)
- "powerful" (marketing language; show power through LOC counts)
- "state-of-the-art" (only if benchmarked against it)
- "trivially" (implies other work is not serious)

---

## WSC-Specific Conventions

### Page limits: 12 pages IEEE format

Current plan: 11.0 pages. Budget breakdown:
- Abstract: 0.2
- Introduction: 1.0
- Related Work: 0.8
- Framework: 2.5
- Case Studies: 1.5
- Evaluation: 3.5
- Conclusion: 0.5
- References: 1.0

If tight, cut in this order:
1. §3.2 (non-DEAP optimization frameworks) → reduce to 2 sentences each
2. §6.4 (algorithm ablation) → cut Table 6 to 2-row if needed
3. §7.3 (limitations) → compress to 1 sentence per item
Never cut: §6.1 (Mesa comparison), §6.3 (tournament validation), Table 1.

### IEEE single-column format notes:
- Figures: max 3.5 inches wide for single-column, 7.0 inches for double-column
- Tables: use `\toprule`, `\midrule`, `\bottomrule` (booktabs style)
- Code blocks: 8pt monospace, no line numbers unless necessary
- Math: inline ($...$) preferred over display ($$...$$) for simple expressions

### Citation style: IEEE numbered

```bibtex
@inproceedings{kazil2020mesa,
  title={Utilizing Python for Agent-Based Modeling: The Mesa Framework},
  author={Kazil, Jackie and Masad, David and Crooks, Andrew},
  booktitle={Social, Cultural, and Behavioral Modeling},
  year={2020}
}
```

Use `\cite{kazil2020mesa}` in text. The WSC proceedings use IEEE format.

### Figure captions go below figures. Table captions go above tables.

---

## Section-by-Section Style Notes

### Abstract
- Target: 200 words (Draft 1) or 150 words (Draft 2)
- The 97% figure must appear in the abstract — it is the headline claim
- Last two sentences must summarize validation, not describe future work
- Do NOT include biological/economic numbers ("+18% biomass") in abstract

### Introduction
- First paragraph: establish that policy search is common and requires three steps
- Second paragraph: make coupling code problem concrete (Mesa scenario)
- Do NOT say "in this paper we present" in the first paragraph
- The 160 vs 5 LOC comparison belongs in the introduction as a forward reference
  ("§6 reports a direct LOC comparison showing..."), not withheld until §6
- Section 1.4 (paper organization) should be a single paragraph, not bullet points

### Related Work
- Be precise about what each framework was designed for; never say "limited"
- Gap table (Table 7) is the punchline of §3 — place it at the END of §3
- One positioning sentence at end of §3: "HEAS occupies the intersection..."

### Framework Section (§4)
- Lead with a code example, not a diagram
- The metric contract should be shown as a 3-step code block (same key in EA,
  tournament, CI) — this is the "aha" moment for reviewers
- Use `\lstlisting` or `\verbatim` for code blocks, 8pt font
- Layer contract should be a compact Python class signature, not full code
- Do not explain how Python decorators work — assume reader knows Python

### Case Studies (§5)
- Both case studies must explicitly state "composition demonstration" framing
- For ecological: mention K=1000 correction story briefly (shows framework
  helped detect degeneracy) — full story belongs in §6.2
- For enterprise: mention that the 5-layer hierarchy is structurally different
  from the ecological 5-stream Arena (different hierarchy depth)

### Evaluation (§6)
- §6.1 must come first — it answers the foundational "why not Mesa" question
- "This is not a strawman" must appear in §6.1 first paragraph
- §6.2: Include the K=1000 correction story as evidence that HEAS's CI reveals
  bugs that single-run studies miss
- §6.3: The 4/4 voting rule agreement is the key result, not the noise curve.
  State it first: "All four rules agree in 100% of (scenario, repeat) pairs."
  Then discuss noise stability as additional robustness evidence.
- §6.4: Never say "NSGA-II performs poorly" — say "simple hillclimbing
  outperforms NSGA-II on this low-dimensional landscape, confirming optimizer-
  agnosticism is practically useful"

### Conclusion (§7)
- Do NOT restate contributions verbatim from §1.3
- Summary paragraph: confirm that contributions were validated with specific
  numbers ("97% LOC reduction confirmed in direct comparison")
- Limitations: be specific and honest (parallelism startup cost, no spatial
  simulation)
- Future work: focus on MesaLayerAdapter as highest-value extension

---

## What Must Be Verifiable

Everything in the paper must be reproducible from the repository:

| Claim | Script | Output file |
|---|---|---|
| Mesa 160 LOC vs HEAS 5 LOC | `experiments/mesa_vs_heas.py --exp A` | `results/mesa_vs_heas/exp_a_loc.json` |
| Eco HV mean=7.665, CI=[6.424,8.914] | `experiments/eco_stats.py --n-runs 30` | `results/eco_stats/summary.json` |
| Ent HV mean=4317.5, CI=[4311.2,4326.0] | `experiments/ent_stats.py --n-runs 30` | `results/ent_stats/summary.json` |
| 4/4 voting rules 100% agree | `experiments/tournament_stress.py --part 1` | `results/tournament_stress/agreement_matrix.csv` |
| τ=1.000 at σ=1, τ=0.944 at σ=10 | `experiments/tournament_stress.py --part 3` | `results/tournament_stress/noise_stability.csv` |
| Simple HV=19.66 > NSGA-II HV=9.99 | `experiments/eco_stats.py --ablation` | `results/eco_stats/ablation.json` |

If any of these cannot be reproduced from the repo, the claim must be revised
or the script must be fixed before submission.

---

## The Submission Checklist

Before submitting:

- [ ] All tables have correct data (cross-check against JSON result files)
- [ ] Reference list is complete (see §3 writing notes for required citations)
- [ ] All figure captions are below figures; table captions above tables
- [ ] "This is not a strawman" appears verbatim in §6.1
- [ ] "97%" appears in abstract and §6.1 total row
- [ ] "structural guarantee" appears in abstract and conclusion
- [ ] Limitations section is honest about parallelism startup cost
- [ ] MesaLayerAdapter future work is mentioned in §7.4
- [ ] Repository URL appears in last sentence of conclusion
- [ ] Word "novel" does not appear in any section
- [ ] Word "glue code" does not appear in any section
- [ ] Field-level claims (+18% biomass) are framed as pipeline validation, not scientific findings
- [ ] All code examples use consistent font and size
- [ ] Page count is ≤ 12 pages in IEEE format
- [ ] Abstract is ≤ 200 words (Draft 1) or ≤ 150 words (Draft 2)
