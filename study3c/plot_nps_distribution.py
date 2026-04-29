"""
Plot two density visualisations:
    1. Predicted NPS (NPS_hat from Eq. 9) across intercept × topic_aware.
       This is what the priority discipline sees at queue entry.
    2. Actual NPS (from Eq. 8) under different disciplines.
       This is the realised customer response after the case closes.

The two distributions are on very different scales — predicted NPS is
extremely narrow (std ≈ 0.04–0.08) and lives in a 0.5-unit band; actual NPS
is a discrete 0–10 integer sampled from a clipped gamma.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from simulation import (
    generate_all_arrivals,
    simulate_timeline,
    derive_seeds,
    NPS_PRED_INTERCEPT,
)

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"

D_END = 365
RHO = 1.0


# =============================================================================
# Predicted NPS distribution (Eq. 9)
# =============================================================================

def gather_predicted_nps(intercept: float, topic_aware: bool, seed: int = 42):
    rng_arrivals    = np.random.default_rng(seed + 1)
    rng_actual      = np.random.default_rng(seed + 2)
    rng_pred_noise  = np.random.default_rng(seed + 3)
    cases = generate_all_arrivals(
        D_END, rng_arrivals, rng_actual, rng_pred_noise, RHO,
        nps_intercept=intercept, topic_aware=topic_aware,
    )
    return np.array([c.predicted_nps for c in cases])


def make_predicted_density_plot():
    intercept_levels = [10.22, 9.50, 9.00, 8.75, 8.50, 8.00]
    topic_aware_levels = [False, True]

    fig, axes = plt.subplots(len(topic_aware_levels), len(intercept_levels),
                              figsize=(15, 5.5), sharex=True, sharey=True)

    for row, topic_aware in enumerate(topic_aware_levels):
        for col, intercept in enumerate(intercept_levels):
            ax = axes[row, col]
            nps_hat = gather_predicted_nps(intercept, topic_aware)

            color = "#d62728" if topic_aware else "#1f77b4"
            ax.hist(nps_hat, bins=50, density=True, color=color,
                      alpha=0.7, edgecolor="black", linewidth=0.3)
            ax.axvline(7.5, color="black", linestyle="--", linewidth=1.0)

            ax.text(0.03, 0.95,
                      f"intercept = {intercept:.2f}\n"
                      f"mean = {nps_hat.mean():.2f}\n"
                      f"std  = {nps_hat.std():.3f}\n"
                      f"frac<7.5 = {np.mean(nps_hat < 7.5):.3f}",
                      transform=ax.transAxes, fontsize=7.5, va="top",
                      bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85))

            if row == 0:
                ax.set_title(f"intercept = {intercept:.2f}", fontsize=10)
            if col == 0:
                ax.set_ylabel(f"topic_aware = {topic_aware}\n\nDensity", fontsize=9)
            if row == 1:
                ax.set_xlabel(r"$\hat{NPS}$", fontsize=9)

            ax.set_xlim(5.5, 10.0)
            ax.tick_params(axis="both", labelsize=7)
            ax.grid(True, alpha=0.3)

    fig.suptitle("Predicted NPS (Eq. 9) — distribution across intercept × topic_aware\n"
                  "(ρ = 1.0, 365 days, single replication ~1100 cases)",
                  fontsize=11, y=1.00)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3c_nps_density.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


# =============================================================================
# Actual NPS distribution (Eq. 8)
# =============================================================================

def gather_actual_nps(discipline: str, n_agents: int = 6, replication: int = 1):
    """Run one simulation and return the integer NPS responses of closed cases."""
    seeds = derive_seeds(replication, rho_idx=0)
    metrics = simulate_timeline(
        discipline=discipline,
        n_agents=n_agents,
        sla_hours=None,
        rho=RHO,
        sampling_mode="hard",
        d_end=D_END,
        seeds=seeds,
        nps_intercept=NPS_PRED_INTERCEPT,
        topic_aware=False,
    )
    return np.array(metrics.nps_responses, dtype=int)


def make_actual_density_plot():
    """Discrete histogram of actual NPS responses, by discipline."""
    disciplines = ["FCFS", "LRTF", "SRTF", "NPS"]
    colors = {"FCFS": "#7f7f7f", "LRTF": "#1f77b4", "SRTF": "#2ca02c", "NPS": "#d62728"}

    fig, axes = plt.subplots(1, len(disciplines), figsize=(16, 4.5),
                              sharey=True)

    bins = np.arange(-0.5, 11.5, 1.0)
    centres = np.arange(0, 11)

    for ax, disc in zip(axes, disciplines):
        nps = gather_actual_nps(disc)
        promoters  = np.mean(nps >= 9)
        passives   = np.mean((nps >= 7) & (nps <= 8))
        detractors = np.mean(nps <= 6)
        org_nps = (promoters - detractors) * 100

        counts, _ = np.histogram(nps, bins=bins)
        density = counts / counts.sum()
        ax.bar(centres, density, width=0.85, color=colors[disc],
                edgecolor="black", linewidth=0.4, alpha=0.85)

        # NPS-segment band shading
        ax.axvspan(-0.5, 6.5, color="red",   alpha=0.07, zorder=0)
        ax.axvspan(6.5, 8.5,  color="grey",  alpha=0.10, zorder=0)
        ax.axvspan(8.5, 10.5, color="green", alpha=0.07, zorder=0)

        ax.set_title(f"{disc}", fontsize=11)
        ax.set_xlabel("Actual NPS (integer 0–10)")
        if disc == disciplines[0]:
            ax.set_ylabel("Probability mass")
        ax.set_xticks(range(0, 11))
        ax.set_xlim(-0.5, 10.5)
        ax.grid(True, axis="y", alpha=0.3)

        ax.text(0.03, 0.97,
                  f"n = {len(nps)}\n"
                  f"mean = {nps.mean():.2f}\n"
                  f"detr  = {detractors:.1%}\n"
                  f"pass  = {passives:.1%}\n"
                  f"prom  = {promoters:.1%}\n"
                  f"orgNPS = {org_nps:+.1f}",
                  transform=ax.transAxes, fontsize=8, va="top",
                  bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.9))

    fig.suptitle("Actual NPS (Eq. 8) — distribution of realised responses by discipline\n"
                  "(intercept = 10.22, topic_aware = False, 6 agents, ρ = 1.0, "
                  "single replication, 365 days)",
                  fontsize=11, y=1.02)
    fig.tight_layout()

    out = RESULTS_DIR / "fig_s3c_actual_nps_density.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


# =============================================================================
# Side-by-side comparison: predicted vs. actual on the same axis
# =============================================================================

def make_combined_comparison():
    """Overlay predicted NPS density and actual NPS pmf on a shared axis."""
    fig, ax = plt.subplots(figsize=(10, 5))

    pred = gather_predicted_nps(NPS_PRED_INTERCEPT, topic_aware=False)
    actual = gather_actual_nps("NPS")

    ax.hist(pred, bins=80, density=True, color="#1f77b4", alpha=0.55,
              edgecolor="black", linewidth=0.3,
              label=fr"Predicted NPS ($\hat{{NPS}}$, Eq. 9), n={len(pred)}")

    bins = np.arange(-0.5, 11.5, 1.0)
    centres = np.arange(0, 11)
    counts, _ = np.histogram(actual, bins=bins)
    density = counts / counts.sum()
    ax.bar(centres, density, width=0.85, color="#d62728", alpha=0.55,
             edgecolor="black", linewidth=0.4,
             label=f"Actual NPS (Eq. 8, integer), n={len(actual)}")

    ax.axvline(7.5, color="black", linestyle="--", linewidth=1.0,
                label="midpoint = 7.5")
    ax.set_xlabel("NPS value")
    ax.set_ylabel("Density / probability mass")
    ax.set_xlim(-0.5, 10.5)
    ax.set_xticks(range(0, 11))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Predicted vs. actual NPS — same scale\n"
                  "(NPS discipline, intercept = 10.22, topic_blind, 6 agents, ρ = 1.0)")

    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3c_nps_predicted_vs_actual.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    make_predicted_density_plot()
    make_actual_density_plot()
    make_combined_comparison()
