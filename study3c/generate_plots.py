"""
Generér Study 3c plots.

Hovedplot: NPS − LRTF advantage vs ρ, opdelt på topic_aware × intercept
(direkte test af H1). Sekundære plots: 2×2 panel over discipliner og en
diagnostik over varians af predicted_nps.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"


# =============================================================================
# Fig. S3c.1: Hovedplot — NPS − LRTF advantage vs ρ pr. (topic_aware, intercept)
# =============================================================================

def make_fig_s3c_1(df):
    """NPS − LRTF advantage vs ρ. Fire kurver: 2 topic_aware × 2 intercepts."""
    rhos = sorted(df["rho"].unique())
    intercepts = sorted(df["nps_intercept"].unique(), reverse=True)
    topic_levels = sorted(df["topic_aware"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    style_for = {
        (False, intercepts[0]): {"color": "#1f77b4", "linestyle": "-",  "marker": "o",
                                   "label": f"topic-blind, int={intercepts[0]:.2f}"},
        (False, intercepts[-1]): {"color": "#1f77b4", "linestyle": "--", "marker": "s",
                                    "label": f"topic-blind, int={intercepts[-1]:.2f}"},
        (True,  intercepts[0]): {"color": "#d62728", "linestyle": "-",  "marker": "o",
                                   "label": f"topic-aware, int={intercepts[0]:.2f}"},
        (True,  intercepts[-1]): {"color": "#d62728", "linestyle": "--", "marker": "s",
                                    "label": f"topic-aware, int={intercepts[-1]:.2f}"},
    }

    for metric_idx, (metric, ylabel, fmt) in enumerate([
        ("avg_individual_nps", "NPS − LRTF (individual NPS units)", "{:+.4f}"),
        ("organisation_nps", "NPS − LRTF (organisation NPS %-points)", "{:+.2f}"),
    ]):
        ax = axes[metric_idx]
        for topic_aware in topic_levels:
            for nps_int in intercepts:
                advantages = []
                for rho in rhos:
                    nps_sub = df[(df["topic_aware"] == topic_aware)
                                   & (df["nps_intercept"] == nps_int)
                                   & (df["rho"] == rho)
                                   & (df["discipline"] == "NPS")]
                    lrtf_sub = df[(df["topic_aware"] == topic_aware)
                                    & (df["nps_intercept"] == nps_int)
                                    & (df["rho"] == rho)
                                    & (df["discipline"] == "LRTF")]
                    if len(nps_sub) > 0 and len(lrtf_sub) > 0:
                        advantages.append(nps_sub[metric].mean() - lrtf_sub[metric].mean())
                    else:
                        advantages.append(np.nan)

                style = style_for.get((topic_aware, nps_int), {})
                ax.plot(rhos, advantages, linewidth=1.7, markersize=5, **style)

        ax.axhline(0, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
        ax.set_xlabel(r"Prediction accuracy ($\rho$)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, frameon=True, loc="best")

    fig.suptitle("Figure S3c.1: Multi-predictor NPS — does topic-awareness break NPS ≡ LRTF?",
                 y=1.02, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3c_1_main_effect.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3c.2: 2×2 panel — alle discipliner pr. (topic_aware, intercept)
# =============================================================================

def make_fig_s3c_2(df):
    """2×2 panel: rækker=topic_aware, kolonner=intercept; FCFS/LRTF/NPS over ρ."""
    rhos = sorted(df["rho"].unique())
    intercepts = sorted(df["nps_intercept"].unique(), reverse=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True)

    disc_styles = {
        "FCFS": {"color": "#7f7f7f", "linestyle": ":",  "marker": "x", "label": "FCFS"},
        "LRTF": {"color": "#1f77b4", "linestyle": "--", "marker": "s", "label": "LRTF"},
        "NPS":  {"color": "#d62728", "linestyle": "-",  "marker": "o", "label": "NPS"},
    }

    # FCFS er kun lagret for ét (topic_aware, intercept) — brug det som baseline overalt
    fcfs_data = df[df["discipline"] == "FCFS"]

    for row_idx, topic_aware in enumerate([False, True]):
        for col_idx, nps_int in enumerate(intercepts):
            ax = axes[row_idx, col_idx]

            for disc in ["FCFS", "LRTF", "NPS"]:
                if disc == "FCFS":
                    sub = fcfs_data
                else:
                    sub = df[(df["topic_aware"] == topic_aware)
                              & (df["nps_intercept"] == nps_int)
                              & (df["discipline"] == disc)]
                means = []
                for rho in rhos:
                    rsub = sub[sub["rho"] == rho]
                    means.append(rsub["avg_individual_nps"].mean() if len(rsub) > 0 else np.nan)
                ax.plot(rhos, means, linewidth=1.5, markersize=4, **disc_styles[disc])

            ax.set_title(f"topic_aware={topic_aware}, intercept={nps_int:.2f}",
                          fontsize=10)
            ax.grid(True, alpha=0.3)
            if col_idx == 0:
                ax.set_ylabel("Avg. individual NPS")
            if row_idx == 1:
                ax.set_xlabel(r"Prediction accuracy ($\rho$)")
            if row_idx == 0 and col_idx == 0:
                ax.legend(fontsize=8, frameon=True)

    fig.suptitle("Figure S3c.2: Disciplines × topic_aware × intercept",
                 y=1.00, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3c_2_2x2_grid.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3c.3: Varians-diagnostik
# =============================================================================

def make_fig_s3c_3(df):
    """Bar chart: Var(predicted_nps) pr. (topic_aware × intercept) — confound-tjek."""
    intercepts = sorted(df["nps_intercept"].unique(), reverse=True)
    cells = []
    labels = []
    colors = []

    color_map = {False: "#1f77b4", True: "#d62728"}

    for topic_aware in [False, True]:
        for nps_int in intercepts:
            sub = df[(df["topic_aware"] == topic_aware)
                      & (df["nps_intercept"] == nps_int)]
            if len(sub) > 0:
                cells.append(sub["predicted_nps_variance"].mean())
                labels.append(f"ta={topic_aware}\nint={nps_int:.2f}")
                colors.append(color_map[topic_aware])

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(range(len(cells)), cells, color=colors, edgecolor="black",
                    linewidth=0.5)
    ax.set_xticks(range(len(cells)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Var(predicted_nps)")
    ax.set_title("Figure S3c.3: Variance of predicted_nps per cell\n"
                  "(diagnostic — checks whether topic-awareness inflates spread)")
    ax.grid(True, axis="y", alpha=0.3)

    for i, v in enumerate(cells):
        ax.text(i, v, f"{v:.4f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3c_3_variance_diagnostic.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"FEJL: {CSV_PATH} findes ikke.")
        raise SystemExit(1)

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} runs")
    print(f"  topic_aware: {sorted(df['topic_aware'].unique())}")
    print(f"  Intercepts:  {sorted(df['nps_intercept'].unique())}")
    print(f"  ρ:           {sorted(df['rho'].unique())}")
    print(f"  Disciplines: {sorted(df['discipline'].unique())}")
    print()

    make_fig_s3c_1(df)
    make_fig_s3c_2(df)
    make_fig_s3c_3(df)

    print("\nAll plots generated.")
