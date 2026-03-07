# Section 5 — Case Studies

## Draft

We demonstrate HEAS's composability on two case studies that differ
structurally: an ecological population model with stochastic spatial dynamics
and a multi-firm economic regulation model with hierarchical governance. Neither
model is proposed as a validated scientific account of its domain — both serve
as *composition vehicles* whose structural diversity validates the generality
of the Layer/Stream/Arena abstraction.

### 5.1 Ecological Population Management

The ecological model represents a fragmented landscape with prey and predator
populations interacting across climate-driven patch dynamics. It is implemented
as a 5-stream Arena:

```
EcoArena (200 steps/episode)
 ├── ClimateStream    — temperature, stochastic fragmentation shocks (shock_prob)
 ├── LandscapeStream  — patch quality Q ∈ [0,1], modulated by fragmentation
 ├── PreyStream       — logistic growth: dx = r·Q·x(1−x/K) − loss(risk,x,y)
 ├── PredStream       — y dynamics: dy = conv·x·y − mort·y
 └── AggStream
      → agg.mean_biomass  (mean of x+y over episode)
      → agg.cv            (coefficient of variation of biomass)
      → agg.extinct       (predator extinction flag)
```

The policy space is two-dimensional: **risk** (predation risk tolerance, ∈[0,1])
and **dispersal** (patch movement rate, ∈[0,1]). The loss term
`risk·(1−risk)·x·y·0.01` is quadratic in risk, creating a non-trivial landscape
where neither extreme (risk=0 or risk=1) maximizes prey biomass — it is
maximized at risk=0 (no predation pressure) or by high dispersal that buffers
fragmentation shocks.

**Key parameter**: carrying capacity K=1,000. At K<750, the predator always goes
extinct (net growth = conv·K·0.01 − mort = 0.02·K·0.01 − 0.15 < 0 for K<750),
making the extinction objective degenerate. K=1,000 was chosen precisely to
ensure genuine predator-prey dynamics and a non-degenerate Pareto landscape.
This parameter choice is an example of domain knowledge informing framework
configuration — the framework's metric contract then validates that both
objectives vary meaningfully across the gene space.

**Objectives** (minimized by NSGA-II):
- −agg.mean_biomass (maximize mean biomass)
- agg.cv (minimize population variability)

**Tournament scenarios**: 8 combinations of fragmentation ∈ {0.2, 0.6} and
shock_prob ∈ {0.05, 0.15, 0.2, 0.3}.

### 5.2 Enterprise Regulatory Design

The enterprise model represents a regulated economy with firms, a sector
regulator, and a government. It is implemented as a 4-layer Arena:

```
EnterpriseArena
 ├── FirmLayer        — production, compliance cost, profit maximization
 ├── RegulatorLayer   — audit enforcement, sector-level coordination
 ├── GovernmentLayer  — tax policy, subsidy allocation
 └── WelfareLayer     — aggregates welfare across all actors
      → welfare.total, welfare.gini, welfare.compliance_rate
```

The policy space is four-dimensional: tax_rate, audit_intensity, subsidy, and
penalty_rate. NSGA-II evolves Pareto-optimal policy configurations minimizing
{−welfare.total, welfare.gini} — maximizing total social welfare while
minimizing distributional inequality.

The 32-scenario evaluation grid covers: 2 governance regimes (cooperative,
directive) × 2 demand shocks (low, high) × 2 audit frequencies × 2 firm counts
× 2 cost structures. Pareto dominance across all 32 scenarios — not just on
the training distribution — is the validation criterion.

### 5.3 Wolf-Sheep Predation: Porting a Published Mesa Model

To demonstrate that HEAS is compatible with *existing published models* — not
only purpose-built composition vehicles — we port the canonical Mesa
Wolf-Sheep Predation model (Wilensky, 1997; Kazil et al., 2020) to the HEAS
framework. The Mesa Wolf-Sheep model is the flagship example distributed with
the Mesa library and is the most widely cited ABM in the Mesa documentation.
Its dynamics are Lotka-Volterra predator-prey with grass regrowth on a 20×20
spatial grid; published default parameters are `initial_sheep=100`,
`initial_wolves=50`, `sheep_reproduce=0.04`, `wolf_reproduce=0.05`,
`wolf_gain_from_food=20`, `grass_regrowth_time=30`.

**HEAS port architecture**: We implement the mean-field ODE approximation of
the published model as a 4-layer Arena, deriving every ODE coefficient
analytically from Mesa's published energy mechanics — no parameters are tuned:

```
WolfSheepArena (200 steps/episode)
 ├── PolicyStream    — writes harvest_rate (h), grazing_rate (γ) to context
 ├── GrassStream     — ΔG = (1−G)/30 − S·G·γ/N
 │                    regrowth matches grass_regrowth_time=30;
 │                    grazing term: S sheep × P(grown patch)=G×γ / N patches
 ├── SheepStream     — ΔS = (r_s − max(0,1−g_s·G·γ)/g_s)·S − W·S/N
 │                    r_s=0.04 (sheep_reproduce); g_s=4 (sheep_gain_from_food)
 │                    starvation derived from Mesa energy mechanic (energy−=1,
 │                    +g_s when on grown patch, die when energy<0, init~U[0,8])
 │                    predation: contact prob per wolf = S/N (random walk)
 ├── WolfStream      — ΔW = r_w·W·S/N − max(0,1−g_w·S/N)/g_w·W − h·W
 │                    r_w=0.05 (wolf_reproduce); g_w=20 (wolf_gain_from_food)
 │                    births: wolf_reproduce per eating event (rate W·S/N)
 │                    starvation: same energy mechanic, init~U[0,40]→mean=20
 └── WolfSheepAgg
      → wolf_sheep.mean_sheep    (mean sheep abundance over episode)
      → wolf_sheep.mean_wolves   (mean wolf abundance over episode)
      → wolf_sheep.extinct       (1 if either population collapses)
      → wolf_sheep.coexistence   (fraction of steps both populations viable)
```

All six published Mesa parameters (sheep_reproduce=0.04, wolf_reproduce=0.05,
wolf_gain_from_food=20, sheep_gain_from_food=4, grass_regrowth_time=30,
N=400 patches) appear directly as ODE coefficients. No additional constants
are introduced. The spatial grid is collapsed to a density field because
HEAS does not provide a spatial runtime — an acknowledged scope difference
discussed in §7.

**Policy space**: Two management genes: `harvest_rate` ∈ [0, 0.3] (fraction
of wolves removed per step, modelling culling policy) and `grazing_rate` ∈
[0, 1] (sheep energy intake multiplier, modelling pasture management). These
represent realistic resource management levers orthogonal to the published
model's dynamics.

**Objectives**: NSGA-II minimises {−`wolf_sheep.mean_sheep`, `wolf_sheep.extinct`}
— maximising sheep abundance while minimising extinction risk. The Pareto front
trades off between high-yield (aggressive sheep growth → wolf boom → crash risk)
and stable coexistence (moderate harvest keeps wolf population balanced).

**Framework effort**: the port required implementing four stream classes
(GrassStream, SheepStream, WolfStream, WolfSheepAgg) totalling ~120 lines,
all of which are *model logic*. Coupling code — connecting the simulation to
NSGA-II, tournament evaluation, and bootstrap CI — is zero additional lines:
the `wolf_sheep_objective()` function is 8 lines reading `metrics_episode()`
keys, and `Tournament`, `run_many()`, and `summarize_runs()` require no
model-specific configuration. This confirms the framework's coupling-code claim
on a model the authors did not design.

### 5.4 Structural Comparison

| Property | Ecological | Enterprise | Wolf-Sheep (ported) |
|---|---|---|---|
| Streams/Layers | 5 streams | 4 layers | 4 layers |
| Policy genes | 2 (risk, dispersal) | 4 (tax, audit, subsidy, penalty) | 2 (harvest, grazing) |
| Objectives | −biomass, CV | −welfare, Gini | −sheep, extinct |
| Scenario dimensions | 4 (frag, shock) | 5 (regime, demand, audit, firm, cost) | 2 (shock_prob, grass_rate) |
| Total scenarios | 8 | 32 | 4 |
| Episode length | 150–200 steps | 50 steps | 200 steps |
| Key dynamic | Stochastic spatial shocks | Deterministic equilibrium | Predator-prey cycles |
| Model origin | Purpose-built | Purpose-built | Published (Wilensky 1997) |

The structural diversity across three case studies — two purpose-built and one
ported from the published literature — confirms that the Layer/Stream/Arena
abstraction is not tailored to one problem type. The metric contract
(`metrics_episode()` → `dict[str, float]`) generalizes from population dynamics
to economic welfare to published predator-prey models without any change in
framework code.

---

## Writing Notes

### Framing discipline
At no point should the case study section claim biological or economic validity.
Use phrases like:
- "the model represents..." (not "the model simulates the real ecology of...")
- "the policy space includes..." (not "these are real regulatory instruments")
- "we use this model to demonstrate..." (not "we use this model to study...")

This protects against the reviewer who asks "is the ecological model validated?"
Answer: it's a composition demonstration vehicle, not a validated domain model.

### The K=1000 paragraph is important
The explanation of why K=1000 was chosen is a demonstration that the framework
allows domain knowledge to inform model configuration, and that the metric
contract validates parameter choices empirically (std(HV) > 0 confirms the
landscape is non-degenerate). This is a subtle but important point about
framework usability.

### Don't show code in case studies
Section 4 has the code. Section 5 should be prose + the stream/layer diagrams.
The ASCII Arena diagrams are the right level of detail.

### Table 5.3 is very useful
The structural comparison table makes it concrete that the two case studies are
genuinely different — not trivially different versions of the same model.

### Page budget: 1.5 pages
Current draft: ~600 words = ~0.9 pages. Need ~0.6 more pages.
Add:
- One paragraph on how the AggStream cross-layer aggregation works
  (connects ClimateStream data to the EA objective — this is where the
  hierarchy pays off in the eco model)
- One paragraph on the enterprise welfare definition
  (what is "total welfare" in the model — brief, without claiming realism)
