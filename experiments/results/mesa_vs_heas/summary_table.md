## HEAS vs Mesa: Quantitative Comparison

| Capability | Mesa | HEAS | Evidence |
|---|---|---|---|
| Coupling code for EA+tournament pipeline | ~160 LOC | ~5 LOC | Exp A: 97% reduction |
| Add second objective | 3 files, ~6 lines | 1 file, 1 line | Exp B |
| Parallel episode evaluation | ~20 LOC boilerplate | n_jobs= parameter | Exp C: zero extra LOC; speedup realises for >0.1s/ep agents |
| Metric consistency (EA ↔ tournament) | Manual (divergence risk) | Contract-enforced | Exp D |
| Native Pareto front output | ❌ | ✅ DEAP-integrated | heas/evolution/algorithms.py |
| Bootstrap CI for multi-run study | Manual scipy | summarize_runs() | heas/utils/stats.py |
| 4-rule voting tournament | ❌ | ✅ | heas/game/voting.py |

*Mesa is superior for spatial agent interactions, browser visualization (SolaraViz), and exploratory single-run modeling.*
