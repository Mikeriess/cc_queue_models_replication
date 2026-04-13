"""
Plot der illustrerer indsigt 1 (skarp transition) + indsigt 2 (plateau).

Viser NPS − LRTF advantage som funktion af intercept, med ρ som parameter.
Den visuelle effekt: en skarp step ved ~8.75-9.0, efterfulgt af et fuldstændigt
fladt plateau hele vejen ned til intercept 6.5.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"


def main():
    df = pd.read_csv(CSV_PATH)

    intercepts = sorted(df["nps_intercept"].unique())  # stigende: 6.5 → 10.22
    rhos = sorted(df["rho"].unique())

    # Vis udvalgte ρ-niveauer for klarhed
    highlight_rhos = [0.0, 0.3, 0.5, 0.7, 0.85, 1.0]
    colors = plt.cm.plasma(np.linspace(0.1, 0.85, len(highlight_rhos)))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # =========================================================================
    # Panel 1: Individual NPS advantage
    # =========================================================================
    ax = axes[0]
    for idx, rho in enumerate(highlight_rhos):
        advantages = []
        cis = []
        for nps_int in intercepts:
            nps_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                          & (df["discipline"] == "NPS")]
            lrtf_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                           & (df["discipline"] == "LRTF")]
            adv = nps_sub["avg_individual_nps"].mean() - lrtf_sub["avg_individual_nps"].mean()
            se = np.sqrt(
                nps_sub["avg_individual_nps"].std()**2 / len(nps_sub)
                + lrtf_sub["avg_individual_nps"].std()**2 / len(lrtf_sub)
            )
            advantages.append(adv)
            cis.append(1.96 * se)

        ax.errorbar(intercepts, advantages, yerr=cis,
                     label=f"ρ = {rho:.2f}", color=colors[idx],
                     marker="o", capsize=2, linewidth=1.8, markersize=5)

    # Annotér transition-zonen
    ax.axvspan(9.0, 9.5, alpha=0.15, color="red", label="_nolegend_")
    ax.axvline(9.0, color="red", linestyle=":", linewidth=1, alpha=0.6)
    ax.axvline(9.5, color="red", linestyle=":", linewidth=1, alpha=0.6)
    ax.text(9.25, ax.get_ylim()[1] * 0.92, "Sharp\ntransition",
             ha="center", va="top", fontsize=9, color="darkred",
             fontweight="bold")

    # Annotér plateau
    ax.axvspan(6.3, 8.75, alpha=0.08, color="green")
    ax.text(7.5, ax.get_ylim()[1] * 0.92, "Plateau (identical values)",
             ha="center", va="top", fontsize=9, color="darkgreen",
             fontweight="bold")

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("NPS prediction intercept")
    ax.set_ylabel("NPS − LRTF advantage\n(individual NPS units)")
    ax.set_title("Individual NPS")
    ax.invert_xaxis()  # høj intercept til venstre (baseline), lav til højre
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, frameon=True, loc="lower left")

    # =========================================================================
    # Panel 2: Organisation NPS advantage
    # =========================================================================
    ax = axes[1]
    for idx, rho in enumerate(highlight_rhos):
        advantages = []
        cis = []
        for nps_int in intercepts:
            nps_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                          & (df["discipline"] == "NPS")]
            lrtf_sub = df[(df["nps_intercept"] == nps_int) & (df["rho"] == rho)
                           & (df["discipline"] == "LRTF")]
            adv = nps_sub["organisation_nps"].mean() - lrtf_sub["organisation_nps"].mean()
            se = np.sqrt(
                nps_sub["organisation_nps"].std()**2 / len(nps_sub)
                + lrtf_sub["organisation_nps"].std()**2 / len(lrtf_sub)
            )
            advantages.append(adv)
            cis.append(1.96 * se)

        ax.errorbar(intercepts, advantages, yerr=cis,
                     label=f"ρ = {rho:.2f}", color=colors[idx],
                     marker="o", capsize=2, linewidth=1.8, markersize=5)

    ax.axvspan(9.0, 9.5, alpha=0.15, color="red")
    ax.axvline(9.0, color="red", linestyle=":", linewidth=1, alpha=0.6)
    ax.axvline(9.5, color="red", linestyle=":", linewidth=1, alpha=0.6)
    ax.text(9.25, ax.get_ylim()[1] * 0.92, "Sharp\ntransition",
             ha="center", va="top", fontsize=9, color="darkred",
             fontweight="bold")

    ax.axvspan(6.3, 8.75, alpha=0.08, color="green")
    ax.text(7.5, ax.get_ylim()[1] * 0.92, "Plateau (identical values)",
             ha="center", va="top", fontsize=9, color="darkgreen",
             fontweight="bold")

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("NPS prediction intercept")
    ax.set_ylabel("NPS − LRTF advantage\n(organisation NPS %)")
    ax.set_title("Organisation NPS")
    ax.invert_xaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, frameon=True, loc="lower left")

    fig.suptitle(
        "Figure S3b.4: Sharp transition + plateau effect\n"
        "The NPS-prioritization benefit activates binarily when NPS_hat-distribution "
        "crosses the 7.5 midpoint",
        fontsize=11, y=1.01
    )
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3b_4_transition_plateau.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


if __name__ == "__main__":
    main()
