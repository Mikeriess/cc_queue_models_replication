"""
Generér Study 3 plots fra results.csv.

Producerer:
    Fig. S3.1: Individual NPS vs ρ (3 discipliner × 2 sampling modes)
    Fig. S3.2: NPS - LRTF advantage vs ρ (diagnostisk, 3 agent-niveauer)
    Fig. S3.3: Organisation NPS vs ρ
    Fig. S3.4: Case resolution time vs ρ
    Fig. S3.5: Waiting time vs ρ

Hypothesen (Fig. S3.1 og S3.2): NPS-kurven skal divergere opad fra LRTF
ved høj ρ. Ved ρ=0 skal NPS ≈ LRTF (ingen information). FCFS skal være
ρ-invariant som sanity check.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = RESULTS_DIR / "results.csv"

# =============================================================================
# Farver og design
# =============================================================================

DISCIPLINES = ["FCFS", "LRTF", "NPS"]
COLORS = {
    "NPS": "#d62728",
    "LRTF": "#2ca02c",
    "SRTF": "#1f77b4",
    "FCFS": "#ff7f0e",
}
SAMPLING_MODES = ["hard", "soft"]
MODE_LABELS = {"hard": "Hard Z (perfect activity correlation)",
               "soft": "Soft Z (z as feature, target corr = 0.5)"}


def aggregate(df: pd.DataFrame, metric: str,
              groupby=("rho", "sampling_mode", "discipline", "n_agents")):
    """Mean + 95% CI over replikationer for hver kombination."""
    grp = df.groupby(list(groupby))[metric]
    agg = grp.agg(["mean", "std", "count"]).reset_index()
    agg["sem"] = agg["std"] / np.sqrt(agg["count"])
    agg["ci95"] = 1.96 * agg["sem"]
    return agg


def plot_metric_vs_rho(ax, agg: pd.DataFrame, metric_col: str,
                        mode: str, n_agents: int, ylabel: str,
                        show_legend: bool = False):
    """Plot én metric som funktion af ρ, med fejlbarer og én linje pr. disciplin."""
    sub = agg[(agg["sampling_mode"] == mode) & (agg["n_agents"] == n_agents)]

    for disc in DISCIPLINES:
        disc_data = sub[sub["discipline"] == disc].sort_values("rho")
        ax.errorbar(
            disc_data["rho"], disc_data["mean"],
            yerr=disc_data["ci95"],
            label=disc,
            color=COLORS[disc],
            marker="o",
            capsize=3,
            linewidth=1.5,
            markersize=5,
        )
    ax.set_xlabel(r"Prediction accuracy ($\rho$)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    if show_legend:
        ax.legend(loc="best", fontsize=9, frameon=True)


# =============================================================================
# Fig. S3.1: Individual NPS vs ρ
# =============================================================================

def make_fig_s3_1(df: pd.DataFrame):
    """
    Hovedresultat: individual NPS vs ρ, 3 agent-niveauer × 2 sampling modes.

    6 paneler i alt (3 rækker × 2 kolonner).
    """
    agg = aggregate(df, "avg_individual_nps")

    fig, axes = plt.subplots(3, 2, figsize=(10, 11), sharex=True)

    for row, n_agents in enumerate([5, 6, 7]):
        for col, mode in enumerate(SAMPLING_MODES):
            ax = axes[row, col]
            plot_metric_vs_rho(
                ax, agg, "avg_individual_nps", mode, n_agents,
                "Avg. individual NPS response",
                show_legend=(row == 0 and col == 0),
            )
            if row == 0:
                ax.set_title(MODE_LABELS[mode], fontsize=10)
            if col == 0:
                ax.text(-0.25, 0.5, f"Agents = {n_agents}",
                        transform=ax.transAxes, rotation=90,
                        va="center", fontsize=11, fontweight="bold")

    fig.suptitle("Figure S3.1: The value of information — individual NPS vs prediction accuracy",
                 y=1.01, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3_1_nps_vs_rho.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3.2: NPS - LRTF advantage vs ρ
# =============================================================================

def make_fig_s3_2(df: pd.DataFrame):
    """
    Diagnostisk plot: NPS - LRTF advantage vs ρ, 3 agent-niveauer pr. panel.

    Hvis hypotesen holder, skal kurven være ≈0 ved ρ=0 og positiv ved høj ρ.
    """
    agg = aggregate(df, "avg_individual_nps")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)

    for col, mode in enumerate(SAMPLING_MODES):
        ax = axes[col]
        sub = agg[agg["sampling_mode"] == mode]

        agent_colors = {5: "#1f77b4", 6: "#ff7f0e", 7: "#2ca02c"}

        for n_agents in [5, 6, 7]:
            nps_data = sub[(sub["discipline"] == "NPS") & (sub["n_agents"] == n_agents)].sort_values("rho")
            lrtf_data = sub[(sub["discipline"] == "LRTF") & (sub["n_agents"] == n_agents)].sort_values("rho")

            # Forskel per ρ
            advantage = nps_data["mean"].values - lrtf_data["mean"].values
            # Kombineret SE (antager uafhængighed — konservativt)
            se_combined = np.sqrt(
                (nps_data["sem"].values ** 2) + (lrtf_data["sem"].values ** 2)
            )
            ci95 = 1.96 * se_combined

            ax.errorbar(
                nps_data["rho"].values, advantage,
                yerr=ci95,
                label=f"{n_agents} agents",
                color=agent_colors[n_agents],
                marker="o",
                capsize=3,
                linewidth=1.5,
                markersize=5,
            )

        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.set_xlabel(r"Prediction accuracy ($\rho$)")
        if col == 0:
            ax.set_ylabel("NPS advantage over LRTF\n(individual NPS units)")
        ax.set_title(MODE_LABELS[mode], fontsize=10)
        ax.grid(True, alpha=0.3)
        if col == 0:
            ax.legend(loc="best", fontsize=9, frameon=True)

    fig.suptitle("Figure S3.2: NPS-prioritization advantage over LRTF (diagnostic)",
                 y=1.02, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3_2_nps_advantage.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3.3: Organisation NPS vs ρ
# =============================================================================

def make_fig_s3_3(df: pd.DataFrame):
    """Samme som S3.1 men for organisations-niveau NPS (-100 til +100 skala)."""
    agg = aggregate(df, "organisation_nps")

    fig, axes = plt.subplots(3, 2, figsize=(10, 11), sharex=True)

    for row, n_agents in enumerate([5, 6, 7]):
        for col, mode in enumerate(SAMPLING_MODES):
            ax = axes[row, col]
            plot_metric_vs_rho(
                ax, agg, "organisation_nps", mode, n_agents,
                "Organisation NPS (%)",
                show_legend=(row == 0 and col == 0),
            )
            if row == 0:
                ax.set_title(MODE_LABELS[mode], fontsize=10)
            if col == 0:
                ax.text(-0.25, 0.5, f"Agents = {n_agents}",
                        transform=ax.transAxes, rotation=90,
                        va="center", fontsize=11, fontweight="bold")

    fig.suptitle("Figure S3.3: Organisation NPS vs prediction accuracy",
                 y=1.01, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3_3_org_nps.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3.4: Case resolution time vs ρ
# =============================================================================

def make_fig_s3_4(df: pd.DataFrame):
    """Gennemsnitlig case resolution time vs ρ — ændres den med prædiktion?"""
    agg = aggregate(df, "avg_case_resolution_time_days")

    fig, axes = plt.subplots(3, 2, figsize=(10, 11), sharex=True)

    for row, n_agents in enumerate([5, 6, 7]):
        for col, mode in enumerate(SAMPLING_MODES):
            ax = axes[row, col]
            plot_metric_vs_rho(
                ax, agg, "avg_case_resolution_time_days", mode, n_agents,
                "Avg. case resolution\ntime (days)",
                show_legend=(row == 0 and col == 0),
            )
            if row == 0:
                ax.set_title(MODE_LABELS[mode], fontsize=10)
            if col == 0:
                ax.text(-0.25, 0.5, f"Agents = {n_agents}",
                        transform=ax.transAxes, rotation=90,
                        va="center", fontsize=11, fontweight="bold")

    fig.suptitle("Figure S3.4: Case resolution time vs prediction accuracy",
                 y=1.01, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3_4_resolution_time.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3.5: Waiting time vs ρ
# =============================================================================

def make_fig_s3_5(df: pd.DataFrame):
    """Gennemsnitlig ventetid vs ρ — ændres trade-off med prædiktion?"""
    agg = aggregate(df, "avg_waiting_time_days")

    fig, axes = plt.subplots(3, 2, figsize=(10, 11), sharex=True)

    for row, n_agents in enumerate([5, 6, 7]):
        for col, mode in enumerate(SAMPLING_MODES):
            ax = axes[row, col]
            plot_metric_vs_rho(
                ax, agg, "avg_waiting_time_days", mode, n_agents,
                "Avg. waiting time\nin queue (days)",
                show_legend=(row == 0 and col == 0),
            )
            if row == 0:
                ax.set_title(MODE_LABELS[mode], fontsize=10)
            if col == 0:
                ax.text(-0.25, 0.5, f"Agents = {n_agents}",
                        transform=ax.transAxes, rotation=90,
                        va="center", fontsize=11, fontweight="bold")

    fig.suptitle("Figure S3.5: Waiting time vs prediction accuracy",
                 y=1.01, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3_5_waiting_time.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"FEJL: {CSV_PATH} findes ikke. Kør run_experiments.py først.")
        raise SystemExit(1)

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} runs from {CSV_PATH.name}")
    print(f"  ρ-niveauer:   {sorted(df['rho'].unique())}")
    print(f"  Modes:        {sorted(df['sampling_mode'].unique())}")
    print(f"  Discipliner:  {sorted(df['discipline'].unique())}")
    print(f"  Agents:       {sorted(df['n_agents'].unique())}")
    print()

    make_fig_s3_1(df)
    make_fig_s3_2(df)
    make_fig_s3_3(df)
    make_fig_s3_4(df)
    make_fig_s3_5(df)

    print("\nAll plots generated.")
