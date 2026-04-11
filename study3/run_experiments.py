"""
Eksperimentkørsel for Study 3 — The Value of Information.

Fuldt faktorielt design:
    5 ρ-niveauer × 2 sampling modes × 3 discipliner × 3 agent-niveauer
    × 100 replikationer = 9.000 simulationskørsler.

Bruger paret seeding (D6) for variance reduction: arrivals og z_actual er
identiske på tværs af ρ-niveauer, kun ε (noise i z_pred) varierer.

Brug:
    python run_experiments.py                          # Fuldt eksperiment
    python run_experiments.py --quick                  # 5 reps, 60 dage
    python run_experiments.py --workers 24             # Specificér kerner
"""

import argparse
import time
from itertools import product
from multiprocessing import Pool, cpu_count
from pathlib import Path

import numpy as np
import pandas as pd

from simulation import run_single_simulation


# =============================================================================
# EKSPERIMENTELT DESIGN
# =============================================================================

RHO_LEVELS = [0.00, 0.22, 0.50, 0.85, 1.00]
SAMPLING_MODES = ["hard", "soft"]
DISCIPLINES = ["FCFS", "LRTF", "NPS"]
AGENT_LEVELS = [5, 6, 7]
SLA_HOURS = None  # SLA udelades — Study 2 viste at SLA udligner forskelle

N_REPLICATIONS = 100
D_END = 365


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    """
    Generér alle eksperimentelle konfigurationer.

    Rækkefølgen er: ρ (yderst) → mode → discipline → agents → replication.
    """
    configs = []
    for rho_idx, rho in enumerate(RHO_LEVELS):
        for mode in SAMPLING_MODES:
            for discipline in DISCIPLINES:
                for n_agents in AGENT_LEVELS:
                    for rep in range(1, n_replications + 1):
                        configs.append({
                            "rho": rho,
                            "rho_idx": rho_idx,
                            "sampling_mode": mode,
                            "discipline": discipline,
                            "n_agents": n_agents,
                            "sla_hours": SLA_HOURS,
                            "replication": rep,
                            "d_end": d_end,
                        })
    return configs


def run_experiments(n_workers: int = None,
                     n_replications: int = N_REPLICATIONS,
                     d_end: int = D_END,
                     output_file: str = "results/results.csv") -> pd.DataFrame:
    """Kør alle eksperimenter parallelt og gem resultater."""
    if n_workers is None:
        n_workers = cpu_count()

    configs = generate_experiment_configs(n_replications, d_end)
    total = len(configs)

    print("Study 3 — eksperimentelt design:")
    print(f"  ρ-niveauer:        {RHO_LEVELS}")
    print(f"  Sampling modes:    {SAMPLING_MODES}")
    print(f"  Discipliner:       {DISCIPLINES}")
    print(f"  Agent-niveauer:    {AGENT_LEVELS}")
    print(f"  Replikationer:     {n_replications}")
    print(f"  Simuleringsdage:   {d_end}")
    print(f"  Total runs:        {total}")
    print(f"  CPU-kerner:        {n_workers}")
    print()

    est_per_run_sec = 1.5
    est_total = total * est_per_run_sec / n_workers
    print(f"  Estimeret tid:     ~{est_total / 60:.0f} min")
    print()

    start_time = time.time()
    print(f"Starter {total} simulationer på {n_workers} kerner...")

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
    print(f"\nFærdig! Total tid: {total_time:.1f}s ({total_time/60:.1f} min)")

    # Separér aggregerede metrikker fra daglige tidsserier
    daily_records = []
    aggregate_records = []

    for r in results:
        daily_q = r.pop("_daily_queue_lengths")
        aggregate_records.append(r)
        for day, qlen in enumerate(daily_q):
            daily_records.append({
                "rho": r["rho"],
                "sampling_mode": r["sampling_mode"],
                "discipline": r["discipline"],
                "n_agents": r["n_agents"],
                "sla_hours": r["sla_hours"],
                "replication": r["replication"],
                "day": day,
                "queue_length": qlen,
            })

    # Sørg for at output-mappen findes
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Gem aggregerede metrikker
    df = pd.DataFrame(aggregate_records)
    df.to_csv(output_file, index=False)
    print(f"\nAggregerede resultater gemt i: {output_file}")

    # Gem daglige kølængder
    out_path = Path(output_file)
    daily_file = out_path.with_name("daily_queue_lengths.csv.gz")
    daily_df = pd.DataFrame(daily_records)
    daily_df.to_csv(daily_file, index=False)
    print(f"Daglige kølængder gemt i: {daily_file}")
    print(f"  ({len(daily_df):,} rækker, ~{daily_file.stat().st_size / 1e6:.0f} MB)")

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print opsummerende statistik — hovedresultat for Study 3."""
    print("\n" + "=" * 80)
    print("STUDY 3 HOVEDRESULTAT: NPS vs ρ")
    print("=" * 80)

    for mode in SAMPLING_MODES:
        print(f"\n--- Sampling mode: {mode} ---")
        for n_agents in AGENT_LEVELS:
            print(f"\n  Agents = {n_agents}:")
            sub = df[(df["sampling_mode"] == mode) & (df["n_agents"] == n_agents)]

            pivot = sub.pivot_table(
                values="avg_individual_nps",
                index="rho",
                columns="discipline",
                aggfunc="mean",
            )
            print(pivot.to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kør Study 3 Monte Carlo eksperimenter"
    )
    parser.add_argument("--quick", action="store_true",
                        help="Hurtig test: 5 replikationer, 60 dage")
    parser.add_argument("--workers", type=int, default=None,
                        help="Antal CPU-kerner (default: alle)")
    parser.add_argument("--replications", type=int, default=N_REPLICATIONS,
                        help="Antal replikationer pr. betingelse")
    parser.add_argument("--days", type=int, default=D_END,
                        help="Antal dage pr. simulering")
    parser.add_argument("--output", type=str, default="results/results.csv",
                        help="Output CSV-fil")

    args = parser.parse_args()

    if args.quick:
        print("*** QUICK MODE: 5 replikationer, 60 dage ***\n")
        df = run_experiments(
            n_workers=args.workers,
            n_replications=5,
            d_end=60,
            output_file=args.output,
        )
    else:
        df = run_experiments(
            n_workers=args.workers,
            n_replications=args.replications,
            d_end=args.days,
            output_file=args.output,
        )

    print_summary(df)
