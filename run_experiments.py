"""
Eksperimentkørsel for reproduktion af Study 2 fra:
"Customer-service queuing based on predicted loyalty outcomes"
(Riess & Scholderer, 2026)

Fuldt faktorielt design: 4 kødiscipliner × 7 agent-niveauer × 2 SLA-niveauer
= 56 betingelser × 100 replikationer = 5600 simulationskørsler.

Bruger multiprocessing for parallel kørsel.
Resultater gemmes i CSV-format til videre analyse.

Brug:
    python run_experiments.py                  # Kør fuldt eksperiment
    python run_experiments.py --quick          # Hurtig test (5 replikationer)
    python run_experiments.py --workers 8      # Specificér antal CPU-kerner
"""

import os
import sys
import time
import argparse
from multiprocessing import Pool, cpu_count
from itertools import product

import pandas as pd
import numpy as np

from simulation import run_single_simulation


# =============================================================================
# EKSPERIMENTELT DESIGN (sektion 3.1.1, s. 12-13)
# =============================================================================

# Faktor 1: Kødisciplin (4 niveauer)
DISCIPLINES = ["FCFS", "SRTF", "LRTF", "NPS"]

# Faktor 2: Antal agenter (7 niveauer)
# Artiklen: 3, 4, 5, 6, 7, 8, 9
AGENT_LEVELS = [3, 4, 5, 6, 7, 8, 9]

# Faktor 3: Service level constraint (2 niveauer)
# None = ingen SLA, 60 = 60 timers hard ceiling
SLA_LEVELS = [None, 60.0]

# Antal replikationer pr. betingelse
N_REPLICATIONS = 100

# Simuleringsperiode i dage
D_END = 365


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    """
    Generér alle eksperimentelle konfigurationer.

    Fuldt faktorielt design: alle kombinationer af de tre faktorer,
    ganget med antal replikationer.

    Returns:
        Liste af parameter-dicts til run_single_simulation()
    """
    configs = []
    for discipline, n_agents, sla_hours in product(DISCIPLINES, AGENT_LEVELS, SLA_LEVELS):
        for rep in range(1, n_replications + 1):
            configs.append({
                "discipline": discipline,
                "n_agents": n_agents,
                "sla_hours": sla_hours,
                "replication": rep,
                "d_end": d_end,
            })
    return configs


def run_experiments(n_workers: int = None, n_replications: int = N_REPLICATIONS,
                     d_end: int = D_END, output_file: str = "results.csv") -> pd.DataFrame:
    """
    Kør alle eksperimenter parallelt og gem resultater.

    Args:
        n_workers: Antal CPU-kerner (default: alle tilgængelige)
        n_replications: Antal replikationer pr. betingelse
        d_end: Antal dage pr. simulering
        output_file: Filnavn for CSV-output

    Returns:
        DataFrame med alle resultater
    """
    if n_workers is None:
        n_workers = cpu_count()

    configs = generate_experiment_configs(n_replications, d_end)
    total = len(configs)

    print(f"Eksperimentelt design:")
    print(f"  Kødiscipliner:    {DISCIPLINES}")
    print(f"  Agent-niveauer:   {AGENT_LEVELS}")
    print(f"  SLA-niveauer:     {SLA_LEVELS}")
    print(f"  Replikationer:    {n_replications}")
    print(f"  Simuleringsperiode: {d_end} dage")
    print(f"  Total antal kørsler: {total}")
    print(f"  CPU-kerner: {n_workers}")
    print()

    # Estimér tid
    est_per_run_sec = 3.5  # estimat fra planen
    est_total_sec = total * est_per_run_sec / n_workers
    est_minutes = est_total_sec / 60
    print(f"  Estimeret tid: ~{est_minutes:.0f} minutter ({est_total_sec/3600:.1f} timer)")
    print()

    # Kør parallelt
    start_time = time.time()
    print(f"Starter {total} simulationer på {n_workers} kerner...")

    with Pool(processes=n_workers) as pool:
        # Brug imap_unordered for bedre progress-feedback
        results = []
        for i, result in enumerate(pool.imap_unordered(run_single_simulation, configs)):
            results.append(result)
            # Progress-output hvert 100. kørsel
            if (i + 1) % 100 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                pct = (i + 1) / total * 100
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{total}] {pct:.1f}% — "
                      f"{elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")

    total_time = time.time() - start_time
    print(f"\nFærdig! Total tid: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Gennemsnitlig tid pr. kørsel: {total_time * n_workers / total:.2f}s")

    # Separér aggregerede metrikker fra rå tidsserier
    # Tidsserierne (daily_queue_lengths) gemmes i en separat fil, da de er for
    # store til at passe pænt ind i den aggregerede CSV.
    daily_records = []
    aggregate_records = []

    for r in results:
        daily_q = r.pop("_daily_queue_lengths")
        aggregate_records.append(r)

        # Udfold daglige kølængder til long-format rækker
        for day, qlen in enumerate(daily_q):
            daily_records.append({
                "discipline": r["discipline"],
                "n_agents": r["n_agents"],
                "sla_hours": r["sla_hours"],
                "replication": r["replication"],
                "day": day,
                "queue_length": qlen,
            })

    # Gem aggregerede metrikker
    df = pd.DataFrame(aggregate_records)
    df.to_csv(output_file, index=False)
    print(f"\nAggregerede resultater gemt i: {output_file}")

    # Gem daglige kølængder (til Fig. 5 og 6)
    # Filnavn afledes af output_file: results.csv → daily_queue_lengths.csv
    from pathlib import Path
    out_path = Path(output_file)
    daily_file = out_path.with_name(
        out_path.stem.replace("results", "daily_queue_lengths") + out_path.suffix
    )
    if daily_file.name == out_path.name:  # fallback hvis replace ikke virkede
        daily_file = out_path.with_stem(out_path.stem + "_daily")

    daily_df = pd.DataFrame(daily_records)
    daily_df.to_csv(daily_file, index=False)
    print(f"Daglige kølængder gemt i: {daily_file}")
    print(f"  ({len(daily_df):,} rækker, ~{daily_file.stat().st_size / 1e6:.0f} MB)")

    return df


def print_summary(df: pd.DataFrame) -> None:
    """
    Print opsummerende statistik svarende til artiklens resultater.

    Beregner gennemsnit og 95% konfidensintervaller for hver betingelse,
    svarende til Fig. 7-9 i artiklen.
    """
    print("\n" + "=" * 80)
    print("OPSUMMERENDE RESULTATER")
    print("=" * 80)

    # Gruppér efter betingelse (discipline × n_agents × sla)
    group_cols = ["discipline", "n_agents", "sla_hours"]
    metrics = ["avg_queue_length", "avg_waiting_time_days",
               "avg_capacity_utilisation", "percent_cases_closed",
               "avg_individual_nps", "organisation_nps"]

    summary = df.groupby(group_cols)[metrics].agg(["mean", "std", "count"])

    # Beregn 95% CI
    for metric in metrics:
        summary[(metric, "ci95")] = (
            1.96 * summary[(metric, "std")] / np.sqrt(summary[(metric, "count")])
        )

    # Print per metric
    for metric in metrics:
        print(f"\n--- {metric} ---")
        print(f"{'Discipline':<10} {'Agents':<8} {'SLA':<8} "
              f"{'Mean':>12} {'±95%CI':>12}")
        print("-" * 58)

        for (disc, agents, sla), row in summary.iterrows():
            mean_val = row[(metric, "mean")]
            ci_val = row[(metric, "ci95")]
            sla_str = "None" if sla == "None" or sla is None else f"{sla:.0f}h"
            print(f"{disc:<10} {agents:<8} {sla_str:<8} "
                  f"{mean_val:>12.4f} {ci_val:>12.4f}")

    # Print NPS-resultater (svarende til artiklens hovedresultat)
    print(f"\n{'='*80}")
    print("HOVEDRESULTAT: Organisation NPS per kødisciplin")
    print(f"{'='*80}")

    nps_by_disc = df.groupby("discipline")["organisation_nps"].agg(["mean", "std", "count"])
    nps_by_disc["ci95"] = 1.96 * nps_by_disc["std"] / np.sqrt(nps_by_disc["count"])

    for disc, row in nps_by_disc.iterrows():
        print(f"  {disc:<6}: {row['mean']:>8.2f} ± {row['ci95']:.2f}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kør Monte Carlo kø-simuleringseksperimenter"
    )
    parser.add_argument("--quick", action="store_true",
                        help="Hurtig test med 5 replikationer og 60 dage")
    parser.add_argument("--workers", type=int, default=None,
                        help="Antal CPU-kerner (default: alle)")
    parser.add_argument("--replications", type=int, default=N_REPLICATIONS,
                        help="Antal replikationer pr. betingelse (default: 100)")
    parser.add_argument("--days", type=int, default=D_END,
                        help="Antal dage pr. simulering (default: 365)")
    parser.add_argument("--output", type=str, default="results.csv",
                        help="Output CSV-fil (default: results.csv)")

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
