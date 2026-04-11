"""
Generér plots til sammenligning med artiklens Fig. 5, 6, 7, 8, 9 og 10.

Figurer der reproduceres:
    Fig. 5:  Daily queue length over simuleringsperioden (no SLA)
    Fig. 6:  Daily queue length over simuleringsperioden (SLA=60h)
    Fig. 7:  Average queue length, capacity utilisation, % cases closed
             som funktion af discipline × n_agents × SLA
    Fig. 8:  Average waiting time + average case resolution time
    Fig. 9:  Average individual NPS + organisation NPS
    Fig. 10: % cases closed over sidste 335 dage (robusthedstjek)

Figurer der kræver ekstra data:
    Fig. 5, 6: kræver daily_queue_lengths.csv (produceret af run_experiments.py)
    Fig. 8 (resolution time): kræver avg_case_resolution_time_days i results.csv
    Fig. 10: kræver percent_cases_closed_last_335 i results.csv

Alle figurer gemmes som PDF.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# =============================================================================
# Indlæsning og forberedelse af data
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = RESULTS_DIR / "results.csv"
DAILY_PATH = RESULTS_DIR / "daily_queue_lengths.csv.gz"

# Fallback til ukomprimeret version hvis komprimeret ikke findes
if not DAILY_PATH.exists():
    _uncompressed = RESULTS_DIR / "daily_queue_lengths.csv"
    if _uncompressed.exists():
        DAILY_PATH = _uncompressed

# Fallback til gamle filnavne hvis de nye ikke findes
if not CSV_PATH.exists():
    legacy = SCRIPT_DIR / "results_queue_experiment.csv"
    if legacy.exists():
        CSV_PATH = legacy

df = pd.read_csv(CSV_PATH)
df["sla_label"] = df["sla_hours"].fillna("None").astype(str)
df["sla_label"] = df["sla_label"].replace({"None": "None", "60.0": "SLA = 60 hours"})

# Tjek om vi har de nye kolonner fra opdateret simulation.py
HAS_RESOLUTION_TIME = "avg_case_resolution_time_days" in df.columns
HAS_LAST_335 = "percent_cases_closed_last_335" in df.columns
HAS_DAILY = DAILY_PATH.exists()

# Daglige kølængder (til Fig. 5 og 6)
daily_df = None
if HAS_DAILY:
    print(f"Indlæser daglige kølængder fra {DAILY_PATH.name}...")
    daily_df = pd.read_csv(DAILY_PATH)
    daily_df["sla_label"] = daily_df["sla_hours"].fillna("None").astype(str)
    daily_df["sla_label"] = daily_df["sla_label"].replace(
        {"None": "None", "60.0": "SLA = 60 hours"}
    )

DISCIPLINES = ["NPS", "LRTF", "SRTF", "FCFS"]
AGENTS = sorted(df["n_agents"].unique())
SLA_ORDER = ["None", "SLA = 60 hours"]

# Farve-mapping (matcher approximativt artiklens figurer)
COLORS = {
    "NPS": "#d62728",    # rød
    "LRTF": "#2ca02c",   # grøn
    "SRTF": "#1f77b4",   # blå
    "FCFS": "#ff7f0e",   # orange
}


def aggregate(metric: str) -> pd.DataFrame:
    """Aggregér en metric med mean og 95% CI over replikationer."""
    grp = df.groupby(["discipline", "n_agents", "sla_label"])[metric]
    agg = grp.agg(["mean", "std", "count"]).reset_index()
    agg["sem"] = agg["std"] / np.sqrt(agg["count"])
    agg["ci95"] = 1.96 * agg["sem"]
    return agg


def plot_metric_panel(ax, metric: str, ylabel: str, sla_label: str):
    """Plot én metric for én SLA-betingelse: x=n_agents, lines=discipline."""
    agg = aggregate(metric)
    sub = agg[agg["sla_label"] == sla_label]

    for disc in DISCIPLINES:
        data = sub[sub["discipline"] == disc].sort_values("n_agents")
        ax.errorbar(
            data["n_agents"], data["mean"],
            yerr=data["ci95"],
            label=disc,
            color=COLORS[disc],
            marker="o",
            capsize=3,
            linewidth=1.5,
            markersize=5,
        )
    ax.set_xlabel("Number of agents")
    ax.set_ylabel(ylabel)
    ax.set_xticks(AGENTS)
    ax.grid(True, alpha=0.3)


# =============================================================================
# Figur 5 & 6: Daglig kølængde over simuleringsperioden
# =============================================================================

def make_fig5_or_6(sla_label: str, filename: str, title: str):
    """
    Replika af artiklens Fig. 5 (no SLA) eller Fig. 6 (SLA=60h).

    7 subplots (én pr. agent-niveau), 4 linjer pr. subplot (én pr. disciplin),
    gennemsnit af daglig kølængde over 100 replikationer.
    """
    if daily_df is None:
        print(f"  [SKIP] {filename}: daily_queue_lengths.csv findes ikke")
        return

    sub = daily_df[daily_df["sla_label"] == sla_label]

    # Aggregér: middelværdi af queue_length over replikationer,
    # for hver (discipline, n_agents, day)
    agg = (sub.groupby(["discipline", "n_agents", "day"])["queue_length"]
              .mean().reset_index())

    n_agents_levels = sorted(agg["n_agents"].unique())
    n_panels = len(n_agents_levels)

    # Layout: 4 rækker × 2 kolonner (kan rumme op til 8 agent-niveauer)
    n_cols = 2
    n_rows = (n_panels + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(10, 2.5 * n_rows),
                              sharex=True)
    axes_flat = axes.flatten() if n_panels > 1 else [axes]

    for idx, n_agents in enumerate(n_agents_levels):
        ax = axes_flat[idx]
        panel_data = agg[agg["n_agents"] == n_agents]

        for disc in DISCIPLINES:
            disc_data = panel_data[panel_data["discipline"] == disc].sort_values("day")
            ax.plot(disc_data["day"], disc_data["queue_length"],
                    label=disc, color=COLORS[disc], linewidth=1.2)

        ax.set_title(f"Agents = {n_agents}", fontsize=10)
        ax.set_ylabel("Avg queue length")
        ax.grid(True, alpha=0.3)
        if idx >= n_panels - n_cols:
            ax.set_xlabel("Simulation day")

    # Skjul ubrugte subplots
    for idx in range(n_panels, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 1.01), ncol=4, frameon=False)

    fig.suptitle(title, y=1.03, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.98])

    out = RESULTS_DIR / filename
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Figur 7: Queue length, Capacity utilisation, % cases closed
# =============================================================================

def make_fig7():
    """Replika af artiklens Fig. 7 (s. 29)."""
    fig, axes = plt.subplots(3, 2, figsize=(10, 11), sharex=True)

    metrics = [
        ("avg_queue_length", "Average queue length"),
        ("avg_capacity_utilisation", "Average % capacity utilisation"),
        ("percent_cases_closed", "% cases closed"),
    ]

    for row, (metric, ylabel) in enumerate(metrics):
        for col, sla in enumerate(SLA_ORDER):
            ax = axes[row, col]
            plot_metric_panel(ax, metric, ylabel, sla)
            if row == 0:
                ax.set_title(sla, fontsize=11)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 0.98), ncol=4, frameon=False)

    fig.suptitle("Figure 7: Queue length, capacity utilisation, and cases closed",
                 y=1.02, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out = RESULTS_DIR / "fig7_queue_util_closed.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Figur 8: Ventetid og case resolution time
# =============================================================================

def make_fig8():
    """
    Replika af artiklens Fig. 8 (s. 30).

    2 rækker × 2 kolonner:
        Øverste: average waiting time in queue
        Nederste: average case resolution time
    """
    has_resolution = HAS_RESOLUTION_TIME

    n_rows = 2 if has_resolution else 1
    fig, axes = plt.subplots(n_rows, 2, figsize=(10, 4 * n_rows),
                              sharex=True, squeeze=False)

    # Øverste række: waiting time
    for col, sla in enumerate(SLA_ORDER):
        ax = axes[0, col]
        plot_metric_panel(ax, "avg_waiting_time_days",
                          "Average time waiting\nin queue (days)", sla)
        ax.set_title(sla, fontsize=11)

    # Nederste række: case resolution time (hvis data er tilgængelig)
    if has_resolution:
        for col, sla in enumerate(SLA_ORDER):
            ax = axes[1, col]
            plot_metric_panel(ax, "avg_case_resolution_time_days",
                              "Average case resolution\ntime (days)", sla)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 0.98), ncol=4, frameon=False)

    title = "Figure 8: Waiting time and case resolution time"
    if not has_resolution:
        title += " (waiting time only — resolution time data missing)"
    fig.suptitle(title, y=1.02, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out = RESULTS_DIR / "fig8_waiting_and_resolution.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Figur 9: Individual NPS og Organisation NPS
# =============================================================================

def make_fig9():
    """Replika af artiklens Fig. 9 (s. 31)."""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True)

    for col, sla in enumerate(SLA_ORDER):
        ax = axes[0, col]
        plot_metric_panel(ax, "avg_individual_nps",
                          "Avg. simulated individual NPS\nresponse after case closure",
                          sla)
        ax.set_title(sla, fontsize=11)

    for col, sla in enumerate(SLA_ORDER):
        ax = axes[1, col]
        plot_metric_panel(ax, "organisation_nps", "Simulated NPS (%)", sla)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 0.98), ncol=4, frameon=False)

    fig.suptitle("Figure 9: Simulated individual NPS response + organisation NPS",
                 y=1.02, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out = RESULTS_DIR / "fig9_nps.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Figur 10: % cases closed i sidste 335 dage (robusthedstjek)
# =============================================================================

def make_fig10():
    """
    Replika af artiklens Fig. 10 (s. 31).

    Efter ekskludering af første 30 dages burn-in: % sager lukket for sager
    der ankom i dag 30-365.
    """
    if not HAS_LAST_335:
        print("  [SKIP] fig10: percent_cases_closed_last_335 findes ikke i data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

    for col, sla in enumerate(SLA_ORDER):
        ax = axes[col]
        plot_metric_panel(ax, "percent_cases_closed_last_335",
                          "% cases closed\n(only cases from the last 335\nsimulated days)",
                          sla)
        ax.set_title(sla, fontsize=11)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 1.02), ncol=4, frameon=False)

    fig.suptitle("Figure 10: % cases closed in last 335 days (robustness check)",
                 y=1.10, fontsize=11)
    fig.tight_layout()

    out = RESULTS_DIR / "fig10_closed_last_335.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Ekstra: Summary plot med alle 6 metrics i ét overblik
# =============================================================================

def make_summary():
    """Bonus: 6-metric overblik for no-SLA betingelsen."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)

    metrics = [
        ("avg_queue_length", "Avg queue length"),
        ("avg_capacity_utilisation", "Avg % capacity utilisation"),
        ("percent_cases_closed", "% cases closed"),
        ("avg_waiting_time_days", "Avg waiting time (days)"),
        ("avg_individual_nps", "Avg individual NPS"),
        ("organisation_nps", "Organisation NPS (%)"),
    ]

    for idx, (metric, ylabel) in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]
        plot_metric_panel(ax, metric, ylabel, "None")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 0.98), ncol=4, frameon=False)

    fig.suptitle("All-metrics summary (no SLA)", y=1.01, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out = RESULTS_DIR / "summary_all_metrics.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print(f"Loaded {len(df)} simulation runs from {CSV_PATH.name}")
    print(f"Conditions: {df.groupby(['discipline','n_agents','sla_label']).ngroups}")
    print(f"  HAS_RESOLUTION_TIME: {HAS_RESOLUTION_TIME}")
    print(f"  HAS_LAST_335:        {HAS_LAST_335}")
    print(f"  HAS_DAILY:           {HAS_DAILY}")
    print()

    make_fig5_or_6("None", "fig5_daily_queue_no_sla.pdf",
                    "Figure 5: Average daily queue length (no SLA)")
    make_fig5_or_6("SLA = 60 hours", "fig6_daily_queue_sla60.pdf",
                    "Figure 6: Average daily queue length (SLA = 60 hours)")
    make_fig7()
    make_fig8()
    make_fig9()
    make_fig10()
    make_summary()

    print("\nAll plots generated.")
