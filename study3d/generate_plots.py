"""
Generate Study 3d plots.

Headline: segment-share comparison across disciplines (the new question
the user asked us to surface). Supplementary plots verify the rank-binning
mechanism and place the discipline in the broader (NPS, LRTF, SRTF, FCFS)
landscape.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"
EMPIRICAL_FILE = RESULTS_DIR / "empirical_nps_multinomial.json"

DISC_ORDER = ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]
DISC_COLORS = {
    "FCFS":       "#7f7f7f",
    "LRTF":       "#1f77b4",
    "SRTF":       "#2ca02c",
    "NPS":        "#ff7f0e",
    "NPS_BINNED": "#d62728",
}


# =============================================================================
# Fig. S3d.1 — segment proportions by discipline (headline plot)
# =============================================================================

def make_fig_s3d_1(df, empirical):
    """Stacked bar of detractor/passive/promoter %, plus orgNPS, by discipline.
    Aggregated across all ρ.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: stacked segment shares
    ax = axes[0]
    detr = []
    pas = []
    prom = []
    labels = []
    for disc in DISC_ORDER:
        sub = df[df["discipline"] == disc]
        detr.append(sub["percent_detractors"].mean())
        pas.append(sub["percent_passives"].mean())
        prom.append(sub["percent_promoters"].mean())
        labels.append(disc)

    x = np.arange(len(labels))
    detr = np.array(detr)
    pas = np.array(pas)
    prom = np.array(prom)

    ax.bar(x, detr, color="#d62728", label="Detractors (0–6)")
    ax.bar(x, pas,  bottom=detr, color="#7f7f7f", label="Passives (7–8)")
    ax.bar(x, prom, bottom=detr + pas, color="#2ca02c", label="Promoters (9–10)")

    if empirical is not None:
        ed = empirical["segment_proportions"]["detractors_0_to_6"]
        ep = empirical["segment_proportions"]["passives_7_to_8"]
        epr = empirical["segment_proportions"]["promoters_9_to_10"]
        ax.axhline(ed, color="black", linestyle="--", linewidth=0.7, alpha=0.5)
        ax.axhline(ed + ep, color="black", linestyle="--", linewidth=0.7, alpha=0.5)
        ax.text(len(labels) - 0.5, ed / 2,
                f"empirical\ndetractors\n{ed:.3f}", fontsize=7, ha="right",
                va="center", alpha=0.7)
        ax.text(len(labels) - 0.5, ed + ep / 2,
                f"empirical\npassives\n{ep:.3f}", fontsize=7, ha="right",
                va="center", alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Share of closed cases")
    ax.set_ylim(0, 1.05)
    ax.set_title("Realised NPS-segment shares\n(averaged over ρ and replications)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, fontsize=9)

    # Annotate values
    for i, (d, p, pr) in enumerate(zip(detr, pas, prom)):
        ax.text(i, d / 2, f"{d:.3f}", ha="center", va="center", fontsize=8, color="white")
        ax.text(i, d + p / 2, f"{p:.3f}", ha="center", va="center", fontsize=8, color="white")
        ax.text(i, d + p + pr / 2, f"{pr:.3f}", ha="center", va="center", fontsize=8, color="white")

    # Right: organisation NPS
    ax = axes[1]
    org = []
    for disc in DISC_ORDER:
        sub = df[df["discipline"] == disc]
        org.append(sub["organisation_nps"].mean())
    bars = ax.bar(DISC_ORDER, org, color=[DISC_COLORS[d] for d in DISC_ORDER],
                    edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Organisation NPS (% promoters − % detractors)")
    ax.set_title("Organisation-level NPS by discipline\n(averaged over ρ)")
    ax.grid(True, axis="y", alpha=0.3)
    for b, v in zip(bars, org):
        ax.text(b.get_x() + b.get_width() / 2, v,
                f"{v:+.2f}", ha="center", va="bottom", fontsize=9)

    fig.suptitle("Figure S3d.1: Customer-segment redistribution across disciplines",
                  y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3d_1_segment_proportions.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3d.2 — Verify the rank-binning mechanism
# =============================================================================

def make_fig_s3d_2(empirical):
    """Run a single mock generation to show: raw NPS_hat, binned NPS_hat,
    target multinomial. Three panels.
    """
    if empirical is None:
        print("Skipping fig_s3d_2 (no empirical multinomial available)")
        return

    from simulation import (
        generate_all_arrivals, apply_rank_binning, NPS_PRED_INTERCEPT,
    )

    rng_a = np.random.default_rng(101)
    rng_b = np.random.default_rng(102)
    rng_c = np.random.default_rng(103)
    cases = generate_all_arrivals(365, rng_a, rng_b, rng_c, 1.0,
                                    nps_intercept=NPS_PRED_INTERCEPT)
    raw = np.array([c.predicted_nps for c in cases])

    apply_rank_binning(cases, empirical["proportions"])
    binned = np.array([c.predicted_nps_binned for c in cases])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # Raw
    ax = axes[0]
    ax.hist(raw, bins=60, color="#1f77b4", alpha=0.7, edgecolor="black", linewidth=0.3)
    ax.axvline(7.5, color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel(r"raw $\hat{NPS}$ (Eq. 9)")
    ax.set_ylabel("Count")
    ax.set_title(f"Raw predicted NPS\nn={len(raw)}, "
                  f"mean={raw.mean():.3f}, std={raw.std():.4f}")
    ax.grid(True, alpha=0.3)

    # Binned
    ax = axes[1]
    counts = np.bincount(binned, minlength=11)
    bars = ax.bar(range(11), counts, color="#d62728", alpha=0.7,
                    edgecolor="black", linewidth=0.5)
    ax.set_xlabel(r"binned $\hat{NPS}$")
    ax.set_ylabel("Count")
    ax.set_xticks(range(11))
    ax.set_title(f"Rank-binned predicted NPS\nn={len(binned)}")
    ax.grid(True, axis="y", alpha=0.3)
    for b, v in zip(bars, counts):
        if v > 0:
            ax.text(b.get_x() + b.get_width() / 2, v,
                    f"{v}", ha="center", va="bottom", fontsize=7)

    # Target
    ax = axes[2]
    target = np.array(empirical["proportions"])
    actual = counts / counts.sum()
    width = 0.4
    x = np.arange(11)
    ax.bar(x - width / 2, target, width=width, color="#2ca02c", alpha=0.8,
            edgecolor="black", linewidth=0.4, label="empirical (target)")
    ax.bar(x + width / 2, actual, width=width, color="#d62728", alpha=0.8,
            edgecolor="black", linewidth=0.4, label="binned (achieved)")
    ax.set_xlabel("NPS bin")
    ax.set_ylabel("Proportion")
    ax.set_xticks(range(11))
    ax.set_title("Target vs. achieved bin proportions")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Figure S3d.2: Rank-binning sanity check",
                  y=1.02, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3d_2_binning_sanity.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3d.3 — Performance vs ρ across disciplines
# =============================================================================

def make_fig_s3d_3(df):
    """Individual NPS, organisation NPS, % promoters, % detractors over ρ
    by discipline.
    """
    rhos = sorted(df["rho"].unique())

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    plots = [
        (axes[0, 0], "avg_individual_nps", "Average individual NPS"),
        (axes[0, 1], "organisation_nps",   "Organisation NPS (% units)"),
        (axes[1, 0], "percent_promoters",  "% promoters"),
        (axes[1, 1], "percent_detractors", "% detractors"),
    ]

    for ax, col, title in plots:
        for disc in DISC_ORDER:
            means = []
            for rho in rhos:
                sub = df[(df["discipline"] == disc) & (df["rho"] == rho)]
                means.append(sub[col].mean() if len(sub) > 0 else np.nan)
            ax.plot(rhos, means, marker="o", linewidth=1.5, markersize=5,
                      color=DISC_COLORS[disc], label=disc)
        ax.set_xlabel(r"Prediction accuracy ($\rho$)")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle("Figure S3d.3: Performance metrics across ρ by discipline",
                  y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3d_3_metrics_vs_rho.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3d.4 — NPS_BINNED vs LRTF advantage over ρ (parallel to 3b/3c)
# =============================================================================

def make_fig_s3d_4(df):
    rhos = sorted(df["rho"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for ax, metric, ylabel in [
        (axes[0], "avg_individual_nps", "advantage in individual NPS"),
        (axes[1], "organisation_nps",   "advantage in organisation NPS (pp)"),
    ]:
        for ref_disc in ["FCFS", "LRTF", "NPS"]:
            advs = []
            for rho in rhos:
                target = df[(df["discipline"] == "NPS_BINNED") & (df["rho"] == rho)][metric].mean()
                ref = df[(df["discipline"] == ref_disc) & (df["rho"] == rho)][metric].mean()
                advs.append(target - ref)
            ax.plot(rhos, advs, marker="o", linewidth=1.5, markersize=5,
                      color=DISC_COLORS[ref_disc],
                      label=f"NPS_BINNED − {ref_disc}")

        ax.axhline(0, color="black", linewidth=0.7, linestyle=":", alpha=0.6)
        ax.set_xlabel(r"Prediction accuracy ($\rho$)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

    fig.suptitle("Figure S3d.4: NPS_BINNED advantage over reference disciplines",
                  y=1.02, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3d_4_advantage.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} does not exist.")
        raise SystemExit(1)

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} runs")
    print(f"  disciplines: {sorted(df['discipline'].unique())}")
    print(f"  ρ:           {sorted(df['rho'].unique())}")
    print()

    empirical = None
    if EMPIRICAL_FILE.exists():
        with open(EMPIRICAL_FILE) as f:
            empirical = json.load(f)

    make_fig_s3d_1(df, empirical)
    make_fig_s3d_2(empirical)
    make_fig_s3d_3(df)
    make_fig_s3d_4(df)

    print("\nAll plots generated.")
