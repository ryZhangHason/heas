================================================================================
Figure X: HEAS metrics_episode() Contract Architecture
WSC 2026 Paper
================================================================================

FILE LOCATIONS:
  PDF:  /sessions/zen-hopeful-noether/mnt/heas/v0.5/figs/fig_contract_architecture.pdf (48 KB)
  PNG:  /sessions/zen-hopeful-noether/mnt/heas/v0.5/figs/fig_contract_architecture.png (190 KB)

FIGURE SPECIFICATIONS:
  Size:           6.4 × 3.2 inches (single column width, WSC format)
  Resolution:     300 DPI
  Font:           Liberation Serif, 7-8pt labels
  PDF Type:       fonttype=42 (embedded TrueType fonts)
  Color Space:    CMYK-safe grayscale compatible

FIGURE CONTENTS:

[LEFT PANEL] Arena/Streams/Layers Hierarchy
  - Shows hierarchical composition: Arena → Streams → Layers
  - Visual representation of HEAS model structure
  - Demonstrates the nesting relationship

[CENTER PANEL] metrics_episode() Contract Interface
  - Yellow-highlighted contract box
  - Method signature: def metrics_episode(obs, actions, rewards) → metrics_dict
  - Single unified interface that all stages call

[RIGHT PANEL] Pipeline Stages
  - Three boxes: Optimizer, Tournament, Inference
  - Each represents a distinct stage in the evaluation pipeline

[UPPER SECTION] DIVERGENT PATH (Problem)
  - Red dashed arrows from Optimizer and Tournament stages
  - Pointing to DIFFERENT aggregation functions:
    * Optimizer → mean_biomass
    * Tournament → q75_biomass
  - RED WARNING BOX: "✗ DIVERGENCE"
  - Shows silent aggregation divergence problem

[LOWER SECTION] HEAS UNIFIED PATH (Solution)
  - BLUE ARROWS from all three stages
  - All converge to SINGLE metrics_episode() interface
  - Green success box: "✓ NO DIVERGENCE"
  - Demonstrates how contract prevents divergence

[BOTTOM PANEL] Concrete Example
  - Policy A ranking inconsistency scenario
  - LEFT (Divergent):
    * Stage 1 reads mean_biomass = 50.5 → Rank #3
    * Stage 2 reads q75_biomass = 57.5 → Rank #7
  - RIGHT (HEAS):
    * All stages read mean_biomass = 50.5 → Rank #3 everywhere
  - Demonstrates practical impact of divergence prevention

VISUAL STYLE:
  ✓ Gray background boxes for component clarity
  ✓ Blue arrows (#1f77b4) for HEAS correct paths
  ✓ Red dashed arrows (#d62728) for divergent paths
  ✓ Green highlights for success state
  ✓ Minimal chart junk, academic quality
  ✓ Publication-ready for printing/PDF inclusion
  ✓ Grayscale-readable (color not required for comprehension)

USAGE:
  1. PDF: Include in LaTeX with \includegraphics[width=\columnwidth]{fig_contract_architecture.pdf}
  2. PNG: Use for web/presentation displays at 96 DPI or higher
  3. Figure caption (suggested):
     "Figure X: The metrics_episode() contract architecture prevents silent
      aggregation divergence. (Left) Arena/Streams/Layers composition hierarchy.
      (Center) The single metrics_episode() interface. (Right) Pipeline stages
      that call the contract. (Top) Without the contract, different stages may
      call different aggregation functions, causing divergence in computed
      metrics. (Bottom) The HEAS solution ensures all stages access a single
      interface, preventing rank inversions (example: Policy A would incorrectly
      rank #7 vs. #3 without the contract)."

TECHNICAL NOTES:
  - Generated using: matplotlib 3.10.8
  - Script: gen_figure_contract_architecture.py
  - Supervisor-approved scope
  - Strict alignment with WSC format requirements
  - All matplotlib rcParams set for publication quality
  - PDF Version 1.4 (broad compatibility)

================================================================================
