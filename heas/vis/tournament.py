from __future__ import annotations
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_tournament_overview(
    per_episode: pd.DataFrame,
    scenario_col: str = "scenario",
    participant_col: str = "participant",
    score_col: str = "score",
    save: Optional[str] = None,
):
    """For each scenario, show participants' average scores with error bars."""
    stats = (per_episode
             .groupby([scenario_col, participant_col])[score_col]
             .agg(["mean","std","count"])
             .reset_index())
    scens = list(stats[scenario_col].unique())
    parts = list(stats[participant_col].unique())
    fig, ax = plt.subplots(figsize=(1.5*len(scens)+2, 4))
    width = 0.8 / max(1,len(parts))
    for i,p in enumerate(parts):
        vals = []
        err  = []
        for sc in scens:
            row = stats[(stats[scenario_col]==sc) & (stats[participant_col]==p)]
            vals.append(row["mean"].iloc[0] if not row.empty else 0.0)
            err.append(row["std"].iloc[0] if not row.empty else 0.0)
        xs = np.arange(len(scens)) + i*width
        ax.bar(xs, vals, width=width, yerr=err, capsize=3, label=p)
    ax.set_xticks(np.arange(len(scens)) + (len(parts)-1)*width/2)
    ax.set_xticklabels(scens, rotation=30, ha="right")
    ax.set_ylabel("score (mean ± std)")
    ax.set_title("Tournament scores by scenario")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig

def plot_tournament_scores_by_scenario(
    per_episode: pd.DataFrame,
    scenario: str,
    participant_col: str = "participant",
    score_col: str = "score",
    episode_col: str = "episode_id",
    save: Optional[str] = None,
):
    """Within a single scenario, plot per-episode scores over time by participant."""
    sub = per_episode[per_episode["scenario"] == scenario]
    parts = list(sub[participant_col].unique())
    fig, ax = plt.subplots(figsize=(6,4))
    for p in parts:
        g = sub[sub[participant_col]==p].sort_values(episode_col)
        ax.plot(g[episode_col].to_numpy(), g[score_col].to_numpy(), marker="o", label=p)
    ax.set_xlabel("episode"); ax.set_ylabel("score")
    ax.set_title(f"Scores over episodes — {scenario}")
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
    return fig