from __future__ import annotations
from typing import Iterable, List, Optional, Sequence, Dict, Any
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def _first_existing(df: pd.DataFrame, candidates: Sequence[str], default: Optional[str]=None) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return default

def plot_steps(
    df: pd.DataFrame,
    x: Optional[str] = None,
    y_cols: Optional[List[str]] = None,
    facet_by: Optional[str] = "scenario",
    hue: Optional[str] = "participant",
    title: Optional[str] = None,
    save: Optional[str] = None,
):
    """Line plots of per-step metrics. Facet by scenario, hue by participant."""
    if x is None:
        x = _first_existing(df, ["t","Step","step","time"], default=None)
        if x is None:
            raise ValueError("Could not infer x column; pass x='t' or similar.")
    if y_cols is None:
        # take numeric columns except ids
        skip = {x, "scenario","participant","episode_id"}
        y_cols = [c for c in df.columns if c not in skip and pd.api.types.is_numeric_dtype(df[c])]
        if not y_cols:
            raise ValueError("No numeric y columns found to plot.")
    cats = ["__all__"]
    if facet_by and facet_by in df.columns:
        cats = sorted(df[facet_by].dropna().unique())
    n = len(cats)
    rows = math.ceil(n / 2)
    cols = 1 if n == 1 else 2
    fig, axes = plt.subplots(rows, cols, figsize=(6*cols, 3.5*rows), squeeze=False)
    ax_iter = iter(axes.flat)
    for cat in cats:
        ax = next(ax_iter)
        sub = df if cat == "__all__" else df[df[facet_by] == cat]
        # plot each y with an average over episodes per participant
        if hue and hue in sub.columns:
            for hval, g in sub.groupby(hue):
                # average across episodes at same t
                piv = g.groupby(x)[y_cols].mean().reset_index()
                for y in y_cols:
                    ax.plot(piv[x].to_numpy(), piv[y].to_numpy(), label=f"{hval} · {y}")
        else:
            piv = sub.groupby(x)[y_cols].mean().reset_index()
            for y in y_cols:
                ax.plot(piv[x].to_numpy(), piv[y].to_numpy(), label=y)
        ax.set_xlabel(x)
        ax.set_ylabel(", ".join(y_cols[:2]) + ("..." if len(y_cols)>2 else ""))
        ax.set_title(str(cat))
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)
    # tidy remaining axes
    for ax in ax_iter:
        ax.axis("off")
    if title:
        fig.suptitle(title, y=1.02)
        fig.tight_layout()
    else:
        fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig

def plot_votes_matrix(
    votes_df: pd.DataFrame,
    scenario_col: str = "scenario",
    episode_col: str = "episode_id",
    winner_col: str = "winner",
    save: Optional[str] = None,
):
    """Episode winners per scenario as a matrix image."""
    scens = sorted(votes_df[scenario_col].unique())
    eps = sorted(votes_df[episode_col].unique())
    label_map = {lab:i for i, lab in enumerate(sorted(votes_df[winner_col].unique()))}
    mat = np.full((len(scens), len(eps)), np.nan)
    for i, sc in enumerate(scens):
        sub = votes_df[votes_df[scenario_col]==sc]
        for j, e in enumerate(eps):
            row = sub[sub[episode_col]==e]
            if not row.empty:
                mat[i,j] = label_map[row[winner_col].iloc[0]]
    fig, ax = plt.subplots(figsize=(1.2*len(eps)+2, 0.6*len(scens)+2))
    im = ax.imshow(mat, aspect="auto")
    ax.set_xticks(range(len(eps)))
    ax.set_xticklabels(eps)
    ax.set_yticks(range(len(scens)))
    ax.set_yticklabels(scens)
    ax.set_xlabel("episode")
    ax.set_title("winners per scenario × episode")
    # colorbar with textual ticks
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    rev = {v:k for k,v in label_map.items()}
    cbar.set_ticks(list(rev.keys()))
    cbar.set_ticklabels([str(rev[k]) for k in rev.keys()])
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig

def plot_votes_bar(
    votes_df: pd.DataFrame,
    scenario_col: str = "scenario",
    winner_col: str = "winner",
    save: Optional[str] = None,
):
    """Bar counts of winners per scenario."""
    counts = votes_df.groupby([scenario_col, winner_col]).size().reset_index(name="n")
    scens = sorted(counts[scenario_col].unique())
    winners = sorted(counts[winner_col].unique())
    fig, ax = plt.subplots(figsize=(1.5*len(scens)+2, 4))
    width = 0.8 / max(1, len(winners))
    for idx, w in enumerate(winners):
        vals = []
        for sc in scens:
            row = counts[(counts[scenario_col]==sc) & (counts[winner_col]==w)]
            vals.append(int(row["n"].iloc[0]) if not row.empty else 0)
        xs = np.arange(len(scens)) + idx*width
        ax.bar(xs, vals, width=width, label=str(w))
    ax.set_xticks(np.arange(len(scens)) + (len(winners)-1)*width/2)
    ax.set_xticklabels(scens, rotation=30, ha="right")
    ax.set_ylabel("wins")
    ax.set_title("winner counts per scenario")
    ax.legend(title="winner")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig

def plot_ea_log(log: Any, save: Optional[str] = None):
    """Generic DEAP logbook curve. Accepts:
       - a deap.tools.Logbook
       - a list of dicts with keys: 'gen', 'min', 'avg', 'max' (values can be scalars or tuples)
    """
    # extract records
    try:
        records = list(log) if isinstance(log, list) else log if hasattr(log, "__iter__") else []
    except Exception:
        records = []

    if not records and hasattr(log, "chapters"):  # Logbook with chapters
        try:
            gen = list(log.select("gen"))
            minv = log.select("min")
            avgv = log.select("avg")
            maxv = log.select("max")
            records = [{"gen":g, "min":m, "avg":a, "max":x} for g,m,a,x in zip(gen,minv,avgv,maxv)]
        except Exception:
            records = []

    if not records:
        raise ValueError("Could not interpret log; pass a Logbook or list of {gen,min,avg,max} dicts.")

    def _scalar(v):
        if isinstance(v, (list, tuple)) and v:
            return float(v[0])
        return float(v)

    G = [r.get("gen", i) for i, r in enumerate(records)]
    MIN = [_scalar(r.get("min", np.nan)) for r in records]
    AVG = [_scalar(r.get("avg", np.nan)) for r in records]
    MAX = [_scalar(r.get("max", np.nan)) for r in records]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(G, MIN, label="min")
    ax.plot(G, AVG, label="avg")
    ax.plot(G, MAX, label="max")
    ax.set_xlabel("generation"); ax.set_ylabel("fitness")
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig

def plot_pareto(points: np.ndarray, save: Optional[str] = None, title: str = "Pareto"):
    """Scatter plot of Nx2 objective array (min-min)."""
    pts = np.asarray(points)
    if pts.ndim != 2 or pts.shape[1] < 2:
        raise ValueError("points must be array-like with shape (N,2+)")

    fig, ax = plt.subplots(figsize=(5.5,4.5))
    ax.scatter(pts[:,0], pts[:,1], s=20)
    ax.set_xlabel("obj1"); ax.set_ylabel("obj2"); ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig