from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

def build_architecture(spec_or_model: Any) -> Dict[str, Any]:
    """
    Return {"layers":[[{"name":..., "class":...}, ...], ...]}
    Works with a List[LayerSpec] or a CompositeHeasModel.
    Edges are optional — wiring is domain-specific (via ctx.data).
    """
    layers_out: List[List[Dict[str, str]]] = []
    # Lazy imports to avoid tight coupling
    try:
        from ..hierarchy.orchestrator import CompositeHeasModel  # type: ignore
        from ..hierarchy.base import Layer  # type: ignore
        from ..hierarchy import LayerSpec  # type: ignore
    except Exception:
        CompositeHeasModel = object  # type: ignore
        Layer = object              # type: ignore
        LayerSpec = object          # type: ignore

    if isinstance(spec_or_model, list):  # spec
        for L in spec_or_model:
            row = []
            for sp in getattr(L, "streams", []):
                row.append({"name": getattr(sp, "name", "?"),
                            "class": getattr(getattr(sp, "cls", None), "__name__", "Stream")})
            layers_out.append(row)
    elif isinstance(spec_or_model, CompositeHeasModel):
        for L in getattr(spec_or_model.graph, "layers", []):
            row = []
            for s in getattr(L, "streams", []):
                row.append({"name": getattr(s, "name", "?"),
                            "class": s.__class__.__name__})
            layers_out.append(row)
    else:
        raise TypeError("Pass a List[LayerSpec] or a CompositeHeasModel instance.")

    return {"layers": layers_out}

def plot_architecture(
    spec_or_model: Any,
    edges: Optional[List[Tuple[str,str]]] = None,  # optional (src_name, dst_name)
    figsize=(8, 3.5),
    save: Optional[str] = None
):
    """Draw layered boxes; optional edges by stream name."""
    arch = build_architecture(spec_or_model)
    layers: List[List[Dict[str,str]]] = arch["layers"]
    L = len(layers)
    fig, ax = plt.subplots(figsize=figsize)
    centers: Dict[str, Tuple[float,float]] = {}
    for i, row in enumerate(layers):
        x = 1 + i*3.2
        n = max(1, len(row))
        for j, node in enumerate(row):
            y = 1 + (n-1-j)*1.5
            box = FancyBboxPatch(
                (x-0.9, y-0.35), 1.8, 0.7,
                boxstyle="round,pad=0.03,rounding_size=0.07", linewidth=1.0, edgecolor="black", facecolor="white"
            )
            ax.add_patch(box)
            ax.text(x, y, f"{node['name']}\n[{node['class']}]", ha="center", va="center", fontsize=9)
            centers[node["name"]] = (x, y)
    # arrows
    if edges:
        for src, dst in edges:
            if src in centers and dst in centers:
                (x1,y1) = centers[src]; (x2,y2) = centers[dst]
                ax.annotate("", xy=(x2-0.9, y2), xytext=(x1+0.9, y1),
                            arrowprops=dict(arrowstyle="->", lw=1.0))
    ax.set_axis_off()
    ax.set_xlim(0, 1 + (L)*3.2)
    # autoscale y
    ymax = 1 + max(1, max(len(r) for r in layers))*1.6
    ax.set_ylim(0, ymax)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig

def render_architecture_ascii(spec_or_model: Any) -> str:
    arch = build_architecture(spec_or_model)
    layers: List[List[Dict[str,str]]] = arch["layers"]
    lines = ["# HEAS Architecture"]
    for i, row in enumerate(layers, start=1):
        lines.append(f"Layer {i}:")
        for node in row:
            lines.append(f"  - {node['name']} [{node['class']}]")
    return "\n".join(lines)