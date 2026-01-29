# Result Interpretation — Sample Usage 1

## Summary of the run
Across four episodes (seeds 123–126), the system stabilizes quickly. The climate and landscape drivers are steady by the end of each episode (final climate value around 0.35 and landscape quality around 0.80). Prey biomass grows to roughly 100, while predator biomass settles around 5.6. No extinction events occur (extinct = 0.0 throughout).

## What the per‑step preview shows
The per‑step preview focuses on the aggregator layer (`L3S1`), which consolidates the ecosystem state. Prey increases rapidly from the initial value to a stable level, while predators decline gently to their steady state. This indicates the predator response is not strong enough to cause prey collapse under the current risk, growth, and dispersal settings.

## Episode‑to‑episode consistency
Episodes 2–4 are nearly identical to each other, suggesting the system is dominated by deterministic dynamics with only mild stochastic influence. Episode 1 shows a slightly lower final prey value, but the differences are small and do not change the qualitative outcome (stable coexistence).

## Practical interpretation
- The ecosystem is resilient under the current parameterization.
- Prey growth and carrying capacity dominate the equilibrium level.
- Predator mortality and conversion rates are low enough to avoid runaway predation.
- No extinction threshold is crossed, so the system remains in a stable coexistence regime.

## If you want different behavior
- Increase predator conversion rate or reduce predator mortality to raise predator pressure.
- Increase prey risk level or reduce growth rate to slow prey recovery.
- Increase dispersal to dampen predation pressure further.
- Raise the extinction threshold to make extinction events more likely.
