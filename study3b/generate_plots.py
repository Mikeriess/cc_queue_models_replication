"""
Generér Study 3b plots.

Hovedfigur (Fig. S3b.1):
    Heatmap eller linje-plot: NPS − LRTF advantage som funktion af
    intercept (x-akse) × ρ (separate linjer), agents = 6.

Sekundære figurer:
    Fig. S3b.2: Individual NPS pr. disciplin for hvert intercept-niveau
    Fig. S3b.3: Organisation NPS pr. disciplin × intercept × ρ
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"

DISCIPLINES = ["FCFS", "LRTF", "NPS"]
COLORS = {"NPS": "#d62728", "LRTF": "#2ca02c", "FCFS": "#ff7f0e"}
RHO_COLORS = {0.0: "#cccccc", 0.22: "#999999", 0.50: "#1f77b4",
              0.85: "#ff7f0e", 1.00: "#d62728"}


def aggregate(df, metric, groupby):
    grp = df.groupby(list(groupby))[metric]
    agg = grp.agg(["mean", "std", "count"]).reset_index()
    agg["sem"] = agg["std"] / np.sqrt(agg["count"])
    agg["ci95"] = 1.96 * agg["sem"]
    return agg


# =============================================================================
# Fig. S3b.1: NPS − LRTF advantage vs intercept, linjer for ρ
# =============================================================================

def make_fig_s3b_1(df):
    """Hovedresultat: NPS-LRTF advantage som funktion af intercept og ρ."""
    intercepts = sorted(df["nps_intercept"].unique())
    rhos = sorted(df["rho"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel 1: Individual NPS advantage
    ax = axes[0]
    for rho in rhos:
        advantages = []
        ci95s = []
        for nps_int in intercepts:
            sub = df[(df["rho"] == rho) & (df["nps_intercept"] == nps_int)]
            nps_vals = sub[sub["discipline"] == "NPS"]["avg_individual_nps"]
            lrtf_vals = sub[sub["discipline"] == "LRTF"]["avg_individual_nps"]
            adv = nps_vals.mean() - lrtf_vals.mean()
            # Konservativ SE (antager uafhængighed)
            se = np.sqrt(nps_vals.std()**2/len(nps_vals) + lrtf_vals.std()**2/len(lrtf_vals))
            advantages.append(adv)
            ci95s.append(1.96 * se)

        ax.errorbar(intercepts, advantages, yerr=ci95s,
                     label=f"ρ = {rho:.2f}", color=RHO_COLORS[rho],
                     marker="o", capsize=3, linewidth=1.5)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("NPS prediction intercept")
    ax.set_ylabel("NPS − LRTF advantage\n(individual NPS units)")
    ax.set_title("Individual NPS")
    ax.legend(fontsize=9, frameon=True)
    ax.grid(True, alpha=0.3)

    # Panel 2: Organisation NPS advantage
    ax = axes[1]
    for rho in rhos:
        advantages = []
        ci95s = []
        for nps_int in intercepts:
            sub = df[(df["rho"] == rho) & (df["nps_intercept"] == nps_int)]
            nps_vals = sub[sub["discipline"] == "NPS"]["organisation_nps"]
            lrtf_vals = sub[sub["discipline"] == "LRTF"]["organisation_nps"]
            adv = nps_vals.mean() - lrtf_vals.mean()
            se = np.sqrt(nps_vals.std()**2/len(nps_vals) + lrtf_vals.std()**2/len(lrtf_vals))
            advantages.append(adv)
            ci95s.append(1.96 * se)

        ax.errorbar(intercepts, advantages, yerr=ci95s,
                     label=f"ρ = {rho:.2f}", color=RHO_COLORS[rho],
                     marker="o", capsize=3, linewidth=1.5)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("NPS prediction intercept")
    ax.set_ylabel("NPS − LRTF advantage\n(organisation NPS %)")
    ax.set_title("Organisation NPS")
    ax.legend(fontsize=9, frameon=True)
    ax.grid(True, alpha=0.3)

    fig.suptitle("Figure S3b.1: When does NPS-prioritization diverge from LRTF?",
                 y=1.02, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3b_1_nps_advantage_vs_intercept.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3b.2: Individual NPS per disciplin for hvert intercept
# =============================================================================

def make_fig_s3b_2(df):
    """Individual NPS vs ρ, ét panel pr. intercept, 3 disciplin-linjer."""
    intercepts = sorted(df["nps_intercept"].unique())
    rhos = sorted(df["rho"].unique())

    fig, axes = plt.subplots(1, len(intercepts), figsize=(4 * len(intercepts), 4),
                              sharey=True)

    for col, nps_int in enumerate(intercepts):
        ax = axes[col]
        sub = df[df["nps_intercept"] == nps_int]
        agg = aggregate(sub, "avg_individual_nps",
                         ("rho", "discipline"))

        for disc in DISCIPLINES:
            disc_data = agg[agg["discipline"] == disc].sort_values("rho")
            ax.errorbar(disc_data["rho"], disc_data["mean"],
                         yerr=disc_data["ci95"],
                         label=disc, color=COLORS[disc],
                         marker="o", capsize=3, linewidth=1.5)

        ax.set_title(f"Intercept = {nps_int}", fontsize=10)
        ax.set_xlabel(r"$\rho$")
        if col == 0:
            ax.set_ylabel("Avg. individual NPS")
        ax.grid(True, alpha=0.3)
        if col == 0:
            ax.legend(fontsize=9, frameon=True)

    fig.suptitle("Figure S3b.2: Individual NPS by discipline and intercept level",
                 y=1.02, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3b_2_nps_by_intercept.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3b.3: Organisation NPS — same layout
# =============================================================================

def make_fig_s3b_3(df):
    """Organisation NPS vs ρ, ét panel pr. intercept."""
    intercepts = sorted(df["nps_intercept"].unique())

    fig, axes = plt.subplots(1, len(intercepts), figsize=(4 * len(intercepts), 4),
                              sharey=True)

    for col, nps_int in enumerate(intercepts):
        ax = axes[col]
        sub = df[df["nps_intercept"] == nps_int]
        agg = aggregate(sub, "organisation_nps",
                         ("rho", "discipline"))

        for disc in DISCIPLINES:
            disc_data = agg[agg["discipline"] == disc].sort_values("rho")
            ax.errorbar(disc_data["rho"], disc_data["mean"],
                         yerr=disc_data["ci95"],
                         label=disc, color=COLORS[disc],
                         marker="o", capsize=3, linewidth=1.5)

        ax.set_title(f"Intercept = {nps_int}", fontsize=10)
        ax.set_xlabel(r"$\rho$")
        if col == 0:
            ax.set_ylabel("Organisation NPS (%)")
        ax.grid(True, alpha=0.3)
        if col == 0:
            ax.legend(fontsize=9, frameon=True)

    fig.suptitle("Figure S3b.3: Organisation NPS by discipline and intercept level",
                 y=1.02, fontsize=12)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3b_3_org_nps_by_intercept.pdf"
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
    print(f"Loaded {len(df)} runs")
    print(f"  Intercepts: {sorted(df['nps_intercept'].unique())}")
    print(f"  ρ:          {sorted(df['rho'].unique())}")
    print()

    make_fig_s3b_1(df)
    make_fig_s3b_2(df)
    make_fig_s3b_3(df)

    print("\nAll plots generated.")
