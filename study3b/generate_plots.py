"""
Generér Study 3b plots fra det tætte intercept × ρ grid.

Hovedfigur: heatmap af NPS − LRTF advantage over hele overfladen.
Sekundære figurer: linjeplots med ρ-snit og intercept-snit.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"


# =============================================================================
# Fig. S3b.1: Heatmap — NPS − LRTF advantage over (intercept × ρ)-fladen
# =============================================================================

def make_fig_s3b_1(df):
    """Heatmap af NPS − LRTF advantage (individual NPS) over intercept × ρ."""
    intercepts = sorted(df["nps_intercept"].unique(), reverse=True)
    rhos = sorted(df["rho"].unique())

    # Beregn NPS − LRTF for hvert (intercept, ρ) punkt
    grid = np.full((len(intercepts), len(rhos)), np.nan)

    for i, nps_int in enumerate(intercepts):
        for j, rho in enumerate(rhos):
            nps_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                          & (df["discipline"] == "NPS")]
            lrtf_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                           & (df["discipline"] == "LRTF")]
            if len(nps_sub) > 0 and len(lrtf_sub) > 0:
                grid[i, j] = nps_sub["avg_individual_nps"].mean() - lrtf_sub["avg_individual_nps"].mean()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Panel 1: individual NPS
    ax = axes[0]
    vmax = max(abs(np.nanmin(grid)), abs(np.nanmax(grid)))
    im = ax.imshow(grid, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                    origin="upper")
    ax.set_xticks(range(len(rhos)))
    ax.set_xticklabels([f"{r:.2f}" for r in rhos], fontsize=8)
    ax.set_yticks(range(len(intercepts)))
    ax.set_yticklabels([f"{v:.2f}" for v in intercepts], fontsize=8)
    ax.set_xlabel(r"Prediction accuracy ($\rho$)")
    ax.set_ylabel("NPS prediction intercept")
    ax.set_title("NPS − LRTF advantage\n(individual NPS units)")
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.ax.tick_params(labelsize=8)

    # Annotér celler med værdier
    for i in range(len(intercepts)):
        for j in range(len(rhos)):
            val = grid[i, j]
            if not np.isnan(val):
                color = "white" if abs(val) > vmax * 0.6 else "black"
                ax.text(j, i, f"{val:+.3f}", ha="center", va="center",
                         fontsize=6, color=color)

    # Panel 2: organisation NPS
    grid_org = np.full((len(intercepts), len(rhos)), np.nan)
    for i, nps_int in enumerate(intercepts):
        for j, rho in enumerate(rhos):
            nps_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                          & (df["discipline"] == "NPS")]
            lrtf_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                           & (df["discipline"] == "LRTF")]
            if len(nps_sub) > 0 and len(lrtf_sub) > 0:
                grid_org[i, j] = nps_sub["organisation_nps"].mean() - lrtf_sub["organisation_nps"].mean()

    ax = axes[1]
    vmax_org = max(abs(np.nanmin(grid_org)), abs(np.nanmax(grid_org)))
    im2 = ax.imshow(grid_org, aspect="auto", cmap="RdBu_r",
                      vmin=-vmax_org, vmax=vmax_org, origin="upper")
    ax.set_xticks(range(len(rhos)))
    ax.set_xticklabels([f"{r:.2f}" for r in rhos], fontsize=8)
    ax.set_yticks(range(len(intercepts)))
    ax.set_yticklabels([f"{v:.2f}" for v in intercepts], fontsize=8)
    ax.set_xlabel(r"Prediction accuracy ($\rho$)")
    ax.set_ylabel("NPS prediction intercept")
    ax.set_title("NPS − LRTF advantage\n(organisation NPS %)")
    cb2 = fig.colorbar(im2, ax=ax, shrink=0.8)
    cb2.ax.tick_params(labelsize=8)

    for i in range(len(intercepts)):
        for j in range(len(rhos)):
            val = grid_org[i, j]
            if not np.isnan(val):
                color = "white" if abs(val) > vmax_org * 0.6 else "black"
                ax.text(j, i, f"{val:+.1f}", ha="center", va="center",
                         fontsize=6, color=color)

    fig.suptitle("Figure S3b.1: When does NPS-prioritization diverge from LRTF?\n"
                 "(Red = NPS better, Blue = LRTF better)", fontsize=12, y=1.02)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3b_1_heatmap.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3b.2: Linjeplots — NPS − LRTF advantage for udvalgte intercepts
# =============================================================================

def make_fig_s3b_2(df):
    """NPS − LRTF advantage vs ρ, én linje pr. intercept (udvalgte niveauer)."""
    rhos = sorted(df["rho"].unique())
    # Vælg subset af intercepts for læsbar figur
    all_intercepts = sorted(df["nps_intercept"].unique(), reverse=True)
    highlight = [10.22, 9.0, 8.5, 8.0, 7.5, 7.0]
    intercepts = [v for v in all_intercepts if v in highlight] or all_intercepts

    colors = plt.cm.viridis(np.linspace(0, 0.9, len(intercepts)))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for metric_idx, (metric, ylabel) in enumerate([
        ("avg_individual_nps", "NPS − LRTF (individual NPS)"),
        ("organisation_nps", "NPS − LRTF (organisation NPS %)"),
    ]):
        ax = axes[metric_idx]
        for idx, nps_int in enumerate(intercepts):
            advantages = []
            for rho in rhos:
                nps_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                              & (df["discipline"] == "NPS")]
                lrtf_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                               & (df["discipline"] == "LRTF")]
                if len(nps_sub) > 0 and len(lrtf_sub) > 0:
                    advantages.append(nps_sub[metric].mean() - lrtf_sub[metric].mean())
                else:
                    advantages.append(np.nan)

            ax.plot(rhos, advantages, marker="o", label=f"int={nps_int:.2f}",
                     color=colors[idx], linewidth=1.5, markersize=4)

        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.set_xlabel(r"Prediction accuracy ($\rho$)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, frameon=True, loc="best")

    fig.suptitle("Figure S3b.2: NPS advantage over LRTF by intercept level",
                 y=1.02, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3b_2_advantage_lines.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3b.3: Intercept-snit — NPS vs LRTF vs FCFS for udvalgte ρ
# =============================================================================

def make_fig_s3b_3(df):
    """Individual NPS som funktion af intercept, for udvalgte ρ-niveauer."""
    intercepts = sorted(df["nps_intercept"].unique())
    rho_highlight = [0.0, 0.3, 0.5, 0.7, 0.85, 1.0]
    rhos = [r for r in sorted(df["rho"].unique()) if r in rho_highlight]

    # FCFS baseline (invariant — tag gennemsnit over alle reps)
    fcfs_data = df[df["discipline"] == "FCFS"]
    fcfs_mean = fcfs_data["avg_individual_nps"].mean()

    colors = plt.cm.plasma(np.linspace(0.1, 0.9, len(rhos)))

    fig, ax = plt.subplots(figsize=(8, 5))

    for idx, rho in enumerate(rhos):
        nps_means = []
        for nps_int in intercepts:
            nps_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                          & (df["discipline"] == "NPS")]
            nps_means.append(nps_sub["avg_individual_nps"].mean() if len(nps_sub) > 0 else np.nan)

        ax.plot(intercepts, nps_means, marker="o", label=f"NPS ρ={rho:.2f}",
                 color=colors[idx], linewidth=1.5, markersize=4)

    ax.axhline(fcfs_mean, color="#ff7f0e", linewidth=2, linestyle="--",
                label=f"FCFS baseline ({fcfs_mean:.3f})", alpha=0.7)

    ax.set_xlabel("NPS prediction intercept")
    ax.set_ylabel("Avg. individual NPS response")
    ax.set_title("Figure S3b.3: NPS discipline performance vs intercept level")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, frameon=True)

    out = RESULTS_DIR / "fig_s3b_3_nps_vs_intercept.pdf"
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
    print(f"  Intercepts: {sorted(df['nps_intercept'].unique())}")
    print(f"  ρ:          {sorted(df['rho'].unique())}")
    print(f"  Disciplines: {sorted(df['discipline'].unique())}")
    print()

    make_fig_s3b_1(df)
    make_fig_s3b_2(df)
    make_fig_s3b_3(df)

    print("\nAll plots generated.")
