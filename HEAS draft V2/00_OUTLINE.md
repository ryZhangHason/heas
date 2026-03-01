# Paper Outline — Argument Map and Page Budget

## Core Argument (one sentence)

> HEAS eliminates 97% of the coupling code required to connect hierarchical agent-based simulations to multi-objective evolutionary search and tournament evaluation, while enforcing metric consistency that existing frameworks cannot guarantee.

---

## Section Plan

| # | Section | Pages | Core claim |
|---|---|---|---|
| 1 | Abstract | 0.2 | Framework + evidence summary |
| 2 | Introduction | 1.0 | Gap: ABMs require glue code for EA+tournament |
| 3 | Related Work | 0.8 | Mesa/NetLogo/Repast: what they miss and why |
| 4 | Framework | 2.5 | Layer/Stream/Arena + metric contract + EA + tournament |
| 5 | Case Studies | 1.5 | Eco (5 streams) + enterprise (4 layers) |
| 6 | Evaluation | 3.5 | Mesa comparison + 30-run studies + tournament validation |
| 7 | Conclusion | 0.5 | Summary + future work |
| — | References | 1.0 | ~20 citations |
| — | **Total** | **11.0** | Within 12-page limit |

---

## Section 2 — Introduction Argument Chain

```
Hook:
  Simulation-based policy search is increasingly used in economics, ecology,
  public health. Researchers run ABMs, evaluate candidate policies over multiple
  scenarios, and search for Pareto-optimal configurations.

Current practice problem:
  Every such project rewrites the same coupling code:
  - DataCollector setup → EA fitness extraction → tournament scoring → bootstrap CI
  - These are independent code paths with no enforcement of consistency
  - When an objective changes, 3–4 files must be updated in sync

Gap in existing tools:
  Mesa: DataCollector is a pull-based logger, not a compositional interface
  NetLogo/BehaviorSpace: grid sweep only, not continuous multi-objective search
  Repast4Py: high-performance but no EA or tournament native support
  → None provide hierarchy + uniform metrics + EA + tournament as integrated system

Our contribution:
  HEAS introduces four architectural innovations (C1–C4):
    C1: Layer/Stream/Arena — formal hierarchy abstraction
    C2: Uniform metric contract — single source of truth across all consumers
    C3: Native NSGA-II integration — zero coupling code for multi-objective EA
    C4: Tournament evaluation — first-class multi-scenario, multi-rule comparison

Evidence:
  - 97% reduction in coupling LOC vs Mesa (Exp A)
  - Adding a second objective: 1 file / 1 line in HEAS vs 3 files / 6 lines in Mesa (Exp B)
  - Metric divergence structurally prevented by contract (Exp D)
  - Validated on two case studies across 30 independent runs each
```

---

## Section 4 — Framework Structure

### 4.1 Layered Composition
```
Layer contract:
  step() → None
  metrics_step() → dict[str, float]   # per-timestep
  metrics_episode() → dict[str, float] # end-of-episode
  reset() → None

Stream = named Layer group with routing contract
Arena = Stream orchestrator + episode runner
```

Key diagram: Stream graph for eco model
```
Arena
├── ClimateStream   → climate.final_value, climate.temp
├── LandscapeStream → landscape.quality
├── PreyStream      → prey.biomass, prey.final_prey
├── PredStream      → pred.final_pred
└── AggStream ←── reads from all above
    → agg.mean_biomass, agg.cv, agg.extinct
```

### 4.2 Metric Contract
```python
# The same key string propagates to ALL consumers:
KEY = "agg.mean_biomass"

# 1. EA objective (eco.py)
fitness = -mean(ep[KEY] for ep in run_many(...))

# 2. Tournament scorer (tournament_stress.py)
score = ep_metrics.get(KEY, 0.0)

# 3. Statistical CI (eco_stats.py)
hv_series = [run[KEY] for run in runs]
ci = summarize_runs(hv_series)["ci_lower"]
```
Point: changing the model requires adding one line to metrics_episode().
All three consumers update automatically. No code path synchronization needed.

### 4.3 EA Integration
```python
result = run_optimization_simple(
    objective_fn=eco.trait_objective,  # reads from metric contract
    n_genes=2, gene_bounds=[(0,1),(0,1)],
    pop_size=20, n_generations=10,
)
# result["hof_fitness"] = Pareto front
# result["hv"] = hypervolume
# No DEAP boilerplate. No seed management. No fitness extraction code.
```

### 4.4 Tournament Evaluation
```python
# 4 voting rules, automatic sample complexity, noise stability bounds
tournament.run(
    participants=["champion", "reference", "contrarian"],
    scenarios=SCENARIOS,   # drawn from scenario distribution
    n_episodes=50,         # per scenario
    voting_rule="argmax"   # or majority / borda / copeland
)
# Output: winner, agreement matrix, P(correct winner), τ-vs-σ curve
```

---

## Section 6 — Evaluation Structure

### 6.1 Mesa Comparison (PRIMARY — answers "why not Mesa?")

Table: LOC breakdown (Exp A)
| Task | Mesa | HEAS | Saved |
| DataCollector setup | 15 | 0 | 15 |
| Metric extraction | 20 | 0 | 20 |
| Episode runner | 22 | 1 | 21 |
| Parallel runner | 20 | 0 | 20 |
| EA fitness glue | 14 | 3 | 11 |
| Tournament scorer | 18 | 0 | 18 |
| Seed management | 12 | 0 | 12 |
| Bootstrap CI | 35 | 0 | 35 |
| TOTAL | 160 | 5 | 155 (97%) |

Table: Extension cost (Exp B)
Table: Metric divergence (Exp D)

### 6.2 Reproducibility Study (30 runs each)
- eco_stats: HV mean=7.665 ± 3.518, 95% CI=[6.424, 8.914]
- ent_stats: HV mean=4317.5 ± 19.4, CI=[4311, 4326]
- Both: per-run seeding, bootstrap BCa CI — infrastructure native to framework

### 6.3 Tournament Validation
- Voting agreement: 4/4 rules agree 100% at well-separated participants
- Sample complexity: P=1.0 at ≥4 episodes/scenario
- Noise stability: τ=1.0 at σ≤1, τ=0.944 at σ=10 (6.5% of margin), graceful degradation

### 6.4 Algorithm Agnosticism
- Ablation: Simple (HV=19.66) > NSGA-II (9.99) > Random (7.61) on 2D landscape
- Framing: HEAS is optimizer-agnostic — swap objective_fn or algorithm with no framework changes
- NSGA-II advantage appears in higher-dimensional search spaces (MLP weight evolution)

---

## Figures Needed

1. **Fig 1**: HEAS architecture diagram — Layer/Stream/Arena with metric contract arrows
2. **Fig 2**: Eco stream graph (Arena with 5 streams + metric flow)
3. **Fig 3**: Enterprise hierarchy (4-layer regulatory arena)
4. **Fig 4**: Tournament noise stability curve (τ vs σ/margin) — key new result
5. **Fig 5**: eco_stats HV distribution (30 runs, bimodal) — shows genuine variance

## Tables Needed

1. **Table 1**: Mesa vs HEAS LOC comparison (Exp A) — 9 rows
2. **Table 2**: Objective extension cost (Exp B) — 3-col: task / Mesa / HEAS
3. **Table 3**: eco_stats 30-run statistics
4. **Table 4**: Tournament voting agreement matrix (4×4, all 1.000)
5. **Table 5**: Tournament noise stability (σ / τ / CI / σ/margin)
6. **Table 6**: Related work comparison (framework × 4 features)
