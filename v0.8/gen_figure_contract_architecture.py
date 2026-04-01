#!/usr/bin/env python3
"""
Generate Figure X: HEAS metrics_episode() Contract Architecture
WSC 2026 Paper

Illustrates:
1. The Layer/Stream/Arena composition hierarchy
2. The metrics_episode() contract preventing silent aggregation divergence
3. Comparison: divergent paths vs. HEAS unified path
4. Concrete example: how divergence manifests in policy ranking
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
import numpy as np

# Set publication-quality rcParams
plt.rcParams.update({
    'font.family': 'Liberation Serif',
    'font.size': 7,
    'axes.linewidth': 0.5,
    'lines.linewidth': 0.75,
    'patch.linewidth': 0.5,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white',
})

fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Color scheme for publication
color_bg = '#f5f5f5'
color_border = '#333333'
color_heas_arrow = '#1f77b4'  # Blue
color_diverge_arrow = '#d62728'  # Red
color_success = '#2ca02c'  # Green

# ============================================================================
# SECTION 1: LEFT - Arena / Streams / Layers (Hierarchy)
# ============================================================================
x_left = 0.5
y_base = 2.0

# Title
ax.text(x_left + 0.8, 9.2, 'Arena/Streams/Layers', fontsize=8, fontweight='bold',
        ha='center', va='top')

# Arena box
arena_box = FancyBboxPatch((x_left, y_base + 2.0), 1.6, 1.2,
                           boxstyle="round,pad=0.08",
                           facecolor=color_bg, edgecolor=color_border, linewidth=0.8)
ax.add_patch(arena_box)
ax.text(x_left + 0.8, y_base + 2.5, 'Arena', fontsize=7, fontweight='bold',
        ha='center', va='center')

# Streams (3 boxes)
stream_y = y_base + 0.6
for i, stream_name in enumerate(['S1', 'S2', 'S3']):
    stream_box = FancyBboxPatch((x_left + i*0.55, stream_y), 0.5, 0.5,
                               boxstyle="round,pad=0.04",
                               facecolor=color_bg, edgecolor=color_border, linewidth=0.6)
    ax.add_patch(stream_box)
    ax.text(x_left + i*0.55 + 0.25, stream_y + 0.25, stream_name, fontsize=6,
            ha='center', va='center')

    # Arrow from Arena to Stream
    arrow = FancyArrowPatch((x_left + 0.8, y_base + 2.0),
                           (x_left + i*0.55 + 0.25, stream_y + 0.5),
                           arrowstyle='->', mutation_scale=10, linewidth=0.5,
                           color=color_border)
    ax.add_patch(arrow)

# Layers (under first stream as example)
layer_y = y_base - 0.5
for i, layer_name in enumerate(['L1', 'L2']):
    layer_box = FancyBboxPatch((x_left + i*0.55, layer_y), 0.5, 0.4,
                              boxstyle="round,pad=0.03",
                              facecolor='#e8e8e8', edgecolor=color_border, linewidth=0.5)
    ax.add_patch(layer_box)
    ax.text(x_left + i*0.55 + 0.25, layer_y + 0.2, layer_name, fontsize=6,
            ha='center', va='center')

    # Arrow from first stream to layers
    if i == 0:
        arrow = FancyArrowPatch((x_left + 0.25, stream_y),
                               (x_left + 0.25, layer_y + 0.4),
                               arrowstyle='->', mutation_scale=8, linewidth=0.4,
                               color=color_border)
        ax.add_patch(arrow)

ax.text(x_left + 0.8, layer_y - 0.3, '(Hierarchy)', fontsize=6,
        ha='center', va='top', style='italic', color='#555555')

# ============================================================================
# SECTION 2: CENTER - metrics_episode() Contract
# ============================================================================
x_center = 3.5

# Section title
ax.text(x_center, 9.2, 'metrics_episode() Contract', fontsize=8, fontweight='bold',
        ha='center', va='top')

# Contract interface box
contract_box = FancyBboxPatch((x_center - 0.9, 5.5), 1.8, 2.0,
                             boxstyle="round,pad=0.1",
                             facecolor='#ffffcc', edgecolor='#cc9900', linewidth=1.0)
ax.add_patch(contract_box)

# Contract details
ax.text(x_center, 7.2, 'SINGLE', fontsize=7, fontweight='bold',
        ha='center', va='center')
ax.text(x_center, 6.8, 'Interface', fontsize=7, fontweight='bold',
        ha='center', va='center')

# Method signature (simplified)
ax.text(x_center, 6.3, 'def metrics_episode(', fontsize=5.5, ha='center', va='center',
        family='monospace')
ax.text(x_center, 6.0, '  obs, actions, rewards', fontsize=5.5, ha='center', va='center',
        family='monospace')
ax.text(x_center, 5.7, ') → metrics_dict', fontsize=5.5, ha='center', va='center',
        family='monospace')

# ============================================================================
# SECTION 3: RIGHT - Pipeline Stages (Optimizer, Tournament, Inference)
# ============================================================================
x_right = 7.5

# Section title
ax.text(x_right, 9.2, 'Pipeline Stages', fontsize=8, fontweight='bold',
        ha='center', va='top')

# Three stages
stages = [
    ('Optimizer', 7.2),
    ('Tournament', 5.8),
    ('Inference', 4.4),
]

stage_boxes = []
for stage_name, y_pos in stages:
    stage_box = FancyBboxPatch((x_right - 0.7, y_pos - 0.35), 1.4, 0.6,
                              boxstyle="round,pad=0.05",
                              facecolor=color_bg, edgecolor=color_border, linewidth=0.7)
    ax.add_patch(stage_box)
    ax.text(x_right, y_pos, stage_name, fontsize=7, fontweight='bold',
            ha='center', va='center')
    stage_boxes.append((x_right - 0.7, y_pos))

# ============================================================================
# SECTION 4: DIVERGENCE PROBLEM (Top half)
# ============================================================================
y_diverg = 7.5

# Label
ax.text(0.5, y_diverg + 0.8, 'DIVERGENT PATH (without contract):', fontsize=6.5,
        fontweight='bold', ha='left', va='bottom', color=color_diverge_arrow)

# Left divergence: Optimizer → different aggregation functions
arrow1 = FancyArrowPatch((x_right - 0.7, 7.2),
                        (x_center - 1.2, y_diverg + 0.2),
                        arrowstyle='->', mutation_scale=12, linewidth=1.0,
                        color=color_diverge_arrow, linestyle='--')
ax.add_patch(arrow1)
ax.text(x_center - 1.8, y_diverg + 0.3, 'mean_biomass', fontsize=5.5,
        ha='center', va='bottom', family='monospace', color=color_diverge_arrow)

# Right divergence: Tournament → different aggregation function
arrow2 = FancyArrowPatch((x_right - 0.7, 5.8),
                        (x_center + 1.2, y_diverg + 0.2),
                        arrowstyle='->', mutation_scale=12, linewidth=1.0,
                        color=color_diverge_arrow, linestyle='--')
ax.add_patch(arrow2)
ax.text(x_center + 1.8, y_diverg + 0.3, 'q75_biomass', fontsize=5.5,
        ha='center', va='bottom', family='monospace', color=color_diverge_arrow)

# Divergence warning box
div_warning = Rectangle((x_center - 1.0, y_diverg - 0.3), 2.0, 0.25,
                        facecolor=color_diverge_arrow, alpha=0.15, edgecolor=color_diverge_arrow,
                        linewidth=0.7, linestyle='--')
ax.add_patch(div_warning)
ax.text(x_center, y_diverg - 0.175, '✗ DIVERGENCE', fontsize=6, fontweight='bold',
        ha='center', va='center', color=color_diverge_arrow)

# ============================================================================
# SECTION 5: HEAS SOLUTION (Bottom half)
# ============================================================================
y_heas = 3.5

# Label
ax.text(0.5, y_heas + 0.8, 'HEAS UNIFIED PATH (with contract):', fontsize=6.5,
        fontweight='bold', ha='left', va='bottom', color=color_heas_arrow)

# All three stages point to contract
for stage_name, stage_y in stages:
    arrow = FancyArrowPatch((x_right - 0.7, stage_y - 0.35 if stage_y < y_heas + 1 else stage_y - 0.35),
                           (x_center, y_heas + 0.2),
                           arrowstyle='->', mutation_scale=12, linewidth=1.0,
                           color=color_heas_arrow)
    ax.add_patch(arrow)

# HEAS contract box
heas_contract_box = FancyBboxPatch((x_center - 0.85, y_heas - 0.3), 1.7, 0.5,
                                   boxstyle="round,pad=0.06",
                                   facecolor='#ccffcc', edgecolor=color_heas_arrow, linewidth=1.0)
ax.add_patch(heas_contract_box)
ax.text(x_center, y_heas, 'metrics_episode()', fontsize=6.5, fontweight='bold',
        ha='center', va='center', family='monospace', color=color_heas_arrow)

# Success box
success_box = Rectangle((x_center - 1.0, y_heas - 1.0), 2.0, 0.25,
                       facecolor=color_success, alpha=0.15, edgecolor=color_success,
                       linewidth=0.7)
ax.add_patch(success_box)
ax.text(x_center, y_heas - 0.875, '✓ NO DIVERGENCE', fontsize=6, fontweight='bold',
        ha='center', va='center', color=color_success)

# ============================================================================
# SECTION 6: CONCRETE EXAMPLE (Bottom inset)
# ============================================================================
y_example = 1.0
x_example = 0.4

# Example box frame
example_frame = FancyBboxPatch((x_example - 0.1, y_example - 0.85), 9.2, 0.95,
                              boxstyle="round,pad=0.08",
                              facecolor='#fafafa', edgecolor='#888888', linewidth=0.7)
ax.add_patch(example_frame)

ax.text(x_example, y_example + 0.08, 'Example: Policy A (Rank inconsistency)', fontsize=6.5,
        fontweight='bold', ha='left', va='top')

# Left side: divergence problem
ax.text(x_example, y_example - 0.1, 'Divergent:', fontsize=6, fontweight='bold',
        ha='left', va='top', color=color_diverge_arrow)
ax.text(x_example, y_example - 0.32, 'Stage 1: mean_biomass = 50.5', fontsize=5.5,
        ha='left', va='top', family='monospace')
ax.text(x_example, y_example - 0.48, '  ↓ Rank #3', fontsize=5.5,
        ha='left', va='top', family='monospace', color='#555')
ax.text(x_example + 2.5, y_example - 0.32, 'Stage 2: q75_biomass = 57.5', fontsize=5.5,
        ha='left', va='top', family='monospace')
ax.text(x_example + 2.5, y_example - 0.48, '  ↓ Rank #7', fontsize=5.5,
        ha='left', va='top', family='monospace', color='#555')

# Center: arrow or separator
ax.plot([5.0, 5.0], [y_example - 0.15, y_example - 0.6], 'k-', linewidth=0.5, alpha=0.3)
ax.text(5.0, y_example - 0.37, 'vs.', fontsize=6, ha='center', va='center',
        style='italic', color='#888888')

# Right side: HEAS solution
ax.text(x_example + 5.2, y_example - 0.1, 'HEAS:', fontsize=6, fontweight='bold',
        ha='left', va='top', color=color_heas_arrow)
ax.text(x_example + 5.2, y_example - 0.32, 'All stages: mean_biomass = 50.5', fontsize=5.5,
        ha='left', va='top', family='monospace')
ax.text(x_example + 5.2, y_example - 0.48, '  ↓ Rank #3 everywhere', fontsize=5.5,
        ha='left', va='top', family='monospace', color=color_heas_arrow, fontweight='bold')

# ============================================================================
# Add figure label
# ============================================================================
ax.text(0.3, -0.3, 'Figure X: HEAS metrics_episode() Contract Architecture',
        fontsize=7, ha='left', va='top', style='italic')

plt.tight_layout(pad=0.1)

# Save as PDF and PNG
pdf_path = '/sessions/zen-hopeful-noether/mnt/heas/v0.5/figs/fig_contract_architecture.pdf'
png_path = '/sessions/zen-hopeful-noether/mnt/heas/v0.5/figs/fig_contract_architecture.png'

plt.savefig(pdf_path, format='pdf', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print(f"✓ PDF saved: {pdf_path}")

plt.savefig(png_path, format='png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print(f"✓ PNG saved: {png_path}")

plt.close()

print("\n" + "="*70)
print("FIGURE GENERATION COMPLETE")
print("="*70)
print(f"Figure size: 6.4 × 3.2 inches (fits single WSC column width)")
print(f"Font: Liberation Serif, 7pt labels, PDF fonttype=42")
print(f"Resolution: 300 DPI")
print(f"\nContents:")
print(f"  LEFT:   Arena/Streams/Layers composition hierarchy")
print(f"  CENTER: metrics_episode() contract interface")
print(f"  RIGHT:  Three pipeline stages (Optimizer, Tournament, Inference)")
print(f"\nVisualization:")
print(f"  Red dashed arrows: divergent paths (problem)")
print(f"  Blue arrows: unified HEAS path (solution)")
print(f"  Bottom panel: concrete ranking example showing divergence effect")
print("="*70)
