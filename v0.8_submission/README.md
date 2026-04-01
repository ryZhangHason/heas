# HEAS v0.8 Submission Bundle

This folder is a cleaned submission bundle built from `heas/v0.8`.

It contains only:
- `paper/`: the final paper PDF plus the minimal self-contained LaTeX source set needed to compile it
- `code/`: the experiment scripts referenced by the paper and the HEAS package modules they depend on

Excluded on purpose:
- LaTeX build artifacts (`.aux`, `.bbl`, `.blg`, `.fls`, `.fdb_latexmk`, `.out`, `.synctex.gz`)
- draft or unused figure sources
- temp Office files
- review notes, reports, manifests, and other narrative working files
- legacy `v0.8` instrumentation scripts with stale absolute paths
- unused package areas such as `cli/`, `examples/`, `torch_integration/`, and `vis/`

Notes:
- The paper itself only uses `figs/Figure1_tau_Finalized_manual.pdf` from `v0.8`.
- Experiment reproducibility code was taken from `heas/experiments/` and `heas/heas/`, because those are the live sources backing the claims in `paper.tex`.
