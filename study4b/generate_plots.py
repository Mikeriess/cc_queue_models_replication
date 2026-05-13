"""
Generate Study 4b plots.

Eight figures focused on the ρ_topic interaction:
    1. Org NPS vs A, panels by (P, ρ_thr), lines by discipline, faceted by ρ_topic.
    2. NPS_BINNED − SRTF vs A, panels by (P, ρ_thr), lines by ρ_topic — H4b.2.
    3. NPS − LRTF vs ρ_topic, panels by (A, P) — H4b.1 directly.
    4. Org NPS vs ρ_topic at A=0.75, panels by (P, ρ_thr), lines by discipline.
    5. Diagnostics: Var(predicted_nps), topic_match_rate, corr(pred, actual)
       as functions of ρ_topic.
    6. Operational metrics vs A at ρ_topic=1, P=28, ρ_thr=1.
    7. Daily queue traces: rows=A, cols=discipline, ρ_topic=1, P=28, ρ_thr=1.
    8. Headline scatter: discipline gains as function of (ρ_thr × ρ_topic).
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

DISC_ORDER = ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]
DISC_COLORS = {
    "FCFS":       "#7f7f7f",
    "LRTF":       "#1f77b4",
    "SRTF":       "#2ca02c",
    "NPS":        "#ff7f0e",
    "NPS_BINNED": "#d62728",
}
RHO_TOPIC_COLORS = {0.0: "#7f7f7f", 0.5: "#ff7f0e", 1.0: "#d62728"}


def _curve(df, discipline, rho, period, rho_topic, col):
    sub = df[(df["discipline"] == discipline)
             & (df["rho"] == rho)
             & (df["period_days"].round(1) == round(period, 1))
             & (df["rho_topic"].round(3) == round(rho_topic, 3))]
    if len(sub) == 0:
        return [], [], []
    grouped = sub.groupby("amplitude")[col].agg(["mean", "std", "count"]).reset_index()
    grouped = grouped.sort_values("amplitude")
    se = grouped["std"] / np.sqrt(grouped["count"])
    return (grouped["amplitude"].tolist(),
            grouped["mean"].tolist(),
            (1.96 * se).tolist())


# =============================================================================
# Fig 1 — Org NPS vs A, faceted by ρ_topic (rows) × (P, ρ_thr) (cols)
# =============================================================================

def make_fig_1(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())
    rho_topics = sorted(df["rho_topic"].unique())

    col_pairs = [(P, rho) for P in periods for rho in rhos]
    n_cols = len(col_pairs)
    n_rows = len(rho_topics)

    fig, axes = plt.subplots(n_rows, n_cols,
                              figsize=(4.5 * n_cols, 3.6 * n_rows),
                              sharey=True)
    if n_rows == 1: axes = np.array([axes])
    if n_cols == 1: axes = axes.reshape(n_rows, 1)

    for i, rt in enumerate(rho_topics):
        for j, (P, rho) in enumerate(col_pairs):
            ax = axes[i, j]
            for disc in DISC_ORDER:
                xs, ys, errs = _curve(df, disc, rho, P, rt, "organisation_nps")
                if xs:
                    ax.errorbar(xs, ys, yerr=errs,
                                marker="o", linewidth=1.5, markersize=5,
                                capsize=2, color=DISC_COLORS[disc],
                                label=disc)
            if i == n_rows - 1:
                ax.set_xlabel("Arrival amplitude $A$")
            if j == 0:
                ax.set_ylabel(f"ρ_topic = {rt:.2f}\nOrg NPS (pp)")
            if i == 0:
                ax.set_title(f"P = {P:.0f}d, ρ_thr = {rho}")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == n_cols - 1:
                ax.legend(fontsize=8, loc="best")

    fig.suptitle("Figure S4b.1: Organisation NPS vs amplitude — facet by ρ_topic",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_1_org_nps_vs_A.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 2 — NPS_BINNED − SRTF vs A, lines by ρ_topic
# =============================================================================

def make_fig_2(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())
    rho_topics = sorted(df["rho_topic"].unique())

    fig, axes = plt.subplots(len(periods), len(rhos),
                              figsize=(5.5 * len(rhos), 4.0 * len(periods)),
                              sharey=True)
    if axes.ndim == 1: axes = axes.reshape(len(periods), len(rhos))

    for i, P in enumerate(periods):
        for j, rho in enumerate(rhos):
            ax = axes[i, j]
            for rt in rho_topics:
                xs_s, ys_s, _ = _curve(df, "SRTF", rho, P, rt, "organisation_nps")
                ref = dict(zip(xs_s, ys_s))
                xs, ys, errs = _curve(df, "NPS_BINNED", rho, P, rt, "organisation_nps")
                advs = [y - ref.get(x, np.nan) for x, y in zip(xs, ys)]
                ax.errorbar(xs, advs, yerr=errs,
                            marker="o", linewidth=1.5, markersize=5,
                            capsize=2, color=RHO_TOPIC_COLORS.get(rt, "#000"),
                            label=f"ρ_topic = {rt:.2f}")
            ax.axhline(0, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
            ax.set_xlabel("Arrival amplitude $A$")
            if j == 0:
                ax.set_ylabel("NPS_BINNED − SRTF (pp)")
            ax.set_title(f"P = {P:.0f}d, ρ_thr = {rho}")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == len(rhos) - 1:
                ax.legend(fontsize=9)

    fig.suptitle("Figure S4b.2: NPS_BINNED − SRTF vs A by ρ_topic\n"
                 "H4b.2: does topic-aware predictor unlock NPS_BINNED?",
                 y=1.02, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_2_nps_binned_vs_srtf.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 3 — NPS − LRTF vs ρ_topic (H4b.1)
# =============================================================================

def make_fig_3(df):
    rho_topics = sorted(df["rho_topic"].unique())
    amps = sorted(df["amplitude"].unique())
    periods = sorted(df["period_days"].unique())

    fig, axes = plt.subplots(1, len(periods),
                              figsize=(6.0 * len(periods), 4.5),
                              sharey=True)
    if not hasattr(axes, "__len__"):
        axes = [axes]

    for ax, P in zip(axes, periods):
        for A in amps:
            diffs = []
            errs = []
            for rt in rho_topics:
                n = df[(df["discipline"] == "NPS") &
                       (df["rho"] == 1.0) &
                       (df["period_days"].round(1) == round(P, 1)) &
                       (df["amplitude"].round(3) == round(A, 3)) &
                       (df["rho_topic"].round(3) == round(rt, 3))]["organisation_nps"]
                l = df[(df["discipline"] == "LRTF") &
                       (df["rho"] == 1.0) &
                       (df["period_days"].round(1) == round(P, 1)) &
                       (df["amplitude"].round(3) == round(A, 3)) &
                       (df["rho_topic"].round(3) == round(rt, 3))]["organisation_nps"]
                diffs.append(n.mean() - l.mean())
                # paired-rep SE
                if len(n) == len(l) and len(n) > 1:
                    pairs = n.values - l.values
                    errs.append(1.96 * pairs.std() / np.sqrt(len(pairs)))
                else:
                    errs.append(0.0)
            ax.errorbar(rho_topics, diffs, yerr=errs,
                        marker="o", linewidth=1.5, markersize=5, capsize=3,
                        label=f"A = {A:.2f}")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
        ax.set_xlabel(r"$\rho_{\mathrm{topic}}$")
        ax.set_ylabel("NPS − LRTF (pp organisation NPS)")
        ax.set_title(f"P = {P:.0f}d, ρ_thr = 1.0")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc="best")

    fig.suptitle("Figure S4b.3: NPS − LRTF by topic-accuracy\n"
                 "H4b.1: does topic info break the NPS ≡ LRTF collapse?",
                 y=1.03, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_3_nps_minus_lrtf_vs_rho_topic.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 4 — Org NPS vs ρ_topic at A=0.75
# =============================================================================

def make_fig_4(df):
    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())
    rho_topics = sorted(df["rho_topic"].unique())
    A_focus = 0.75

    fig, axes = plt.subplots(len(periods), len(rhos),
                              figsize=(5.5 * len(rhos), 4.0 * len(periods)),
                              sharey=True)
    if axes.ndim == 1: axes = axes.reshape(len(periods), len(rhos))

    for i, P in enumerate(periods):
        for j, rho in enumerate(rhos):
            ax = axes[i, j]
            for disc in DISC_ORDER:
                means = []
                errs = []
                for rt in rho_topics:
                    sub = df[(df["discipline"] == disc) &
                             (df["rho"] == rho) &
                             (df["period_days"].round(1) == round(P, 1)) &
                             (df["amplitude"].round(3) == round(A_focus, 3)) &
                             (df["rho_topic"].round(3) == round(rt, 3))]["organisation_nps"]
                    means.append(sub.mean())
                    errs.append(1.96 * sub.std() / np.sqrt(max(1, len(sub))))
                ax.errorbar(rho_topics, means, yerr=errs,
                            marker="o", linewidth=1.5, markersize=5, capsize=2,
                            color=DISC_COLORS[disc], label=disc)
            ax.set_xlabel(r"$\rho_{\mathrm{topic}}$")
            if j == 0:
                ax.set_ylabel("Org NPS (pp)")
            ax.set_title(f"P = {P:.0f}d, ρ_thr = {rho}")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == len(rhos) - 1:
                ax.legend(fontsize=8)

    fig.suptitle(f"Figure S4b.4: Organisation NPS vs ρ_topic at A = {A_focus}",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_4_org_nps_vs_rho_topic.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 5 — Predictor diagnostics
# =============================================================================

def make_fig_5(df):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    rho_topics = sorted(df["rho_topic"].unique())
    rhos = sorted(df["rho"].unique())

    diagnostics = [
        ("predicted_nps_var", "Var(predicted_nps)"),
        ("topic_match_rate",   "Topic match rate"),
        ("pred_actual_corr",   "corr(predicted, actual NPS)"),
    ]
    for ax, (col, title) in zip(axes, diagnostics):
        for rho in rhos:
            ys = []
            es = []
            for rt in rho_topics:
                sub = df[(df["rho"] == rho) &
                         (df["rho_topic"].round(3) == round(rt, 3))][col]
                sub = sub.dropna()
                ys.append(sub.mean() if len(sub) else np.nan)
                es.append(1.96 * sub.std() / np.sqrt(max(1, len(sub))) if len(sub) else 0.0)
            ax.errorbar(rho_topics, ys, yerr=es, marker="o", capsize=3,
                        label=f"ρ_thr = {rho}")
        ax.set_xlabel(r"$\rho_{\mathrm{topic}}$")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

    fig.suptitle("Figure S4b.5: Predictor diagnostics by ρ_topic and ρ_throughput",
                 y=1.03, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_5_predictor_diagnostics.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 6 — Operational metrics at ρ_topic=1
# =============================================================================

def make_fig_6(df):
    rho = 1.0
    P = 28.0
    rt = 1.0

    plots = [
        ("avg_waiting_time_days",         "Avg waiting time (days)"),
        ("avg_case_resolution_time_days", "Avg resolution time (days)"),
        ("percent_cases_closed",          "% cases closed"),
        ("peak_queue_length",             "Peak queue length"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (col, title) in zip(axes.flatten(), plots):
        for disc in DISC_ORDER:
            xs, ys, errs = _curve(df, disc, rho, P, rt, col)
            if xs:
                ax.errorbar(xs, ys, yerr=errs,
                            marker="o", linewidth=1.5, markersize=5,
                            capsize=2, color=DISC_COLORS[disc],
                            label=disc)
        ax.set_xlabel("Arrival amplitude $A$")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle(f"Figure S4b.6: Operational metrics vs A (P={P:.0f}d, "
                 f"ρ_thr={rho}, ρ_topic={rt})",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_6_operational_vs_A.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 7 — Daily queue traces at ρ_topic=1
# =============================================================================

def make_fig_7():
    if not DAILY_Q_PATH.exists():
        print(f"  Skipping fig_7 (no {DAILY_Q_PATH.name})")
        return
    daily = pd.read_csv(DAILY_Q_PATH)

    P_focus = 28.0
    rho_focus = 1.0
    rt_focus = 1.0
    disciplines = ["FCFS", "SRTF", "NPS", "NPS_BINNED"]
    amps = sorted(daily["amplitude"].unique())

    sub = daily[(daily["period_days"].round(1) == round(P_focus, 1))
                & (daily["rho"] == rho_focus)
                & (daily["rho_topic"].round(3) == round(rt_focus, 3))
                & (daily["discipline"].isin(disciplines))]

    fig, axes = plt.subplots(len(amps), len(disciplines),
                              figsize=(3.6 * len(disciplines), 2.5 * len(amps)),
                              sharex=True, sharey=True)
    if axes.ndim == 1: axes = axes.reshape(len(amps), len(disciplines))

    for i, A in enumerate(amps):
        for j, disc in enumerate(disciplines):
            ax = axes[i, j]
            cell = sub[(sub["amplitude"].round(3) == round(A, 3))
                       & (sub["discipline"] == disc)]
            if len(cell) == 0:
                ax.set_visible(False); continue
            grouped = cell.groupby("day")["queue_length"].agg(["mean", "std"]).reset_index()
            grouped = grouped.sort_values("day")
            ax.plot(grouped["day"], grouped["mean"], color=DISC_COLORS[disc],
                    linewidth=1.0)
            ax.fill_between(grouped["day"],
                            grouped["mean"] - grouped["std"],
                            grouped["mean"] + grouped["std"],
                            color=DISC_COLORS[disc], alpha=0.18)
            ax.axvline(30, color="black", linestyle=":", linewidth=0.6, alpha=0.5)
            if i == 0:
                ax.set_title(disc, fontsize=10)
            if j == 0:
                ax.set_ylabel(f"A = {A:.2f}", fontsize=9)
            if i == len(amps) - 1:
                ax.set_xlabel("day")
            ax.grid(True, alpha=0.25)

    fig.suptitle(f"Figure S4b.7: Daily queue traces "
                 f"(P={P_focus:.0f}d, ρ_thr={rho_focus}, ρ_topic={rt_focus})",
                 y=1.00, fontsize=12)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_7_daily_queue_traces.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Fig 8 — Headline summary: best - FCFS gap as function of (ρ_thr × ρ_topic × A)
# =============================================================================

def make_fig_8(df):
    rho_topics = sorted(df["rho_topic"].unique())
    amps = sorted(df["amplitude"].unique())
    P_focus = 28.0
    rho = 1.0

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    for rt in rho_topics:
        fcfs_y = []
        best_y = []
        best_e = []
        for A in amps:
            f = df[(df["discipline"] == "FCFS") &
                   (df["rho"] == rho) &
                   (df["period_days"].round(1) == round(P_focus, 1)) &
                   (df["amplitude"].round(3) == round(A, 3)) &
                   (df["rho_topic"].round(3) == round(rt, 3))]["organisation_nps"].mean()
            best_val = -np.inf
            best_std = 0.0
            best_n = 1
            for disc in ["LRTF", "SRTF", "NPS", "NPS_BINNED"]:
                vals = df[(df["discipline"] == disc) &
                          (df["rho"] == rho) &
                          (df["period_days"].round(1) == round(P_focus, 1)) &
                          (df["amplitude"].round(3) == round(A, 3)) &
                          (df["rho_topic"].round(3) == round(rt, 3))]["organisation_nps"]
                m = vals.mean()
                if m > best_val:
                    best_val = m
                    best_std = vals.std()
                    best_n = len(vals)
            fcfs_y.append(f)
            best_y.append(best_val - f)
            best_e.append(1.96 * best_std / np.sqrt(max(1, best_n)))
        ax.errorbar(amps, best_y, yerr=best_e,
                    marker="o", linewidth=1.5, markersize=6, capsize=3,
                    color=RHO_TOPIC_COLORS.get(rt, "#000"),
                    label=f"ρ_topic = {rt:.2f}")

    ax.set_xlabel("Arrival amplitude $A$")
    ax.set_ylabel("Best discipline − FCFS  (pp organisation NPS)")
    ax.set_title(f"Figure S4b.8: Best−FCFS gap by amplitude and ρ_topic\n"
                 f"(P = {P_focus:.0f}d, ρ_thr = {rho})")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    fig.tight_layout()
    out = RESULTS_DIR / "fig_s4b_8_best_vs_fcfs_gap.pdf"
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
    print(f"  ρ_thr:       {sorted(df['rho'].unique())}")
    print(f"  ρ_topic:     {sorted(df['rho_topic'].unique())}")
    print(f"  amplitude:   {sorted(df['amplitude'].unique())}")
    print(f"  period_days: {sorted(df['period_days'].unique())}")
    print()

    make_fig_1(df)
    make_fig_2(df)
    make_fig_3(df)
    make_fig_4(df)
    make_fig_5(df)
    make_fig_6(df)
    make_fig_7()
    make_fig_8(df)

    print("\nAll plots generated.")
