# Section 8 — Anticipated Reviewer Q&A

This file prepares responses to reviewer questions that are likely for a WSC
submission. For each question, two versions are provided: a short in-paper
response (to use if the question arises in the rebuttal) and a longer discussion
version (for internal reference).

---

## Q1: "Why not just use Mesa carefully? A competent Mesa programmer can do everything HEAS does."

### Short response (rebuttal-ready):
A competent Mesa programmer writes 160 lines of coupling code to connect one
simulation to NSGA-II, tournament scoring, and bootstrap CI (Table 1). HEAS
requires 5. More importantly, Mesa provides no structural mechanism to prevent
a developer from changing the EA objective (`mean_prey`) without updating the
tournament scorer — a silent bug that can persist for weeks. In HEAS, this is
structurally impossible: both consumers read the same `metrics_episode()` key.
The Mesa comparison uses all Mesa best practices including DataCollector, episode
runner, ProcessPoolExecutor parallelism, and independent tournament scoring.
It is not a strawman.

### Discussion:
This is the most important reviewer question. The answer has two parts:

1. **Quantitative**: 160 vs 5 LOC is not a style preference — it is 155 lines
   that must be written, debugged, and maintained per project. For a lab that
   runs 10 policy search projects per year, that is 1,550 lines of boilerplate
   that HEAS eliminates.

2. **Structural**: Mesa can be used carefully, but "using it carefully" means
   the researcher becomes the enforcement mechanism for metric consistency.
   HEAS makes metric consistency a structural property of the framework —
   it is not possible to forget to update the tournament scorer because the
   tournament scorer reads the same dict key as the EA.

The phrase to use: "HEAS provides structural guarantees where Mesa provides
conventions."

---

## Q2: "The ecological model is not biologically realistic. The predator-prey dynamics don't account for X."

### Short response (rebuttal-ready):
The ecological model is a composition demonstration, not a domain contribution.
As stated in §5.1, the case study demonstrates how a 5-stream HEAS Arena
integrates climate, landscape, prey dynamics, predator response, and dispersal
as independent composable units — a structural claim about the framework, not
a biological claim about ecology. Biological realism is not required for a
composition demonstration; what matters is structural diversity from the
enterprise case study (different hierarchy, different state variables, different
objective).

### Discussion:
Pre-empt this in the paper itself with the framing: "We present two case
studies that differ structurally — one with stochastic spatial dynamics, one
with multi-stakeholder economic interactions — as composition demonstrations.
We make no domain-level scientific claims about ecology or economics."

If the reviewer asks anyway, the response is: "You are right that a biologically
realistic predator-prey model would require X. We did not intend to make a
biological contribution. The ecological model serves the same role as the
sorting-algorithm example in a data structure paper: it provides a concrete,
understandable substrate for demonstrating the framework."

---

## Q3: "Why NSGA-II? There are better multi-objective algorithms."

### Short response (rebuttal-ready):
HEAS is optimizer-agnostic. The `run_optimization_simple()` interface accepts
any callable `objective_fn` and any strategy string. The algorithm ablation
(§6.4) demonstrates this: we swap NSGA-II for simple hillclimbing and random
grid search with no framework changes. NSGA-II was chosen as the default because
it is the most widely used non-dominated sorting algorithm in the ABM policy
search literature (Pangallo et al., 2019; Caprì et al., 2023). Researchers
who prefer CMA-ES, SMS-EMOA, or MOEA/D can substitute them via the
`strategy` parameter or by replacing the objective function wrapper.

### Discussion:
The right answer is: "We chose NSGA-II because it is the community standard,
not because it is optimal for all landscapes." The ablation (§6.4) actually
shows that for 2-gene problems, hillclimbing outperforms NSGA-II — and we
report this honestly, because it reinforces the optimizer-agnosticism claim.

---

## Q4: "Table 3 shows high variance in ecological HV (std=3.518). Doesn't this undermine the reproducibility claim?"

### Short response (rebuttal-ready):
The variance is real and expected: the ecological landscape is bimodal — NSGA-II
runs either converge to a local optimum (HV≈4.0–6.5) or reach the global Pareto
front (HV≈11.7–11.8). The 95% bootstrap CI [6.424, 8.914] correctly captures
this spread. The reproducibility claim is that HEAS's per-run seeding makes
this variance *quantifiable* across 30 independent runs, with bootstrap CI
providing a statistically valid summary — something that a single-run Mesa study
cannot provide. The high variance is evidence that NSGA-II does not always find
the global front on this landscape, not evidence against reproducibility.

### Discussion:
The K=1000 correction story (§6.2) is the strongest internal evidence of
reproducibility benefit: at K=120, HV std=0.000 (degenerate — predator always
extinct). Only by running 30 replicates with proper seeding was this degeneracy
detectable. A single-run Mesa study would have reported one number and published
it without knowing the distribution was collapsed.

Frame the variance as "the framework revealing genuine stochasticity in the
landscape" not as "the framework failing to converge."

---

## Q5: "Where are the scalability benchmarks? HEAS's architecture might be slower than Mesa."

### Short response (rebuttal-ready):
HEAS is not primarily a performance contribution — it is a composability
contribution. The LOC comparison and structural consistency guarantees are the
primary claims. That said, we report honest timing data: for lightweight ODE
simulations (0.004 s/episode), HEAS and Mesa have equivalent single-threaded
throughput; HEAS's `n_jobs` parallelism has 9s process startup overhead that
dominates at small episode counts. For computationally heavy agents (> 0.1
s/episode), `n_jobs=N` delivers linear speedup with zero additional LOC versus
Mesa's 20-line ProcessPoolExecutor boilerplate. Scalability benchmarks at HPC
scale (1,000+ agents, GPU-backed dynamics) are a planned extension
(§7.4, Distributed Execution).

### Discussion:
This question is an attempt to find a dimension where HEAS is strictly worse
than Mesa. The honest answer: HEAS adds a small amount of overhead from the
Layer dispatch mechanism (~1ms/episode, negligible for episodes > 0.01 s).
It does not add Python GIL contention or memory overhead beyond Mesa.

The scalability deferred to future work framing is legitimate: WSC accepts
framework papers without complete scaling characterizations, especially when
the primary contribution is architectural.

---

## Q6: "The tournament uses a known 'champion' — how would a real user find the champion without knowing the ground truth?"

### Short response (rebuttal-ready):
In practice, the champion is found by running `run_optimization_simple()` first,
extracting the Pareto-dominant genome, and then entering it into the tournament
alongside a reference (baseline) policy and a contrarian (high-variance
alternative). This is the standard workflow: optimization finds the candidate,
tournament validates it across scenarios with statistical certification. The
tournament is not used to *find* a winner — it is used to *certify* that the
optimization output is robust across the scenario distribution. The workflow
is documented in the case study (§5) and the tournament experiment (§6.3).

### Discussion:
The concern is valid: the tournament experiment uses a pre-specified champion
rather than an evolved champion. This is intentional — tournament stress-testing
should use known-good participants so that the certification properties can be
independently verified. In a full pipeline, the champion genome comes from
`run_optimization_simple()`, and the tournament certifies it.

---

## Q7: "Is HEAS useful outside of evolutionary search? What if I just want to run Monte Carlo simulations?"

### Short response (rebuttal-ready):
Yes. The `Layer`/`Stream`/`Arena` composition model and `run_many()` episode
runner are useful for any multi-episode simulation study, including Monte Carlo
parameter sweeps. `summarize_runs()` and `bootstrap_ci()` apply equally to
Monte Carlo outputs. The EA and tournament are optional — researchers who only
need the compositional hierarchy and bootstrap CI can use HEAS without touching
the optimization stack. The framework's layered design was deliberately chosen
to make these components independently usable.

### Discussion:
This is actually a selling point, not a limitation. HEAS's value proposition
extends to any study requiring: (a) reproducible multi-episode statistics,
(b) composable simulation hierarchy, or (c) multi-scenario comparison. The EA
and tournament are the headline features, but the framework is useful for any
ABM validation study.

---

## Q8: "The Copeland voting rule appears in your experiment but not in the main Tournament API."

### Short response (rebuttal-ready):
Copeland requires cross-episode pairwise comparison and cannot be routed through
the per-episode `voter_fn` interface in `Tournament.play()`. In the current
implementation, Copeland is computed directly from the Arena's per-episode score
data (see `copeland_vote()` in `heas/game/voting.py`). In the next version,
`Tournament.play()` will support a `'copeland'` label that internally uses the
cross-episode aggregation path. This is an API cleanup item, not a missing
feature — the Copeland computation is fully implemented and used in §6.3.

### Discussion:
Be transparent about this. Don't claim Copeland is "in Tournament.play()" when
it isn't. The reviewers might check the code. Say: "Copeland is implemented
in `copeland_vote()` in `heas/game/voting.py` and used in the experiment; its
integration into `Tournament.play()` as a first-class option is planned for
the next release."

---

## Q9: "The 97% LOC reduction claims to count only 'coupling code' — isn't this cherry-picked?"

### Short response (rebuttal-ready):
The LOC comparison explicitly separates *model logic* (identical between Mesa
and HEAS — dynamics, parameters, state update rules) from *coupling code*
(lines that exist solely to wire simulation output to a downstream consumer).
Model logic is not included in either count because it is equivalent between
implementations. The coupling code breakdown is task-by-task with individual
counts per task (Table 1) so reviewers can verify each line count independently.
The 97% reduction is a property of the coupling code specifically, which is
the framework's primary claim — we do not claim that HEAS reduces total code
by 97%.

### Discussion:
This is the methodologically most vulnerable claim. Preempt it by making
the LOC accounting methodology explicit in the paper: "We count non-blank,
non-comment lines in coupling code only — lines that exist solely to connect
simulation output to downstream consumers. Model logic lines (dynamics,
parameters, state) are counted in neither column because they are equivalent
between implementations." This framing is honest and makes the comparison
auditable.

---

## Q10: "How does HEAS handle real-time simulation or time-indexed event queuing?"

### Short response (rebuttal-ready):
HEAS uses a discrete, synchronous step model: at each step, all active Layers
call `step()` in dependency order. This is appropriate for ABMs with a
common global clock (ecological seasons, economic quarters, regulatory cycles).
HEAS does not support event-driven simulation with asynchronous timing or
continuous-time queues (e.g., DEVS or SimPy). For event-driven simulations,
a SimPy-based backend wrapped as a HEAS Layer is possible but not currently
provided. This is a known architectural constraint of the synchronous step model
used by Mesa, NetLogo, and most ABM frameworks targeting social and ecological
systems.

---

---

## Q11: "The Mesa code excerpt is absent from the manuscript — a referee without repository access cannot verify the 160-line count."

### Short response (rebuttal-ready):
§6.1 (Revision) now includes Listing 1 — verbatim reproduction of DataCollector
Block A (15 LOC) and episode-extraction Block B (20 LOC) from
`experiments/mesa_eco.py`. These are the two most illustrative blocks; all six
blocks (A–F) are annotated with per-block line counts in the repository files
`experiments/mesa_eco.py` and `experiments/mesa_vs_heas.py`, which are included
in the supplemental material package accompanying the submission.

### Discussion:
Show the code, don't just reference it. Listing 1 must appear in the camera-ready
version regardless of page pressure. A two-column WSC paper can fit ~35 lines of
code per column; Listing 1 (35 LOC) fits in one column. If page budget is tight,
compress by removing the inline comments from the listing — the LOC count is
unaffected.

---

## Q12: "The case studies are purpose-built composition vehicles. No externally published model has been ported."

### Short response (rebuttal-ready):
§5.3 (Revision) presents a HEAS port of the canonical Mesa Wolf-Sheep Predation
model (Wilensky, 1997; Kazil et al., 2020) — the flagship example distributed
with the Mesa library. The port implements the mean-field ODE equivalent of the
published model using the published default parameters (`initial_sheep=100`,
`initial_wolves=50`, `sheep_reproduce=0.04`, `wolf_reproduce=0.05`,
`grass_regrowth_time=30`) without tuning. The spatial grid is collapsed to a
density field — an acknowledged simplification noted in §7. The port confirms
that adding NSGA-II optimisation and tournament evaluation to the published model
requires zero additional coupling code, validating the framework's claim on a
model the authors did not design.

### Discussion:
The Wolf-Sheep port is the strongest answer to this concern. Frame it precisely:
"We port — not adapt — the published model, using the published parameters
verbatim. The mean-field ODE approximation is dynamically equivalent at
large N; at small N, spatial effects dominate and a full spatial runtime
(future work) would be needed." Do not overclaim that the port is a complete
replication of the Mesa spatial model.

---

## Internal Reviewer Risk Assessment

| Question | Likelihood | Severity | Preparation needed |
|---|---|---|---|
| Q1: Why not Mesa? | Very high | High | **Exp A-D results must be airtight** |
| Q2: Ecological realism | High | Medium | Composition vehicle framing |
| Q3: Why NSGA-II? | Medium | Low | Ablation §6.4 already answers |
| Q4: High variance | Medium | Medium | Bimodal landscape explanation |
| Q5: Scalability | Medium | Medium | Honest timing + future work |
| Q6: Known champion | Low | Low | Workflow explanation |
| Q7: Non-EA use | Low | Low | Selling point, not weakness |
| Q8: Copeland API gap | Low | Medium | Be transparent in paper |
| Q9: LOC cherry-picked | Medium | High | Methodology must be explicit |
| Q10: Event-driven | Low | Low | Architectural scope limitation |

**Priority**: Address Q1 and Q9 in the main paper text. Address Q2 and Q4 in
framing sentences. Leave Q5, Q6, Q7, Q8, Q10 to the rebuttal if raised.
