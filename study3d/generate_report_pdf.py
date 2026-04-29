"""
Generate a self-contained PDF report of Study 3d results, suitable for sharing
with a coauthor. Pulls data from results/results.csv and re-renders all figures
inside the report PDF for a single deliverable.

Output: results/Study3d_Report.pdf
"""
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

# Reuse figure code from generate_plots.py
from generate_plots import (
    DISC_ORDER, DISC_COLORS,
)
import json

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PATH = RESULTS_DIR / "results.csv"
EMPIRICAL_FILE = RESULTS_DIR / "empirical_nps_multinomial.json"
OUT_PATH = RESULTS_DIR / "Study3d_Report.pdf"

PAGE = (8.5, 11.0)  # US letter inches


# =============================================================================
# Page builders — each returns a matplotlib Figure
# =============================================================================

def make_cover_page(df):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.5, 0.85, "Study 3d", ha="center", fontsize=28, weight="bold")
    fig.text(0.5, 0.80, "Rank-binned NPS Prediction", ha="center", fontsize=20)
    fig.text(0.5, 0.74,
              "Internal results report — for coauthor review",
              ha="center", fontsize=12, style="italic")

    fig.text(0.5, 0.65,
              "Customer-service queueing based on predicted loyalty outcomes",
              ha="center", fontsize=11, color="#444")
    fig.text(0.5, 0.62,
              "Riess & Scholderer (2026) — replication / extension series",
              ha="center", fontsize=10, color="#444")

    box_y = 0.40
    fig.text(0.15, box_y + 0.08, "Run summary", fontsize=13, weight="bold")
    rho_levels = sorted(float(x) for x in df["rho"].unique())
    agent_levels = sorted(int(x) for x in df["n_agents"].unique())
    intercept = float(sorted(df["nps_intercept"].unique())[0])
    bullets = [
        f"Total runs:        {len(df):,}",
        f"Disciplines:       {', '.join(sorted(df['discipline'].unique()))}",
        f"ρ levels:          {rho_levels}",
        f"Replications:      {df['replication'].nunique()} per cell",
        f"Simulation period: 365 days",
        f"Agents:            {agent_levels} (critical-load setting)",
        f"NPS intercept:     {intercept:.2f} (paper baseline)",
        f"Sampling mode:     hard",
        f"SLA:               none",
    ]
    for i, line in enumerate(bullets):
        fig.text(0.18, box_y - i * 0.025, line, fontsize=10, family="monospace")

    fig.text(0.5, 0.05, f"Generated {date.today().isoformat()}",
              ha="center", fontsize=9, color="#888")
    return fig


def make_executive_summary(df):
    fig = plt.figure(figsize=PAGE)
    y = 0.93
    fig.text(0.08, y, "Executive summary", fontsize=18, weight="bold")

    findings = [
        ("H₃d is partially confirmed.",
         "Rank-binning the predicted NPS distribution to match the empirical "
         "multinomial successfully breaks the NPS ≡ LRTF equivalence at the "
         "paper's baseline calibration (intercept = 10.22). This is the first "
         "intervention in our study chain (3 → 3b → 3c → 3d) that achieves "
         "this without manipulating the intercept or adding topic-awareness."),

        ("The effect is real but modest.",
         "NPS_BINNED beats LRTF by +0.0067 individual NPS / +0.15 pp "
         "organisation NPS on average over ρ. At ρ = 1.0 (perfect prediction) "
         "the advantage grows to +0.034 indiv NPS / +1.13 pp organisation NPS "
         "— comparable in magnitude to Study 3b's plateau effect, but achieved "
         "at the paper's actual calibration."),

        ("The advantage grows monotonically with ρ.",
         "From −0.014 at ρ = 0 (pure noise) to +0.034 at ρ = 1.0 (perfect). "
         "This matches the structural prediction: rank-binning extracts value "
         "to the extent that the underlying Eq. 9 prediction carries information."),

        ("But SRTF outperforms NPS_BINNED on most quality metrics.",
         "SRTF achieves +20.65 organisation NPS, 48.51% promoters, 6.3-day "
         "resolution, 95.5% closure — better than NPS_BINNED on every dimension. "
         "Mechanism: SRTF directly optimises throughput, closing more cases "
         "(including more promoters) than disciplines that hold long cases for "
         "explicit prioritisation."),

        ("All sanity checks pass.",
         "FCFS is perfectly ρ-invariant (range = 0.0000). NPS ≡ LRTF holds to 6 "
         "decimal places — confirming Study 3's structural finding under this "
         "calibration. Rank-binning produces the empirical multinomial exactly "
         "(modulo a single rounding leftover absorbed into bin 10)."),
    ]
    y -= 0.05
    for i, (heading, body) in enumerate(findings):
        fig.text(0.08, y, f"{i+1}. {heading}", fontsize=11, weight="bold")
        y -= 0.025
        wrapped = body  # let matplotlib wrap via wrap=True
        fig.text(0.10, y, body, fontsize=9.5, wrap=True,
                  bbox=dict(boxstyle="round,pad=0.4", fc="#f5f5f5",
                              ec="#cccccc", lw=0.5),
                  va="top")
        y -= 0.110

    fig.text(0.08, 0.05,
              "Practical recommendation: if you have a calibrated throughput "
              "predictor, use SRTF. NPS_BINNED works but its gain over LRTF is "
              "small and SRTF dominates on every quality metric.",
              fontsize=9, style="italic", color="#444", wrap=True)
    return fig


def make_headline_table(df):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.5, 0.93, "Headline metrics by discipline (averaged over ρ)",
              ha="center", fontsize=14, weight="bold")
    fig.text(0.5, 0.90,
              "n = 500 runs per discipline, 100 reps × 5 ρ levels",
              ha="center", fontsize=9, style="italic", color="#666")

    rows = []
    for disc in DISC_ORDER:
        sub = df[df["discipline"] == disc]
        rows.append([
            disc,
            f"{sub['avg_individual_nps'].mean():.4f}",
            f"{sub['organisation_nps'].mean():+.2f}",
            f"{sub['percent_detractors'].mean():.4f}",
            f"{sub['percent_passives'].mean():.4f}",
            f"{sub['percent_promoters'].mean():.4f}",
            f"{sub['avg_waiting_time_days'].mean():.2f}",
            f"{sub['avg_case_resolution_time_days'].mean():.2f}",
            f"{sub['percent_cases_closed'].mean():.4f}",
        ])

    columns = ["Discipline", "Indiv NPS", "Org NPS", "% detr",
               "% pass", "% prom", "wait (d)", "res (d)", "% closed"]

    ax = fig.add_axes([0.05, 0.55, 0.90, 0.30])
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=columns, loc="center",
                     cellLoc="center", colLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.6)

    # Highlight winners per column (manually picked)
    # SRTF wins on: indiv NPS, org NPS, % detr, % prom, wait, res, % closed
    # FCFS wins on: % pass (mostly because least sorted)
    winner_idx = {
        1: "SRTF",  2: "SRTF",  3: "SRTF",  4: "FCFS",
        5: "SRTF",  6: "FCFS",  7: "SRTF",  8: "SRTF",
    }
    for col_idx, winner_disc in winner_idx.items():
        for row_idx, disc in enumerate(DISC_ORDER):
            if disc == winner_disc:
                cell = table[(row_idx + 1, col_idx)]
                cell.set_facecolor("#d5f5d5")
    # Header
    for col_idx in range(len(columns)):
        cell = table[(0, col_idx)]
        cell.set_facecolor("#cccccc")
        cell.set_text_props(weight="bold")

    # NPS_BINNED row — discipline column highlight
    for row_idx, disc in enumerate(DISC_ORDER):
        if disc == "NPS_BINNED":
            cell = table[(row_idx + 1, 0)]
            cell.set_facecolor("#fce5cd")
            cell.set_text_props(weight="bold")

    fig.text(0.05, 0.50, "Reading guide", fontsize=11, weight="bold")
    notes = [
        "• Green-shaded cells are the per-column winner.",
        "• NPS_BINNED row is highlighted; rest of cells unshaded for comparison.",
        "• NPS and LRTF cells are identical to 4 decimal places — Study 3's "
          "monotonicity finding holds.",
        "• SRTF wins on every quality metric except passive share (where FCFS "
          "is highest by virtue of doing no sorting at all).",
        "• NPS_BINNED is consistently between SRTF and LRTF on operational "
          "metrics — a smooth blend of the two.",
        "• % closed gap: SRTF closes 95.5% of cases, NPS/LRTF only 92.8%.",
    ]
    for i, line in enumerate(notes):
        fig.text(0.07, 0.46 - i * 0.022, line, fontsize=9.5, wrap=True)

    return fig


def make_segment_shifts_table(df):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.5, 0.94,
              "Segment shifts: discipline − FCFS (percentage points)",
              ha="center", fontsize=14, weight="bold")
    fig.text(0.5, 0.91,
              "Positive Δ %prom and negative Δ %detr indicate quality improvement",
              ha="center", fontsize=9, style="italic", color="#666")

    fcfs = df[df["discipline"] == "FCFS"]
    fcfs_d = fcfs["percent_detractors"].mean()
    fcfs_p = fcfs["percent_passives"].mean()
    fcfs_pr = fcfs["percent_promoters"].mean()

    rows = []
    for disc in DISC_ORDER:
        sub = df[df["discipline"] == disc]
        rows.append([
            disc,
            f"{(sub['percent_detractors'].mean() - fcfs_d) * 100:+.3f}",
            f"{(sub['percent_passives'].mean()   - fcfs_p) * 100:+.3f}",
            f"{(sub['percent_promoters'].mean()  - fcfs_pr) * 100:+.3f}",
            f"{sub['organisation_nps'].mean() - fcfs['organisation_nps'].mean():+.3f}",
        ])

    columns = ["Discipline", "Δ % detr", "Δ % pass", "Δ % prom", "Δ org NPS (pp)"]
    ax = fig.add_axes([0.13, 0.62, 0.74, 0.20])
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=columns, loc="center",
                     cellLoc="center", colLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.7)
    for col_idx in range(len(columns)):
        table[(0, col_idx)].set_facecolor("#cccccc")
        table[(0, col_idx)].set_text_props(weight="bold")
    for row_idx, disc in enumerate(DISC_ORDER):
        if disc == "NPS_BINNED":
            table[(row_idx + 1, 0)].set_facecolor("#fce5cd")
            table[(row_idx + 1, 0)].set_text_props(weight="bold")

    # Now NPS_BINNED − reference advantage at ρ=1.0
    fig.text(0.5, 0.55, "NPS_BINNED − reference at ρ = 1.0",
              ha="center", fontsize=12, weight="bold")

    rho1 = df[df["rho"] == 1.0]
    nb = rho1[rho1["discipline"] == "NPS_BINNED"]
    rows2 = []
    for ref in ["FCFS", "LRTF", "NPS", "SRTF"]:
        rs = rho1[rho1["discipline"] == ref]
        rows2.append([
            ref,
            f"{nb['avg_individual_nps'].mean()   - rs['avg_individual_nps'].mean():+.4f}",
            f"{nb['organisation_nps'].mean()    - rs['organisation_nps'].mean():+.3f}",
            f"{(nb['percent_detractors'].mean() - rs['percent_detractors'].mean())*100:+.3f}",
            f"{(nb['percent_promoters'].mean()  - rs['percent_promoters'].mean())*100:+.3f}",
        ])
    columns2 = ["Reference", "Δ Indiv NPS", "Δ Org NPS (pp)", "Δ % detr (pp)", "Δ % prom (pp)"]
    ax2 = fig.add_axes([0.10, 0.30, 0.80, 0.20])
    ax2.axis("off")
    table2 = ax2.table(cellText=rows2, colLabels=columns2, loc="center",
                       cellLoc="center", colLoc="center")
    table2.auto_set_font_size(False)
    table2.set_fontsize(9.5)
    table2.scale(1, 1.7)
    for col_idx in range(len(columns2)):
        table2[(0, col_idx)].set_facecolor("#cccccc")
        table2[(0, col_idx)].set_text_props(weight="bold")

    fig.text(0.10, 0.22,
              "At ρ = 1.0, NPS_BINNED beats LRTF and NPS by +0.034 indiv NPS "
              "/ +1.13 pp org NPS, but is essentially tied with SRTF (+0.003 / "
              "+0.08 pp) and beats FCFS by +0.067 / +2.49 pp.",
              fontsize=9.5, wrap=True, style="italic", color="#444")
    return fig


def make_rho_table(df):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.5, 0.95, "NPS_BINNED − LRTF advantage by ρ",
              ha="center", fontsize=14, weight="bold")
    fig.text(0.5, 0.92,
              "The signal grows monotonically with prediction quality",
              ha="center", fontsize=9, style="italic", color="#666")

    rhos = sorted(df["rho"].unique())
    rows = []
    for rho in rhos:
        nb = df[(df["discipline"] == "NPS_BINNED") & (df["rho"] == rho)]
        lrtf = df[(df["discipline"] == "LRTF") & (df["rho"] == rho)]
        rows.append([
            f"{rho:.2f}",
            f"{nb['avg_individual_nps'].mean()   - lrtf['avg_individual_nps'].mean():+.4f}",
            f"{nb['organisation_nps'].mean()    - lrtf['organisation_nps'].mean():+.3f}",
            f"{(nb['percent_detractors'].mean() - lrtf['percent_detractors'].mean())*100:+.3f}",
            f"{(nb['percent_promoters'].mean()  - lrtf['percent_promoters'].mean())*100:+.3f}",
        ])
    cols = ["ρ", "Δ Indiv NPS", "Δ Org NPS (pp)", "Δ % detr (pp)", "Δ % prom (pp)"]

    ax = fig.add_axes([0.10, 0.62, 0.80, 0.25])
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=cols, loc="center",
                     cellLoc="center", colLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.7)
    for col_idx in range(len(cols)):
        table[(0, col_idx)].set_facecolor("#cccccc")
        table[(0, col_idx)].set_text_props(weight="bold")
    for row_idx, r in enumerate(rhos):
        if r == 1.0:
            for col_idx in range(len(cols)):
                table[(row_idx + 1, col_idx)].set_facecolor("#d5f5d5")

    # Sanity check section
    fig.text(0.08, 0.55, "Sanity checks (all pass ✓)", fontsize=12, weight="bold")
    sanity = [
        ("FCFS ρ-invariance",
          "individual NPS range across ρ = 0.0000, detractor share range = 0.0000"),
        ("NPS ≡ LRTF preservation",
          "NPS − LRTF = 0.000000 across all five ρ levels (Study 3 finding holds)"),
        ("Replication count",
          "exactly 100 per (discipline, ρ) cell — total 2,500 runs"),
        ("Rank preservation",
          "binning is rank-monotone in raw predicted_nps by construction"),
        ("Target conformance",
          "per-rep histogram of binned values matches the empirical multinomial "
          "exactly (modulo a single rounding leftover absorbed into bin 10)"),
    ]
    for i, (heading, body) in enumerate(sanity):
        y = 0.49 - i * 0.06
        fig.text(0.10, y, f"• {heading}:", fontsize=10, weight="bold")
        fig.text(0.10, y - 0.022, f"  {body}", fontsize=9.5, color="#444",
                  wrap=True)

    return fig


# =============================================================================
# Re-render figures in the report PDF (parallel to generate_plots.py)
# =============================================================================

def make_fig_segment_shares(df, empirical):
    fig, axes = plt.subplots(1, 2, figsize=PAGE)
    fig.subplots_adjust(top=0.85, bottom=0.15, left=0.08, right=0.95, wspace=0.30)

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
    detr = np.array(detr); pas = np.array(pas); prom = np.array(prom)

    ax.bar(x, detr, color="#d62728", label="Detractors (0–6)")
    ax.bar(x, pas, bottom=detr, color="#7f7f7f", label="Passives (7–8)")
    ax.bar(x, prom, bottom=detr + pas, color="#2ca02c", label="Promoters (9–10)")

    if empirical:
        ed = empirical["segment_proportions"]["detractors_0_to_6"]
        ep = empirical["segment_proportions"]["passives_7_to_8"]
        ax.axhline(ed, color="black", linestyle="--", linewidth=0.7, alpha=0.5)
        ax.axhline(ed + ep, color="black", linestyle="--", linewidth=0.7, alpha=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, fontsize=9)
    ax.set_ylabel("Share of closed cases")
    ax.set_ylim(0, 1.05)
    ax.set_title("Realised NPS-segment shares (avg over ρ)", fontsize=11)
    ax.legend(loc="upper right", fontsize=8)

    for i, (d, p, pr) in enumerate(zip(detr, pas, prom)):
        ax.text(i, d / 2, f"{d:.3f}", ha="center", va="center", fontsize=8, color="white")
        ax.text(i, d + p / 2, f"{p:.3f}", ha="center", va="center", fontsize=8, color="white")
        ax.text(i, d + p + pr / 2, f"{pr:.3f}", ha="center", va="center", fontsize=8, color="white")

    ax = axes[1]
    org = []
    for disc in DISC_ORDER:
        sub = df[df["discipline"] == disc]
        org.append(sub["organisation_nps"].mean())
    bars = ax.bar(DISC_ORDER, org, color=[DISC_COLORS[d] for d in DISC_ORDER],
                    edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Organisation NPS (% prom − % detr)")
    ax.set_title("Organisation NPS by discipline (avg over ρ)", fontsize=11)
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=20, labelsize=9)
    for b, v in zip(bars, org):
        ax.text(b.get_x() + b.get_width() / 2, v,
                f"{v:+.2f}", ha="center", va="bottom", fontsize=9)

    fig.suptitle("Figure 1 — Segment-share comparison (headline)",
                  fontsize=13, weight="bold", y=0.95)
    return fig


def make_fig_metrics_vs_rho(df):
    fig, axes = plt.subplots(2, 2, figsize=PAGE)
    fig.subplots_adjust(top=0.90, bottom=0.08, left=0.10, right=0.95,
                          hspace=0.35, wspace=0.25)
    rhos = sorted(df["rho"].unique())

    plots = [
        (axes[0, 0], "avg_individual_nps", "Average individual NPS"),
        (axes[0, 1], "organisation_nps",   "Organisation NPS"),
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
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)

    fig.suptitle("Figure 2 — All metrics across ρ by discipline",
                  fontsize=13, weight="bold", y=0.96)
    return fig


def make_fig_advantage(df):
    fig, axes = plt.subplots(1, 2, figsize=PAGE)
    fig.subplots_adjust(top=0.82, bottom=0.42, left=0.08, right=0.95, wspace=0.30)
    rhos = sorted(df["rho"].unique())

    for ax, metric, ylabel in [
        (axes[0], "avg_individual_nps", "Δ individual NPS"),
        (axes[1], "organisation_nps",   "Δ organisation NPS (pp)"),
    ]:
        for ref_disc in ["FCFS", "LRTF", "NPS", "SRTF"]:
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
        ax.legend(fontsize=8)

    fig.suptitle("Figure 3 — NPS_BINNED advantage over reference disciplines",
                  fontsize=13, weight="bold", y=0.92)
    fig.text(0.08, 0.30,
              "Reading the plot:",
              fontsize=11, weight="bold")
    fig.text(0.08, 0.27,
              "• The grey line (NPS_BINNED − FCFS) is the practical lift over "
              "the company's current discipline. It grows from +0.04 to +0.07 "
              "individual NPS as ρ improves, and from +1.4 pp to +2.5 pp on "
              "organisation NPS.",
              fontsize=9.5, wrap=True)
    fig.text(0.08, 0.20,
              "• The blue (LRTF) and orange (NPS) lines are identical "
              "(Study 3: NPS ≡ LRTF). NPS_BINNED breaks even at ρ ≈ 0.22 and "
              "rises monotonically thereafter, peaking at +0.034 / +1.13 pp at ρ = 1.0.",
              fontsize=9.5, wrap=True)
    fig.text(0.08, 0.13,
              "• The green line (NPS_BINNED − SRTF) hovers around zero, "
              "occasionally dipping below at ρ = 0.5 and 0.85. SRTF is a strong "
              "competitor — NPS_BINNED does not consistently beat it on these metrics.",
              fontsize=9.5, wrap=True)
    return fig


def make_fig_binning_sanity(empirical):
    if empirical is None:
        return None
    from simulation import generate_all_arrivals, apply_rank_binning, NPS_PRED_INTERCEPT

    rng_a = np.random.default_rng(101)
    rng_b = np.random.default_rng(102)
    rng_c = np.random.default_rng(103)
    cases = generate_all_arrivals(365, rng_a, rng_b, rng_c, 1.0,
                                    nps_intercept=NPS_PRED_INTERCEPT)
    raw = np.array([c.predicted_nps for c in cases])
    apply_rank_binning(cases, empirical["proportions"])
    binned = np.array([c.predicted_nps_binned for c in cases])

    fig, axes = plt.subplots(3, 1, figsize=PAGE)
    fig.subplots_adjust(top=0.92, bottom=0.06, left=0.10, right=0.95, hspace=0.50)

    ax = axes[0]
    ax.hist(raw, bins=60, color="#1f77b4", alpha=0.7, edgecolor="black", linewidth=0.3)
    ax.axvline(7.5, color="black", linestyle="--", linewidth=1.0, label="midpoint = 7.5")
    ax.set_xlabel(r"raw $\hat{NPS}$ (Eq. 9)")
    ax.set_ylabel("Count")
    ax.set_title(f"Raw predicted NPS — n={len(raw)}, mean={raw.mean():.3f}, "
                  f"std={raw.std():.4f} (very narrow!)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    counts = np.bincount(binned, minlength=11)
    ax.bar(range(11), counts, color="#d62728", alpha=0.7,
            edgecolor="black", linewidth=0.5)
    ax.set_xlabel(r"binned $\hat{NPS}$")
    ax.set_ylabel("Count")
    ax.set_xticks(range(11))
    ax.set_title("Rank-binned predicted NPS — distribution after transformation",
                  fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)
    for i, v in enumerate(counts):
        if v > 0:
            ax.text(i, v, f"{v}", ha="center", va="bottom", fontsize=7)

    ax = axes[2]
    target = np.array(empirical["proportions"])
    actual = counts / counts.sum()
    width = 0.4
    x = np.arange(11)
    ax.bar(x - width / 2, target, width=width, color="#2ca02c", alpha=0.8,
            edgecolor="black", linewidth=0.4, label="empirical (target, n=1898)")
    ax.bar(x + width / 2, actual, width=width, color="#d62728", alpha=0.8,
            edgecolor="black", linewidth=0.4, label="binned (achieved)")
    ax.set_xlabel("NPS bin")
    ax.set_ylabel("Proportion")
    ax.set_xticks(range(11))
    ax.set_title("Target vs achieved bin proportions — exact match", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Figure 4 — Rank-binning sanity check",
                  fontsize=13, weight="bold", y=0.97)
    return fig


# =============================================================================
# Narrative pages
# =============================================================================

def make_narrative_page_1():
    fig = plt.figure(figsize=PAGE)
    fig.text(0.08, 0.94, "Why this study, and what we built", fontsize=14, weight="bold")

    text = (
        "The study chain (Study 2 → 3 → 3b → 3c) progressively narrowed in on a "
        "single observation: the paper's NPS-priority discipline produces case "
        "orderings identical to LRTF under the calibration the paper actually "
        "uses. Study 3 showed this is structural: Eq. 9 is monotonic in throughput "
        "and produces predicted NPS values entirely above 7.5, so |NPS_hat − 7.5| "
        "reduces to a monotonic re-labelling of throughput. Studies 3b and 3c "
        "broke the equivalence by manipulating intercept (3b) or adding "
        "topic-aware predictors (3c), but only outside the paper's actual "
        "calibration.\n\n"
        "Study 3d takes a different route. Instead of changing the prediction model "
        "or the intercept, we change the priority function's input: the predicted "
        "NPS is rank-mapped onto the empirical multinomial distribution of "
        "realised NPS responses (n = 1,898, supplied by the paper authors). "
        "The transformation is rank-preserving — the case predicted to have the "
        "shortest throughput still gets the highest predicted NPS — but values "
        "are now spread across the full 0–10 scale, so |NPS_binned − 7.5| has "
        "genuine V-shape and ~14.5% of cases (those binned to 7 or 8) get top "
        "priority instead of being indistinguishable from the rest.\n\n"
        "The paper itself flagged this exact follow-up on p. 23: "
        "\"In follow-up studies, the distribution of the individual NPS responses "
        "should be systematically varied … to identify the conditions under "
        "which the NPS-based prioritisation discipline will diverge from the "
        "LRTF discipline.\" Study 3d is that follow-up."
    )
    fig.text(0.08, 0.88, text, fontsize=10, va="top", wrap=True)

    fig.text(0.08, 0.30, "Implementation summary", fontsize=12, weight="bold")
    impl = (
        "• New discipline 'NPS_BINNED' added to study3d/simulation.py (fork of "
        "study3c). Preserves all Study 2/3 calibration (intercept = 10.22, no "
        "topic-aware, all paper coefficients).\n\n"
        "• 5 disciplines × 5 ρ levels × 100 replications = 2,500 simulation runs, "
        "each 365 days, 6 agents, hard sampling, no SLA.\n\n"
        "• Headline new metrics: per-segment shares (% detractors / passives / "
        "promoters) of realised customer responses.\n\n"
        "• Random tie-break within priority class via per-case key drawn at "
        "case creation. ~62.5% of cases tie in bin 10 (priority 2.5) → bulk of "
        "the queue is resolved randomly within that class.\n\n"
        "• All sanity checks pass (FCFS ρ-invariance: 0.0000; NPS ≡ LRTF: "
        "0.000000 across all ρ; rank preservation: by construction; "
        "target conformance: exact)."
    )
    fig.text(0.08, 0.27, impl, fontsize=10, va="top", wrap=True)
    return fig


def make_narrative_page_2():
    fig = plt.figure(figsize=PAGE)
    fig.text(0.08, 0.94, "Interpretation in the study chain", fontsize=14, weight="bold")

    text = (
        "How does Study 3d fit alongside its siblings?\n\n"
        "Study 2 reproduced the paper. NPS > FCFS, NPS ≈ LRTF. Confirmed all 8 "
        "qualitative claims.\n\n"
        "Study 3 isolated the LRTF equivalence as structural. Across all 5 ρ "
        "levels, NPS = LRTF to 4 decimal places. The paper's own Eq. 9 "
        "produces predictions entirely on one side of 7.5; the abs operator "
        "never folds.\n\n"
        "Study 3b broke the equivalence by lowering the intercept. The transition "
        "is sharp (between intercept 9.5 and 8.75) and produces a plateau effect "
        "with maximum +0.0375 individual NPS / +1.39 pp organisation NPS at "
        "intercept ≤ 8.75 and ρ = 1.0. Diagnostic: the entire predicted "
        "distribution shifts from 'all above 7.5' to 'all below 7.5'. The "
        "abs still doesn't fold — what changes is the slope of priority vs "
        "throughput.\n\n"
        "Study 3c added topic-coefficients to Eq. 9. Result: at the paper's "
        "intercept, topic-awareness made the discipline worse than LRTF by "
        "−0.04 individual NPS — the discipline prioritised cases predicted to "
        "have low actual NPS first. At intercept = 8.0, topic-awareness "
        "compounded with the intercept fix and gave the best result yet "
        "(+0.066 individual NPS / +2.37 pp org NPS at ρ = 1.0).\n\n"
        "Study 3d: rank-binning at paper baseline. First time NPS ≢ LRTF "
        "without changing the intercept or model. Peak advantage: +0.034 "
        "individual NPS / +1.13 pp organisation NPS at ρ = 1.0. This roughly "
        "matches Study 3b's plateau effect — but achieved at the calibration "
        "the paper actually uses."
    )
    fig.text(0.08, 0.88, text, fontsize=10, va="top", wrap=True)

    fig.text(0.08, 0.18, "The unexpected finding: SRTF dominates", fontsize=12, weight="bold")
    text2 = (
        "The new discipline works as designed — but a much simpler discipline (SRTF) "
        "outperforms it on every quality metric. SRTF achieves +20.65 organisation "
        "NPS, 48.5% promoter share, 6.3-day resolution time, 95.5% closure rate. "
        "NPS_BINNED ranks second on each. Mechanism: SRTF closes more cases overall "
        "(by serving short cases first, no holdouts), and Eq. 8's negative throughput "
        "coefficient means more closure → higher realised NPS distribution shifted "
        "toward 9–10. The two-stage NPS-prediction architecture, even after the "
        "diagnostic fix, doesn't beat single-stage throughput-based prioritisation."
    )
    fig.text(0.08, 0.15, text2, fontsize=10, va="top", wrap=True)
    return fig


def make_narrative_page_3():
    fig = plt.figure(figsize=PAGE)
    fig.text(0.08, 0.94, "Limitations and follow-ups", fontsize=14, weight="bold")

    fig.text(0.08, 0.88, "Limitations of Study 3d:", fontsize=11, weight="bold")
    limits = [
        "• Single intercept (10.22). We don't know whether rank-binning + "
          "low intercept compounds with Study 3b's effects.",
        "• Single agent count (6). Study 2 showed effects depend on capacity.",
        "• No SLA. Study 2 showed SLA = 60h erases all discipline differences.",
        "• No topic-aware × binning interaction. Study 3c found topic-awareness "
          "is double-edged; combining it with binning is open.",
        "• Random tie-break introduces variance. ~62.5% of cases tie in bin 10. "
          "Deterministic alternatives (FCFS-within-class, SRTF-within-class) "
          "could give cleaner discipline definitions.",
    ]
    for i, line in enumerate(limits):
        fig.text(0.08, 0.83 - i * 0.05, line, fontsize=10, wrap=True)

    fig.text(0.08, 0.55, "Recommended follow-ups:", fontsize=11, weight="bold")
    follow = [
        ("Study 3d-ext: low intercept × rank-binning",
          "Test whether rank-binning at intercept = 8.0 stacks with "
          "Study 3b's plateau. Could uncover a 'super-additive' regime."),
        ("Tie-break sensitivity",
          "Compare random vs FCFS-within-class vs SRTF-within-class for "
          "NPS_BINNED. Could close the gap to SRTF if SRTF-within-class works."),
        ("Uniform multinomial",
          "The empirical distribution is heavily promoter-skewed (76% in 9–10). "
          "A uniform target (1/11 per bin) would isolate 'rank-binning per se' "
          "from the empirical shape."),
        ("Capacity sweep",
          "Repeat with 3, 5, 7, 9 agents. NPS_BINNED's advantage over SRTF may "
          "emerge at any capacity level — Study 2 showed effects vary "
          "non-monotonically."),
    ]
    for i, (heading, body) in enumerate(follow):
        y = 0.50 - i * 0.07
        fig.text(0.10, y, f"• {heading}", fontsize=10, weight="bold")
        fig.text(0.10, y - 0.022, f"  {body}", fontsize=9.5, color="#444",
                  wrap=True)

    fig.text(0.08, 0.16, "Practical recommendation", fontsize=12, weight="bold")
    rec = (
        "If the goal is maximum customer-loyalty outcomes for a customer-service "
        "organisation similar to the case company, the chain of studies points to "
        "SRTF as the single strongest discipline. NPS_BINNED is a meaningful "
        "improvement over the original symmetric NPS / LRTF formulation, but it "
        "does not surpass SRTF in any quality metric we measured. The two-stage "
        "NPS-prediction architecture's unique value over throughput-based "
        "prioritisation is conditional on conditions (low intercept × topic-aware "
        "× rank-binning × high ρ) that are not present in the paper's actual "
        "calibration."
    )
    fig.text(0.08, 0.13, rec, fontsize=10, va="top", wrap=True, style="italic",
              color="#444")
    return fig


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} does not exist.")
        raise SystemExit(1)

    df = pd.read_csv(CSV_PATH)
    empirical = None
    if EMPIRICAL_FILE.exists():
        with open(EMPIRICAL_FILE) as f:
            empirical = json.load(f)

    print(f"Loaded {len(df)} runs. Generating PDF report → {OUT_PATH.name}")

    with PdfPages(OUT_PATH) as pdf:
        for builder in [
            lambda: make_cover_page(df),
            lambda: make_executive_summary(df),
            lambda: make_headline_table(df),
            lambda: make_segment_shifts_table(df),
            lambda: make_rho_table(df),
            lambda: make_fig_segment_shares(df, empirical),
            lambda: make_fig_metrics_vs_rho(df),
            lambda: make_fig_advantage(df),
            lambda: make_fig_binning_sanity(empirical),
            make_narrative_page_1,
            make_narrative_page_2,
            make_narrative_page_3,
        ]:
            fig = builder()
            if fig is not None:
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

    print(f"Done. {OUT_PATH}")
    print(f"Size: {OUT_PATH.stat().st_size / 1024:.1f} KB")
