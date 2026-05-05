"""
Generate Study 3e plots.

Six figures:
    1. Org NPS vs f for NPS_BINNED at three ρ levels (headline).
    2. Segment shares vs f at ρ = 1.0.
    3. NPS_BINNED − reference advantage vs f, one curve per ρ.
    4. The nine target multinomials, faceted (design space).
    5. Top-priority class size and bulk-class size as functions of f.
    6. Operational metrics vs f at ρ = 1.0 (waiting, resolution, closed, queue).
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
RHO_COLORS = {0.0: "#7f7f7f", 0.5: "#ff7f0e", 1.0: "#d62728"}


def _ref_mean(df, disc, rho, col):
    sub = df[(df["discipline"] == disc) & (df["rho"] == rho)]
    return sub[col].mean() if len(sub) > 0 else np.nan


def _binned_curve(df, rho, col):
    sub = df[(df["discipline"] == "NPS_BINNED") & (df["rho"] == rho)]
    if len(sub) == 0:
        return [], []
    grouped = sub.groupby("target_f")[col].mean().reset_index()
    grouped = grouped.sort_values("target_f")
    return grouped["target_f"].tolist(), grouped[col].tolist()


# =============================================================================
# Fig. S3e.1 — Org NPS vs f (headline)
# =============================================================================

def make_fig_s3e_1(df):
    rhos = sorted(df["rho"].unique())

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    # Reference horizontal lines (averaged across ρ for FCFS/LRTF/SRTF
    # since they barely depend on ρ; show one per discipline).
    for disc in ["FCFS", "LRTF", "SRTF"]:
        m = df[df["discipline"] == disc]["organisation_nps"].mean()
        ax.axhline(m, color=DISC_COLORS[disc], linestyle="--",
                    linewidth=1.0, alpha=0.55,
                    label=f"{disc} (avg over ρ): {m:+.2f}")

    # NPS_BINNED curves per ρ
    for rho in rhos:
        fs, ys = _binned_curve(df, rho, "organisation_nps")
        ax.plot(fs, ys, marker="o", linewidth=1.7, markersize=6,
                  color=RHO_COLORS.get(rho, "#000"),
                  label=f"NPS_BINNED, ρ = {rho}")
        if fs:
            i_max = int(np.argmax(ys))
            ax.scatter([fs[i_max]], [ys[i_max]], s=140,
                        facecolors="none", edgecolors="black", linewidths=1.5,
                        zorder=5)
            ax.annotate(f"argmax\nf={fs[i_max]:.3f}",
                          xy=(fs[i_max], ys[i_max]),
                          xytext=(8, 6), textcoords="offset points",
                          fontsize=8, alpha=0.7)

    # Empirical baseline (Study 3d)
    ax.axvline(0.145, color="black", linestyle=":", linewidth=0.9, alpha=0.5)
    ax.text(0.147, ax.get_ylim()[0] + 0.5, "empirical f=0.145",
              fontsize=8, alpha=0.6, rotation=90, va="bottom")

    ax.set_xlabel(r"$f$ = mass at bins {7, 8} (top priority class)")
    ax.set_ylabel("Organisation NPS (% promoters − % detractors)")
    ax.set_title("Figure S3e.1: Organisation NPS vs target multinomial shape\n"
                  "(NPS_BINNED with mode at 7.5, uniform-tail family)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)

    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3e_1_org_nps_vs_f.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3e.2 — Segment shares vs f at ρ = 1.0
# =============================================================================

def make_fig_s3e_2(df):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    rho = 1.0

    metrics = [
        ("percent_detractors", "% detractors", "#d62728"),
        ("percent_passives",    "% passives",   "#7f7f7f"),
        ("percent_promoters",   "% promoters",  "#2ca02c"),
    ]

    for ax, (col, title, color) in zip(axes, metrics):
        # Reference horizontal lines
        for disc in ["FCFS", "LRTF", "SRTF", "NPS"]:
            m = _ref_mean(df, disc, rho, col)
            ax.axhline(m, color=DISC_COLORS[disc], linestyle="--",
                        linewidth=0.8, alpha=0.6,
                        label=f"{disc}: {m:.3f}")

        fs, ys = _binned_curve(df, rho, col)
        ax.plot(fs, ys, marker="o", linewidth=1.7, markersize=6,
                  color=color, label="NPS_BINNED")

        ax.axvline(0.145, color="black", linestyle=":", linewidth=0.7, alpha=0.4)

        ax.set_xlabel(r"$f$ = mass at bins {7,8}")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")

    fig.suptitle(f"Figure S3e.2: Realised NPS-segment shares vs $f$ "
                  f"(ρ = {rho})", y=1.02, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3e_2_segment_shares_vs_f.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3e.3 — NPS_BINNED − reference advantage vs f
# =============================================================================

def make_fig_s3e_3(df):
    rhos = sorted(df["rho"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, metric, ylabel in [
        (axes[0], "avg_individual_nps", "NPS_BINNED − LRTF (individual NPS)"),
        (axes[1], "organisation_nps",    "NPS_BINNED − LRTF (organisation NPS, pp)"),
    ]:
        for rho in rhos:
            ref = _ref_mean(df, "LRTF", rho, metric)
            fs, ys = _binned_curve(df, rho, metric)
            advs = [y - ref for y in ys]
            ax.plot(fs, advs, marker="o", linewidth=1.7, markersize=6,
                      color=RHO_COLORS.get(rho, "#000"),
                      label=f"ρ = {rho}")

        ax.axhline(0, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
        ax.axvline(0.145, color="black", linestyle=":", linewidth=0.7, alpha=0.4)
        ax.set_xlabel(r"$f$ = mass at bins {7,8}")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

    fig.suptitle("Figure S3e.3: NPS_BINNED advantage over LRTF vs target shape",
                  y=1.02, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3e_3_advantage_vs_f.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3e.4 — Visualise the design space (target multinomials)
# =============================================================================

def make_fig_s3e_4(df, empirical):
    from simulation import build_target

    fs = sorted([f for f in df["target_f"].dropna().unique()])
    if not fs:
        return

    n = len(fs)
    cols = 3
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.6 * cols, 2.8 * rows),
                              sharex=True, sharey=True)
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for idx, f in enumerate(fs):
        ax = axes_flat[idx]
        target = build_target(f)
        bars = ax.bar(range(11), target, color="#1f77b4", edgecolor="black",
                        linewidth=0.4)
        # Highlight bins 7+8
        bars[7].set_color("#d62728")
        bars[8].set_color("#d62728")
        ax.set_xticks(range(11))
        ax.set_title(f"f = {f:.3f}", fontsize=9)
        ax.set_ylim(0, 1.0)
        ax.grid(True, axis="y", alpha=0.3)

    # Optional empirical overlay on the f≈0.145 panel as a reference
    if empirical is not None:
        for idx, f in enumerate(fs):
            if abs(f - 0.145) < 0.001:
                ax = axes_flat[idx]
                emp = np.array(empirical["proportions"])
                ax.plot(range(11), emp, marker="x", linestyle="--",
                          color="black", markersize=6, linewidth=0.9,
                          label="empirical")
                ax.legend(fontsize=7, loc="upper left")

    # Hide unused axes
    for j in range(n, len(axes_flat)):
        axes_flat[j].axis("off")

    fig.suptitle("Figure S3e.4: Target multinomial family (mode at 7.5, uniform tail)",
                  y=1.0, fontsize=12)
    fig.supxlabel("NPS bin", fontsize=10)
    fig.supylabel("Probability", fontsize=10)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3e_4_target_distributions.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3e.5 — Class sizes vs f
# =============================================================================

def make_fig_s3e_5(df):
    fig, ax = plt.subplots(1, 1, figsize=(10, 5.5))

    sub = df[df["discipline"] == "NPS_BINNED"].copy()
    sub = sub.dropna(subset=["target_f"])
    grouped = sub.groupby("target_f").agg(
        top_mean=("top_class_size", "mean"),
        top_std=("top_class_size", "std"),
        bulk_mean=("bulk_class_size", "mean"),
        bulk_std=("bulk_class_size", "std"),
        cases_mean=("total_cases_arrived", "mean"),
    ).reset_index().sort_values("target_f")

    ax.errorbar(grouped["target_f"], grouped["top_mean"], yerr=grouped["top_std"],
                  marker="o", linewidth=1.5, markersize=6,
                  color="#d62728", capsize=3, label="top class size (priority 0.5)")
    ax.errorbar(grouped["target_f"], grouped["bulk_mean"], yerr=grouped["bulk_std"],
                  marker="s", linewidth=1.5, markersize=5,
                  color="#1f77b4", capsize=3, label="bulk (largest tied) class size")
    ax.plot(grouped["target_f"], grouped["cases_mean"],
              linestyle="--", color="black", linewidth=0.8, alpha=0.6,
              label="total cases arrived")

    ax.set_xlabel(r"$f$ = mass at bins {7, 8}")
    ax.set_ylabel("Number of cases")
    ax.set_title("Figure S3e.5: Priority-class sizes as functions of target shape\n"
                  "(NPS_BINNED, averaged over ρ and replications)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3e_5_class_sizes_vs_f.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S3e.6 — Operational metrics vs f at ρ = 1.0
# =============================================================================

def make_fig_s3e_6(df):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    rho = 1.0

    plots = [
        (axes[0, 0], "avg_waiting_time_days",        "Avg waiting time (days)"),
        (axes[0, 1], "avg_case_resolution_time_days", "Avg resolution time (days)"),
        (axes[1, 0], "percent_cases_closed",          "% cases closed"),
        (axes[1, 1], "avg_queue_length",              "Avg queue length"),
    ]

    for ax, col, title in plots:
        for disc in ["FCFS", "LRTF", "SRTF", "NPS"]:
            m = _ref_mean(df, disc, rho, col)
            ax.axhline(m, color=DISC_COLORS[disc], linestyle="--",
                        linewidth=0.8, alpha=0.55, label=f"{disc}: {m:.2f}")

        fs, ys = _binned_curve(df, rho, col)
        ax.plot(fs, ys, marker="o", linewidth=1.7, markersize=6,
                  color=DISC_COLORS["NPS_BINNED"], label="NPS_BINNED")
        ax.axvline(0.145, color="black", linestyle=":", linewidth=0.7, alpha=0.4)

        ax.set_xlabel(r"$f$ = mass at bins {7,8}")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")

    fig.suptitle(f"Figure S3e.6: Operational metrics vs $f$ (ρ = {rho})",
                  y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s3e_6_operational_vs_f.pdf"
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
    print(f"  target_f:    {sorted(df['target_f'].dropna().unique())}")
    print()

    empirical = None
    if EMPIRICAL_FILE.exists():
        with open(EMPIRICAL_FILE) as f:
            empirical = json.load(f)

    make_fig_s3e_1(df)
    make_fig_s3e_2(df)
    make_fig_s3e_3(df)
    make_fig_s3e_4(df, empirical)
    make_fig_s3e_5(df)
    make_fig_s3e_6(df)

    print("\nAll plots generated.")
