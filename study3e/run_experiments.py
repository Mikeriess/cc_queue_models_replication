"""
Experiment runner for Study 3e — Multinomial-shape sensitivity for
rank-binned NPS prioritisation.

Sweeps the target multinomial parameter f = mass at bins {7, 8} while
holding the rest of the simulation pipeline fixed. Mode of the target
held at 7.5 (symmetric in 7 and 8); remainder uniform on the other 9
bins. ρ axis reduced to {0.0, 0.5, 1.0} since Study 3d already mapped
five ρ levels.

Design:
    NPS_BINNED:        9 (f) × 3 (ρ) × 100 reps = 2,700 runs
    LRTF, SRTF, NPS:   1 × 3 × 100 reps each = 900 runs
                       (ρ-dependent but f-invariant — run once per ρ)
    FCFS:              1 × 3 × 100 reps = 300 runs
                       (also ρ-invariant in expectation, kept for paired
                       seeding consistency with prior studies)
    Total: 3,900 runs
"""

import argparse
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd

from simulation import run_single_simulation


# =============================================================================
# EXPERIMENT DESIGN
# =============================================================================

DISCIPLINES_NON_FCFS = ["LRTF", "SRTF", "NPS"]
RHO_LEVELS = [0.0, 0.5, 1.0]
RHO_IDX_MAP = {0.0: 0, 0.5: 2, 1.0: 4}  # match study3d/3c rho_idx for paired seeding
F_LEVELS = [0.00, 0.05, 0.10, 0.145, 0.20, 0.30, 0.50, 0.80, 1.00]
SAMPLING_MODES = ["hard"]
AGENT_LEVELS = [6]
NPS_INTERCEPT = 10.22  # paper baseline

N_REPLICATIONS = 100
D_END = 365


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    configs = []

    # NPS_BINNED across all (f, ρ)
    for rho in RHO_LEVELS:
        rho_idx = RHO_IDX_MAP[rho]
        for f in F_LEVELS:
            for mode in SAMPLING_MODES:
                for n_agents in AGENT_LEVELS:
                    for rep in range(1, n_replications + 1):
                        configs.append({
                            "discipline": "NPS_BINNED",
                            "rho": rho,
                            "rho_idx": rho_idx,
                            "sampling_mode": mode,
                            "n_agents": n_agents,
                            "nps_intercept": NPS_INTERCEPT,
                            "sla_hours": None,
                            "replication": rep,
                            "d_end": d_end,
                            "target_f": f,
                        })

    # Reference disciplines: independent of f, run once per (ρ, rep).
    for rho in RHO_LEVELS:
        rho_idx = RHO_IDX_MAP[rho]
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
                            # target_f intentionally absent → NaN in output
                        })

    # FCFS: ρ-invariant in expectation but kept across ρ for paired seeding
    for rho in RHO_LEVELS:
        rho_idx = RHO_IDX_MAP[rho]
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

    print("Study 3e — Multinomial-shape sensitivity")
    print(f"  Disciplines:       FCFS + {DISCIPLINES_NON_FCFS} + NPS_BINNED")
    print(f"  ρ levels:          {RHO_LEVELS}")
    print(f"  f levels:          {F_LEVELS}")
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
            if (i + 1) % 200 == 0 or (i + 1) == total:
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
                "target_f": r.get("target_f"),
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
    print("\n" + "=" * 88)
    print("STUDY 3e: ORG NPS BY (DISCIPLINE × f × ρ)")
    print("=" * 88)

    rhos = sorted(df["rho"].unique())
    f_levels = sorted([f for f in df["target_f"].dropna().unique()])

    for rho in rhos:
        print(f"\n>>> ρ = {rho}")
        header = f"{'f':>8} | " + " | ".join(f"{d:>10}" for d in
                                              ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"])
        print(header)
        print("-" * len(header))
        for f in f_levels:
            row = [f"{f:>8.3f}"]
            for disc in ["FCFS", "LRTF", "SRTF", "NPS"]:
                sub = df[(df["discipline"] == disc) & (df["rho"] == rho)]
                if len(sub) > 0:
                    row.append(f"{sub['organisation_nps'].mean():>+10.3f}")
                else:
                    row.append("       n/a")
            sub = df[(df["discipline"] == "NPS_BINNED")
                     & (df["rho"] == rho)
                     & (df["target_f"].round(3) == round(f, 3))]
            if len(sub) > 0:
                row.append(f"{sub['organisation_nps'].mean():>+10.3f}")
            else:
                row.append("       n/a")
            print(" | ".join(row))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Study 3e Monte Carlo experiments")
    parser.add_argument("--quick", action="store_true",
                        help="5 replications × 60 days (smoke pipeline)")
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
