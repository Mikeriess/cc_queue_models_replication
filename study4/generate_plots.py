"""
Generate Study 4 plots.

Seven figures:
    1. Org NPS vs A, 2x2 panels by (P, ρ), one line per discipline (HEADLINE).
    2. Individual NPS vs A, same layout.
    3. (SRTF − LRTF) and (NPS_BINNED − LRTF) advantages vs A.
    4. (NPS_BINNED − SRTF) vs A — does NPS_BINNED ever pull ahead under load variation?
    5. Daily queue-length traces, rows=A, columns=disciplines, P=28d, ρ=1.
    6. Operational metrics vs A (waiting, resolution, %closed, peak queue).
    7. Daily arrivals trace, one panel per A, P=28d, demonstrates input modulation.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"
DAILY_Q_PATH = RESULTS_DIR / "daily_queue_lengths.csv.gz"
DAILY_A_PATH = RESULTS_DIR / "daily_arrivals.csv.gz"

DISC_ORDER = ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]
DISC_COLORS = {
    "FCFS":       "#7f7f7f",
    "LRTF":       "#1f77b4",
    "SRTF":       "#2ca02c",
    "NPS":        "#ff7f0e",
    "NPS_BINNED": "#d62728",
}


# =============================================================================
# Helpers
# =============================================================================

def _curve(df, discipline, rho, period, col):
    sub = df[(df["discipline"] == discipline)
             & (df["rho"] == rho)
             & (df["period_days"].round(1) == round(period, 1))]
    if len(sub) == 0:
        return [], [], []
    grouped = sub.groupby("amplitude")[col].agg(["mean", "std", "count"]).reset_index()
    grouped = grouped.sort_values("amplitude")
    se = grouped["std"] / np.sqrt(grouped["count"])
    return (grouped["amplitude"].tolist(),
            grouped["mean"].tolist(),
            (1.96 * se).tolist())


# =============================================================================
# Fig. S4.1 — Org NPS vs A (HEADLINE)
# =============================================================================

def make_fig_s4_1(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())

    fig, axes = plt.subplots(len(periods), len(rhos),
                              figsize=(6.0 * len(rhos), 4.5 * len(periods)),
                              sharey=True)
    if axes.ndim == 1:
        axes = axes.reshape(len(periods), len(rhos))

    for i, P in enumerate(periods):
        for j, rho in enumerate(rhos):
            ax = axes[i, j]
            for disc in DISC_ORDER:
                xs, ys, errs = _curve(df, disc, rho, P, "organisation_nps")
                if xs:
                    ax.errorbar(xs, ys, yerr=errs,
                                marker="o", linewidth=1.7, markersize=6,
                                capsize=3, color=DISC_COLORS[disc],
                                label=disc)
            ax.set_xlabel("Arrival amplitude $A$")
            if j == 0:
                ax.set_ylabel("Organisation NPS (pp)")
            ax.set_title(f"P = {P:.0f}d, ρ = {rho}")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == len(rhos) - 1:
                ax.legend(fontsize=9, loc="best")

    fig.suptitle("Figure S4.1: Organisation NPS vs sinusoidal arrival amplitude\n"
                 "(mean rate held constant; phase φ=0; 6 agents; intercept=10.22)",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_1_org_nps_vs_amplitude.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S4.2 — Individual NPS vs A
# =============================================================================

def make_fig_s4_2(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())

    fig, axes = plt.subplots(len(periods), len(rhos),
                              figsize=(6.0 * len(rhos), 4.5 * len(periods)),
                              sharey=True)
    if axes.ndim == 1:
        axes = axes.reshape(len(periods), len(rhos))

    for i, P in enumerate(periods):
        for j, rho in enumerate(rhos):
            ax = axes[i, j]
            for disc in DISC_ORDER:
                xs, ys, errs = _curve(df, disc, rho, P, "avg_individual_nps")
                if xs:
                    ax.errorbar(xs, ys, yerr=errs,
                                marker="o", linewidth=1.7, markersize=6,
                                capsize=3, color=DISC_COLORS[disc],
                                label=disc)
            ax.set_xlabel("Arrival amplitude $A$")
            if j == 0:
                ax.set_ylabel("Individual NPS (mean)")
            ax.set_title(f"P = {P:.0f}d, ρ = {rho}")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == len(rhos) - 1:
                ax.legend(fontsize=9, loc="best")

    fig.suptitle("Figure S4.2: Individual NPS vs sinusoidal arrival amplitude",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_2_individual_nps_vs_amplitude.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S4.3 — Discipline advantages over LRTF
# =============================================================================

def make_fig_s4_3(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())

    fig, axes = plt.subplots(len(periods), len(rhos),
                              figsize=(6.0 * len(rhos), 4.5 * len(periods)),
                              sharey=True)
    if axes.ndim == 1:
        axes = axes.reshape(len(periods), len(rhos))

    advantage_disciplines = ["SRTF", "NPS_BINNED"]
    for i, P in enumerate(periods):
        for j, rho in enumerate(rhos):
            ax = axes[i, j]
            xs_l, ys_l, _ = _curve(df, "LRTF", rho, P, "organisation_nps")
            ref = dict(zip(xs_l, ys_l))

            for disc in advantage_disciplines:
                xs, ys, errs = _curve(df, disc, rho, P, "organisation_nps")
                advs = [y - ref.get(x, np.nan) for x, y in zip(xs, ys)]
                ax.errorbar(xs, advs, yerr=errs,
                             marker="o", linewidth=1.7, markersize=6,
                             capsize=3, color=DISC_COLORS[disc],
                             label=f"{disc} − LRTF")
            ax.axhline(0, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
            ax.set_xlabel("Arrival amplitude $A$")
            if j == 0:
                ax.set_ylabel("Org NPS advantage over LRTF (pp)")
            ax.set_title(f"P = {P:.0f}d, ρ = {rho}")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == len(rhos) - 1:
                ax.legend(fontsize=9)

    fig.suptitle("Figure S4.3: Org-NPS advantage of SRTF and NPS_BINNED over LRTF\n"
                 "(H2: SRTF gap grows with A. H3: NPS_BINNED tracks SRTF or pulls ahead.)",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_3_advantage_vs_lrtf.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S4.4 — NPS_BINNED − SRTF
# =============================================================================

def make_fig_s4_4(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())

    fig, axes = plt.subplots(1, len(periods),
                              figsize=(6.5 * len(periods), 4.5),
                              sharey=True)
    if not hasattr(axes, "__len__"):
        axes = [axes]

    for i, P in enumerate(periods):
        ax = axes[i]
        for rho in rhos:
            xs_s, ys_s, _ = _curve(df, "SRTF", rho, P, "organisation_nps")
            ref = dict(zip(xs_s, ys_s))
            xs, ys, errs = _curve(df, "NPS_BINNED", rho, P, "organisation_nps")
            advs = [y - ref.get(x, np.nan) for x, y in zip(xs, ys)]
            ax.errorbar(xs, advs, yerr=errs,
                         marker="o", linewidth=1.7, markersize=6,
                         capsize=3, label=f"ρ = {rho}")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
        ax.set_xlabel("Arrival amplitude $A$")
        if i == 0:
            ax.set_ylabel("NPS_BINNED − SRTF (pp)")
        ax.set_title(f"P = {P:.0f}d")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

    fig.suptitle("Figure S4.4: Does non-stationary load break the SRTF tie? "
                 "(NPS_BINNED at f=0.20 minus SRTF)",
                 y=1.02, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_4_nps_binned_vs_srtf.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S4.5 — Daily queue traces (rows=A, cols=disciplines)
# =============================================================================

def make_fig_s4_5():
    if not DAILY_Q_PATH.exists():
        print(f"  Skipping fig_s4_5 (no {DAILY_Q_PATH.name})")
        return
    daily = pd.read_csv(DAILY_Q_PATH)

    P_focus = 28.0
    rho_focus = 1.0
    disciplines = ["FCFS", "SRTF", "NPS_BINNED"]
    amps = sorted(daily["amplitude"].unique())

    sub = daily[(daily["period_days"].round(1) == round(P_focus, 1))
                & (daily["rho"] == rho_focus)
                & (daily["discipline"].isin(disciplines))]

    fig, axes = plt.subplots(len(amps), len(disciplines),
                              figsize=(4.5 * len(disciplines), 2.6 * len(amps)),
                              sharex=True, sharey=True)
    if axes.ndim == 1:
        axes = axes.reshape(len(amps), len(disciplines))

    for i, A in enumerate(amps):
        for j, disc in enumerate(disciplines):
            ax = axes[i, j]
            cell = sub[(sub["amplitude"].round(3) == round(A, 3))
                       & (sub["discipline"] == disc)]
            if len(cell) == 0:
                ax.set_visible(False)
                continue
            grouped = cell.groupby("day")["queue_length"].agg(["mean", "std"]).reset_index()
            grouped = grouped.sort_values("day")
            ax.plot(grouped["day"], grouped["mean"], color=DISC_COLORS[disc],
                     linewidth=1.2)
            ax.fill_between(grouped["day"],
                            grouped["mean"] - grouped["std"],
                            grouped["mean"] + grouped["std"],
                            color=DISC_COLORS[disc], alpha=0.18)
            ax.axvline(30, color="black", linestyle=":", linewidth=0.6, alpha=0.5)
            if i == 0:
                ax.set_title(disc, fontsize=10)
            if j == 0:
                ax.set_ylabel(f"A = {A:.2f}\nqueue len", fontsize=9)
            if i == len(amps) - 1:
                ax.set_xlabel("day")
            ax.grid(True, alpha=0.25)

    fig.suptitle(f"Figure S4.5: Daily queue length traces (P={P_focus:.0f}d, ρ={rho_focus})\n"
                 "Mean ± 1 SD across replications. Vertical line = end of burn-in.",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_5_daily_queue_traces.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S4.6 — Operational metrics vs A
# =============================================================================

def make_fig_s4_6(df):
    rho = 1.0
    P = 28.0
    sub = df[(df["rho"] == rho) & (df["period_days"].round(1) == round(P, 1))]
    if len(sub) == 0:
        return

    plots = [
        ("avg_waiting_time_days",        "Avg waiting time (days)"),
        ("avg_case_resolution_time_days", "Avg resolution time (days)"),
        ("percent_cases_closed",          "% cases closed"),
        ("peak_queue_length",             "Peak queue length"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (col, title) in zip(axes.flatten(), plots):
        for disc in DISC_ORDER:
            xs, ys, errs = _curve(df, disc, rho, P, col)
            if xs:
                ax.errorbar(xs, ys, yerr=errs,
                            marker="o", linewidth=1.5, markersize=5,
                            capsize=3, color=DISC_COLORS[disc],
                            label=disc)
        ax.set_xlabel("Arrival amplitude $A$")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")

    fig.suptitle(f"Figure S4.6: Operational metrics vs $A$ (P={P:.0f}d, ρ={rho})",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_6_operational_vs_amplitude.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig. S4.7 — Daily arrivals trace (input verification)
# =============================================================================

def make_fig_s4_7():
    if not DAILY_A_PATH.exists():
        print(f"  Skipping fig_s4_7 (no {DAILY_A_PATH.name})")
        return
    daily = pd.read_csv(DAILY_A_PATH)

    P_focus = 28.0
    rho_focus = 1.0
    disc_focus = "FCFS"
    sub = daily[(daily["period_days"].round(1) == round(P_focus, 1))
                & (daily["rho"] == rho_focus)
                & (daily["discipline"] == disc_focus)]
    amps = sorted(sub["amplitude"].unique())

    fig, axes = plt.subplots(len(amps), 1,
                              figsize=(11, 2.0 * len(amps)),
                              sharex=True, sharey=True)
    if not hasattr(axes, "__len__"):
        axes = [axes]

    for ax, A in zip(axes, amps):
        cell = sub[sub["amplitude"].round(3) == round(A, 3)]
        if len(cell) == 0:
            continue
        grouped = cell.groupby("day")["arrivals"].mean().reset_index().sort_values("day")
        ax.plot(grouped["day"], grouped["arrivals"], color="#1f77b4", linewidth=0.9)
        ax.axvline(30, color="black", linestyle=":", linewidth=0.6, alpha=0.5)
        ax.set_ylabel(f"A={A:.2f}", fontsize=9)
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("day")
    fig.suptitle(f"Figure S4.7: Daily arrival counts (P={P_focus:.0f}d, ρ={rho_focus})\n"
                 "Mean across replications. Verifies input modulation; mean preserved.",
                 y=1.0, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4_7_daily_arrivals.pdf"
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
    print(f"  amplitude:   {sorted(df['amplitude'].unique())}")
    print(f"  period_days: {sorted(df['period_days'].unique())}")
    print()

    make_fig_s4_1(df)
    make_fig_s4_2(df)
    make_fig_s4_3(df)
    make_fig_s4_4(df)
    make_fig_s4_5()
    make_fig_s4_6(df)
    make_fig_s4_7()

    print("\nAll plots generated.")
