"""
Eksperimentkørsel for Study 3b — Counterfactual Probe.

Tilføjer NPS_PRED_INTERCEPT som eksperimentel faktor til Study 3's design.
Når interceptet sænkes, krydser NPS_hat-fordelingen 7.5-midtpunktet, og
|NPS_hat − 7.5| bliver V-formet → NPS-prioritering giver en anden rangorden
end LRTF.

Fuldt faktorielt design:
    4 intercept-niveauer × 5 ρ × 1 mode (hard) × 3 discipliner × 1 agent-niveau
    × 100 replikationer = 6.000 simulationskørsler.

    Vi bruger kun hard mode og 6 agenter (Study 3 viste at soft mode og
    agents 5/7 bekræfter det samme mønster, men ikke tilføjer ny indsigt
    for dette specifikke spørgsmål).

Brug:
    python run_experiments.py                  # Fuldt eksperiment
    python run_experiments.py --quick          # 5 reps, 60 dage
"""

import argparse
import time
from itertools import product
from multiprocessing import Pool, cpu_count
from pathlib import Path

import numpy as np
import pandas as pd

from simulation import run_single_simulation, NPS_PRED_INTERCEPT


# =============================================================================
# EKSPERIMENTELT DESIGN
# =============================================================================

# Study 3b tilføjer NPS_PRED_INTERCEPT som faktor
INTERCEPT_LEVELS = [10.22, 9.0, 8.0, 7.5]

RHO_LEVELS = [0.00, 0.22, 0.50, 0.85, 1.00]
SAMPLING_MODES = ["hard"]           # kun hard mode i Study 3b
DISCIPLINES = ["FCFS", "LRTF", "NPS"]
AGENT_LEVELS = [6]                  # fikseret til 6 (kritisk load)

N_REPLICATIONS = 100
D_END = 365


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    """Generér alle konfigurationer med intercept som ny faktor."""
    configs = []
    for nps_int in INTERCEPT_LEVELS:
        for rho_idx, rho in enumerate(RHO_LEVELS):
            for mode in SAMPLING_MODES:
                for discipline in DISCIPLINES:
                    for n_agents in AGENT_LEVELS:
                        for rep in range(1, n_replications + 1):
                            configs.append({
                                "nps_intercept": nps_int,
                                "rho": rho,
                                "rho_idx": rho_idx,
                                "sampling_mode": mode,
                                "discipline": discipline,
                                "n_agents": n_agents,
                                "sla_hours": None,
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

    print("Study 3b — Counterfactual Probe")
    print(f"  NPS intercepts:    {INTERCEPT_LEVELS}")
    print(f"  ρ-niveauer:        {RHO_LEVELS}")
    print(f"  Sampling modes:    {SAMPLING_MODES}")
    print(f"  Discipliner:       {DISCIPLINES}")
    print(f"  Agent-niveauer:    {AGENT_LEVELS}")
    print(f"  Replikationer:     {n_replications}")
    print(f"  Total runs:        {total}")
    print(f"  CPU-kerner:        {n_workers}")
    print()

    start_time = time.time()
    print(f"Starter {total} simulationer...")

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
    print(f"\nFærdig! {total_time:.1f}s ({total_time/60:.1f} min)")

    # Separér aggregerede metrikker fra daglige tidsserier
    daily_records = []
    aggregate_records = []

    for r in results:
        daily_q = r.pop("_daily_queue_lengths")
        aggregate_records.append(r)
        for day, qlen in enumerate(daily_q):
            daily_records.append({
                "nps_intercept": r["nps_intercept"],
                "rho": r["rho"],
                "discipline": r["discipline"],
                "n_agents": r["n_agents"],
                "replication": r["replication"],
                "day": day,
                "queue_length": qlen,
            })

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(aggregate_records)
    df.to_csv(output_file, index=False)
    print(f"\nResultater gemt i: {output_file}")

    out_path = Path(output_file)
    daily_file = out_path.with_name("daily_queue_lengths.csv.gz")
    daily_df = pd.DataFrame(daily_records)
    daily_df.to_csv(daily_file, index=False)
    print(f"Daglige kølængder gemt i: {daily_file}")
    print(f"  ({len(daily_df):,} rækker, ~{daily_file.stat().st_size / 1e6:.1f} MB)")

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print hovedresultat: NPS vs LRTF som funktion af intercept og ρ."""
    print("\n" + "=" * 70)
    print("STUDY 3b: NPS − LRTF ADVANTAGE som funktion af intercept × ρ")
    print("=" * 70)

    for nps_int in INTERCEPT_LEVELS:
        print(f"\n--- NPS intercept = {nps_int} ---")
        sub = df[df["nps_intercept"] == nps_int]

        nps_means = sub[sub["discipline"] == "NPS"].groupby("rho")["avg_individual_nps"].mean()
        lrtf_means = sub[sub["discipline"] == "LRTF"].groupby("rho")["avg_individual_nps"].mean()
        fcfs_means = sub[sub["discipline"] == "FCFS"].groupby("rho")["avg_individual_nps"].mean()

        for rho in sorted(sub["rho"].unique()):
            adv_lrtf = nps_means[rho] - lrtf_means[rho]
            adv_fcfs = nps_means[rho] - fcfs_means[rho]
            print(f"  ρ={rho:.2f}: NPS−LRTF={adv_lrtf:+.4f}  NPS−FCFS={adv_fcfs:+.4f}  "
                  f"NPS={nps_means[rho]:.4f}  LRTF={lrtf_means[rho]:.4f}  FCFS={fcfs_means[rho]:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kør Study 3b Monte Carlo eksperimenter"
    )
    parser.add_argument("--quick", action="store_true",
                        help="Hurtig test: 5 replikationer, 60 dage")
    parser.add_argument("--workers", type=int, default=None,
                        help="Antal CPU-kerner")
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
