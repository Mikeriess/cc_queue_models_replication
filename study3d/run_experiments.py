"""
Experiment runner for Study 3d — Rank-binned NPS Prediction.

Tests the new NPS_BINNED discipline against FCFS / LRTF / SRTF / NPS at
the paper's baseline calibration (intercept = 10.22, no topic-aware
prediction). The new discipline applies a rank-preserving bin mapping
that forces the predicted NPS distribution to match the empirical
multinomial supplied by the paper authors (n = 1,898).

Design:
    5 disciplines × 5 ρ × 1 mode (hard) × 1 agent (6) × 1 intercept
    × 100 replications.

    LRTF, SRTF, NPS, NPS_BINNED: 4 × 5 × 100 = 2,000 runs
    FCFS:                       1 × 5 × 100 =   500 runs (ρ-invariant
                                                  but kept for paired seeding)
    Total:                                     2,500 runs
"""

import argparse
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd

from simulation import run_single_simulation, NPS_PRED_INTERCEPT


# =============================================================================
# EXPERIMENT DESIGN
# =============================================================================

DISCIPLINES_NON_FCFS = ["LRTF", "SRTF", "NPS", "NPS_BINNED"]
RHO_LEVELS = [0.0, 0.22, 0.5, 0.85, 1.0]
SAMPLING_MODES = ["hard"]
AGENT_LEVELS = [6]
NPS_INTERCEPT = 10.22  # paper baseline

N_REPLICATIONS = 100
D_END = 365


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    configs = []

    # LRTF, SRTF, NPS, NPS_BINNED across all ρ
    for rho_idx, rho in enumerate(RHO_LEVELS):
        for mode in SAMPLING_MODES:
            for discipline in DISCIPLINES_NON_FCFS:
                for n_agents in AGENT_LEVELS:
                    for rep in range(1, n_replications + 1):
                        configs.append({
                            "discipline": discipline,
                            "rho": rho,
                            "rho_idx": rho_idx,
                            "sampling_mode": mode,
                            "n_agents": n_agents,
                            "nps_intercept": NPS_INTERCEPT,
                            "sla_hours": None,
                            "replication": rep,
                            "d_end": d_end,
                        })

    # FCFS: invariant but kept for paired seeding
    for rho_idx, rho in enumerate(RHO_LEVELS):
        for mode in SAMPLING_MODES:
            for n_agents in AGENT_LEVELS:
                for rep in range(1, n_replications + 1):
                    configs.append({
                        "discipline": "FCFS",
                        "rho": rho,
                        "rho_idx": rho_idx,
                        "sampling_mode": mode,
                        "n_agents": n_agents,
                        "nps_intercept": NPS_INTERCEPT,
                        "sla_hours": None,
                        "replication": rep,
                        "d_end": d_end,
                    })

    return configs


def run_experiments(n_workers: int = None,
                     n_replications: int = N_REPLICATIONS,
                     d_end: int = D_END,
                     output_file: str = "results/results.csv") -> pd.DataFrame:
    if n_workers is None:
        n_workers = cpu_count()

    configs = generate_experiment_configs(n_replications, d_end)
    total = len(configs)

    print("Study 3d — Rank-binned NPS Prediction")
    print(f"  Disciplines:       FCFS + {DISCIPLINES_NON_FCFS}")
    print(f"  ρ levels:          {RHO_LEVELS}")
    print(f"  Sampling modes:    {SAMPLING_MODES}")
    print(f"  Agents:            {AGENT_LEVELS}")
    print(f"  NPS intercept:     {NPS_INTERCEPT}")
    print(f"  Replications:      {n_replications}")
    print(f"  Total runs:        {total}")
    print(f"  CPU cores:         {n_workers}")
    print()

    start_time = time.time()
    print(f"Starting {total} simulations...")

    with Pool(processes=n_workers) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(run_single_simulation, configs)):
            results.append(result)
            if (i + 1) % 100 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                pct = (i + 1) / total * 100
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (total - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{total}] {pct:.1f}% — "
                      f"{elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")

    total_time = time.time() - start_time
    print(f"\nDone! {total_time:.1f}s ({total_time/60:.1f} min)")

    daily_records = []
    aggregate_records = []

    for r in results:
        daily_q = r.pop("_daily_queue_lengths")
        aggregate_records.append(r)
        for day, qlen in enumerate(daily_q):
            daily_records.append({
                "discipline": r["discipline"],
                "rho": r["rho"],
                "n_agents": r["n_agents"],
                "replication": r["replication"],
                "day": day,
                "queue_length": qlen,
            })

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(aggregate_records)
    df.to_csv(output_file, index=False)
    print(f"\nResults saved: {output_file}")

    out_path = Path(output_file)
    daily_file = out_path.with_name("daily_queue_lengths.csv.gz")
    daily_df = pd.DataFrame(daily_records)
    daily_df.to_csv(daily_file, index=False)
    print(f"Daily queue lengths: {daily_file}")
    print(f"  ({len(daily_df):,} rows, ~{daily_file.stat().st_size / 1e6:.1f} MB)")

    return df


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("STUDY 3d: SEGMENT PROPORTIONS BY DISCIPLINE × ρ")
    print("=" * 80)

    rhos = sorted(df["rho"].unique())

    for metric_name, col in [
        ("Avg individual NPS", "avg_individual_nps"),
        ("Organisation NPS",   "organisation_nps"),
        ("% detractors",       "percent_detractors"),
        ("% passives",         "percent_passives"),
        ("% promoters",        "percent_promoters"),
    ]:
        print(f"\n>>> {metric_name}")
        header = f"{'Discipline':>12} | " + " | ".join(f"ρ={r:.2f}" for r in rhos)
        print(header)
        print("-" * len(header))
        for disc in ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]:
            row = []
            for rho in rhos:
                sub = df[(df["discipline"] == disc) & (df["rho"] == rho)]
                if len(sub) > 0:
                    row.append(f"{sub[col].mean():>+7.4f}")
                else:
                    row.append("   n/a ")
            print(f"{disc:>12} | " + " | ".join(row))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Study 3d Monte Carlo experiments")
    parser.add_argument("--quick", action="store_true", help="5 reps, 60 days")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--replications", type=int, default=N_REPLICATIONS)
    parser.add_argument("--days", type=int, default=D_END)
    parser.add_argument("--output", type=str, default="results/results.csv")
    args = parser.parse_args()

    if args.quick:
        print("*** QUICK MODE ***\n")
        df = run_experiments(args.workers, 5, 60, args.output)
    else:
        df = run_experiments(args.workers, args.replications, args.days, args.output)

    print_summary(df)
