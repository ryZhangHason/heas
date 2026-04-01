# PPTX Element Layout Reference
## File: `Figure1_tau_sweep_editable.pptx`
**Slide canvas:** 10.00" × 5.625" (16:9).
All coordinates are `(x, y, w, h)` in **inches from top-left corner**.
Origin = top-left = (0, 0). Right edge = x 10.00. Bottom edge = y 5.625.

---

## Slide 1 — Both Panels (Overview)

| # | Element | x | y | w | h | Notes |
|---|---------|---|---|---|---|-------|
| 1 | **Title text** | 0.20 | 0.08 | 9.60 | 0.35 | "Figure 1 \| τ-Sweep Divergence…" · 11pt bold TNR |
| 2 | **(a) subtitle** | 0.20 | 0.45 | 4.50 | 0.25 | "Rank Reversal Rate (%)" · 9pt TNR |
| 3 | **LINE chart** (left panel) | 0.20 | 0.72 | 4.60 | 4.30 | 4 series: Entropy/Step/Mean/HEAS; y-axis 0–55, step 10 |
| 4 | Annotation box — Semantic | 0.42 | 2.05 | 1.05 | 0.42 | Rounded rect · border #4D4D4D · "Semantic / h=0.72–1.14" |
| 5 | Annotation box — Syntactic | 2.10 | 3.30 | 1.10 | 0.42 | Rounded rect · border #D6604D · "Syntactic / h=0.32–0.66" |
| 6 | Annotation box — Near-uniform | 3.00 | 4.40 | 1.20 | 0.42 | Rounded rect · border #4DAF4A · "Near-uniform / \|h\|<0.07" |
| 7 | **(b) subtitle** | 5.20 | 0.45 | 4.50 | 0.25 | "Cohen's h (HEAS vs. ad-hoc)" · 9pt TNR |
| 8 | **BAR chart** (right panel) | 5.20 | 0.72 | 4.60 | 4.30 | 3 series: Entropy/Step/Mean; y-axis 0–1.3, step 0.2 |
| 9 | Ref line — small h=0.2 (line) | 5.25 | 3.68 | 3.95 | 0 | Dotted · #BBBBBB |
| 10 | Ref line — small h=0.2 (label) | 9.22 | 3.56 | 0.72 | 0.24 | "small (h=0.2)" · 6pt #888888 |
| 11 | Ref line — medium h=0.5 (line) | 5.25 | 2.90 | 3.95 | 0 | Dotted · #BBBBBB |
| 12 | Ref line — medium h=0.5 (label) | 9.22 | 2.78 | 0.72 | 0.24 | "medium (h=0.5)" · 6pt #888888 |
| 13 | Ref line — large h=0.8 (line) | 5.25 | 2.12 | 3.95 | 0 | Dotted · #BBBBBB |
| 14 | Ref line — large h=0.8 (label) | 9.22 | 2.00 | 0.72 | 0.24 | "large (h=0.8)" · 6pt #888888 |

**Chart colours:** Entropy=#4D4D4D · Step=#D6604D · Mean=#4DAF4A · HEAS=#2166AC

---

## Slide 2 — Panel (a) Alone — Rank Reversal Rates

| # | Element | x | y | w | h | Notes |
|---|---------|---|---|---|---|-------|
| 1 | **Title text** | 0.30 | 0.10 | 9.40 | 0.35 | "Panel (a) — Rank Reversal Rates…" · 10pt bold TNR |
| 2 | **LINE chart** | 0.50 | 0.55 | 9.00 | 4.70 | Same 4 series as Slide 1; legend at right (legendPos "r"); marker size 8 |

No annotation boxes on this slide (add your own after editing).

---

## Slide 3 — Panel (b) Alone — Cohen's h

| # | Element | x | y | w | h | Notes |
|---|---------|---|---|---|---|-------|
| 1 | **Title text** | 0.30 | 0.10 | 9.40 | 0.35 | "Panel (b) — Cohen's h Effect Sizes…" · 10pt bold TNR |
| 2 | **BAR chart** | 0.50 | 0.55 | 6.00 | 4.70 | 3 series; legend at right; y-axis 0–1.3 |
| 3 | Ref line — large h=0.8 (line) | 0.55 | 1.87 | 5.85 | 0 | Dotted · #AAAAAA |
| 4 | Ref line — large h=0.8 (label) | 6.42 | 1.72 | 1.50 | 0.30 | "large  h = 0.8" · 8pt #888888 |
| 5 | Ref line — medium h=0.5 (line) | 0.55 | 2.68 | 5.85 | 0 | Dotted · #AAAAAA |
| 6 | Ref line — medium h=0.5 (label) | 6.42 | 2.53 | 1.50 | 0.30 | "medium h = 0.5" · 8pt #888888 |
| 7 | Ref line — small h=0.2 (line) | 0.55 | 3.82 | 5.85 | 0 | Dotted · #AAAAAA |
| 8 | Ref line — small h=0.2 (label) | 6.42 | 3.67 | 1.50 | 0.30 | "small  h = 0.2" · 8pt #888888 |
| 9 | **Data reference box** | 6.70 | 2.80 | 3.10 | 2.50 | Consolas 7.5pt · grey fill #F5F5F5 · all 6 τ values |

---

## Slide 4 — Contract Architecture

**Three-column layout.** Left col x∈[0.10, 2.90] · Centre col x∈[3.05, 6.95] · Right col x∈[7.10, 9.85]

| # | Element | x | y | w | h | Notes |
|---|---------|---|---|---|---|-------|
| 1 | **Title text** | 0.15 | 0.05 | 9.70 | 0.30 | "Figure X \| HEAS Contract Architecture…" · 11pt bold TNR |
| 2 | Col header — Arena/Streams/Layers | 0.10 | 0.38 | 2.75 | 0.24 | 9pt bold TNR · centred |
| 3 | Col header — Contract | 3.05 | 0.38 | 3.90 | 0.24 | 9pt bold TNR · centred |
| 4 | Col header — Pipeline Stages | 7.10 | 0.38 | 2.75 | 0.24 | 9pt bold TNR · centred |
| **CENTRE — Divergent path** | | | | | | |
| 5 | Divergent-path background rect | 3.05 | 0.66 | 3.90 | 2.10 | Rounded · fill #FFF0F0 · dashed border #CC3333 |
| 6 | "DIVERGENT PATH…" label | 3.10 | 0.69 | 3.80 | 0.22 | 8pt bold red #CC3333 |
| 7 | Interface box (yellow) | 3.40 | 0.96 | 3.20 | 1.65 | Rounded · fill #FFFACD · border #C8960C |
| 8 | "Interface" title inside box | 3.45 | 1.02 | 3.10 | 0.30 | 10pt bold #7B5800 · centred |
| 9 | Code text inside box | 3.50 | 1.34 | 3.00 | 1.18 | Consolas 9pt · "def metrics_episode(…)" |
| 10 | **metrics_episode() green box** | 3.40 | 3.10 | 3.20 | 0.52 | Rounded · fill #C8E6C9 · border #388E3C 1.5pt |
| 11 | "metrics_episode()" label | 3.40 | 3.10 | 3.20 | 0.52 | Consolas 12pt bold #1B5E20 · centred (same coords as box) |
| 12 | "NO DIVERGENCE" label | 3.40 | 3.68 | 3.20 | 0.28 | 9pt bold green #2E7D32 · centred |
| **LEFT — HEAS Hierarchy** | | | | | | |
| 13 | "HEAS UNIFIED PATH…" label | 0.10 | 0.66 | 2.80 | 0.22 | 7.5pt bold blue #2166AC |
| 14 | **Arena box** | 0.65 | 1.00 | 1.55 | 0.42 | Fill #DDEEFF · border #2166AC 1.2pt · "Arena" 10pt bold |
| 15 | Stream box S1 | 0.10 | 1.62 | 0.68 | 0.38 | Fill #DDEEFF · border #2166AC · "S1" 9pt bold |
| 16 | Stream box S2 | 0.90 | 1.62 | 0.68 | 0.38 | Fill #DDEEFF · border #2166AC · "S2" 9pt bold |
| 17 | Stream box S3 | 1.70 | 1.62 | 0.68 | 0.38 | Fill #DDEEFF · border #2166AC · "S3" 9pt bold |
| 18 | Arrow Arena→S1 (vertical) | 0.44 | 1.42 | 0.00 | 0.20 | Blue #2166AC · endArrow |
| 19 | Arrow Arena→S2 (vertical) | 1.24 | 1.42 | 0.00 | 0.20 | Blue #2166AC · endArrow |
| 20 | Arrow Arena→S3 (vertical) | 2.04 | 1.42 | 0.00 | 0.20 | Blue #2166AC · endArrow |
| 21 | Layer box L1 | 0.10 | 2.22 | 0.80 | 0.38 | Fill #DDEEFF · border #2166AC · "L1" 9pt bold |
| 22 | Layer box L2 | 1.50 | 2.22 | 0.80 | 0.38 | Fill #DDEEFF · border #2166AC · "L2" 9pt bold |
| 23 | Arrow S→L (from x=0.44) | 0.44 | 2.00 | 0.00 | 0.22 | Blue · endArrow |
| 24 | Arrow S→L (from x=1.24) | 1.24 | 2.00 | 0.00 | 0.22 | Blue · endArrow |
| 25 | Arrow S→L (from x=2.04) | 2.04 | 2.00 | 0.00 | 0.22 | Blue · endArrow |
| **RIGHT — Pipeline** | | | | | | |
| 26 | **Optimizer box** | 7.10 | 1.00 | 2.75 | 0.52 | Fill #F5F5F5 · border #777777 · "Optimizer" 11pt bold |
| 27 | **Tournament box** | 7.10 | 1.82 | 2.75 | 0.52 | Fill #F5F5F5 · border #777777 · "Tournament" 11pt bold |
| 28 | **Inference box** | 7.10 | 2.64 | 2.75 | 0.52 | Fill #F5F5F5 · border #777777 · "Inference" 11pt bold |
| **ARROWS** | | | | | | |
| 29 | Red dashed → Interface (Optimizer) | 6.60 | 1.26 | 0.50 | 0.00 | #CC3333 · sysDash · beginArrow (points left) |
| 30 | Red dashed → Interface (Tournament) | 6.60 | 2.08 | 0.50 | 0.00 | #CC3333 · sysDash · beginArrow |
| 31 | Red dashed → Interface (Inference) | 6.60 | 2.90 | 0.50 | 0.00 | #CC3333 · sysDash · beginArrow |
| 32 | Blue horizontal (L-cols → centre) | 2.90 | 2.36 | 0.50 | 0.00 | #2166AC 1.5pt · endArrow |
| 33 | Blue vertical (elbow → green box) | 3.40 | 2.36 | 0.00 | 0.74 | #2166AC 1.5pt · endArrow (arrives at y=3.10) |
| **BOTTOM EXAMPLE** | | | | | | |
| 34 | Example background rect | 0.10 | 4.15 | 9.80 | 1.28 | Fill #F8F8F8 · border #CCCCCC |
| 35 | Example title | 0.18 | 4.18 | 9.65 | 0.24 | "Example — Policy A (Rank inconsistency)" · 8.5pt bold |
| 36 | Divergent line (red text) | 0.18 | 4.44 | 9.65 | 0.27 | 8.5pt #CC3333 |
| 37 | HEAS line (green text) | 0.18 | 4.73 | 9.65 | 0.27 | 8.5pt #1B5E20 |
| 38 | Contract note (italic) | 0.18 | 5.02 | 9.65 | 0.24 | 8pt italic #555555 |

---

## Quick-fix guide for common manual edits

| What to fix | Which element # (Slide 4) | What to change |
|---|---|---|
| Interface box too small / text clipped | #7 + #9 | Increase h of #7 from 1.65; adjust y of #9 accordingly |
| Green box too low / gap too large | #10, #11, #12 | Move all three up; keep them stacked (gap = 0.06") |
| Arrows not reaching boxes | #29–#31 | Increase w from 0.50 to close the gap to box left edge (7.10) |
| Arena→S connectors misaligned | #18–#20 | x = centre of each S box (S1 centre = 0.10+0.34=0.44 ✓) |
| S→L connectors misaligned | #23–#25 | Same x values; y top = 1.62+0.38=2.00 ✓; y bottom = 2.22 ✓ |
| Example box cut off at bottom | #34–#38 | Slide bottom = 5.625; box bottom = 4.15+1.28=5.43 ✓ (fits) |
| Ref labels clipped on Slide 1 | #10,12,14 | x=9.22+w=0.72 → right edge=9.94 (tight); reduce fontSize or move x left |
