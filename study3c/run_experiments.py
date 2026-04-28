"""
Eksperimentkørsel for Study 3c — Multi-Predictor NPS Model.

Tilføjer topic_aware (bool) som eksperimentel faktor til Study 3b's design.
Når topic_aware=True bruger NPS-prædiktionen NPS_PRED_TOPIC_COEFS, hvilket
bryder den monotone afhængighed af predicted_throughput og giver
|NPS_hat − 7.5| en anden rangorden end LRTF.

Faktorielt design:
    2 topic_aware × 2 intercepts × 5 ρ × 1 mode × 3 discipliner × 1 agent
    × 100 reps = 6.000 simulationskørsler.

    Vi holder os til 6 agenter (kritisk load) og hard mode (Study 3 viste at
    soft bekræfter samme mønster). De to intercept-niveauer (10.22, 8.0)
    undersøger interaktionen mellem topic-awareness og Study 3b's
    transition-mekanisme.

Brug:
    python run_experiments.py                  # Fuldt eksperiment
    python run_experiments.py --quick          # 5 reps, 60 dage
"""

import argparse
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd

from simulation import run_single_simulation, NPS_PRED_INTERCEPT


# =============================================================================
# EKSPERIMENTELT DESIGN
# =============================================================================

# Study 3c-faktorer
TOPIC_AWARE_LEVELS = [False, True]
INTERCEPT_LEVELS = [10.22, 8.0]    # baseline + Study 3b plateau-zone
RHO_LEVELS = [0.0, 0.22, 0.5, 0.85, 1.0]
SAMPLING_MODES = ["hard"]
DISCIPLINES = ["LRTF", "NPS"]      # FCFS tilføjes separat (invariant)
AGENT_LEVELS = [6]

N_REPLICATIONS = 100
D_END = 365


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    """
    Generér alle konfigurationer.

    LRTF og NPS køres for alle (topic_aware × intercept × ρ)-kombinationer.
    FCFS er invariant ift. alle tre faktorer, så den køres kun for ét
    (topic_aware, intercept) — men alle ρ-niveauer for at matche paret seeding.
    """
    configs = []

    # LRTF og NPS: fuldt grid
    for topic_aware in TOPIC_AWARE_LEVELS:
        for nps_int in INTERCEPT_LEVELS:
            for rho_idx, rho in enumerate(RHO_LEVELS):
                for mode in SAMPLING_MODES:
                    for discipline in DISCIPLINES:
                        for n_agents in AGENT_LEVELS:
                            for rep in range(1, n_replications + 1):
                                configs.append({
                                    "topic_aware": topic_aware,
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

    # FCFS: kun ét (topic_aware, intercept) — alle ρ for seed-paritet
    fcfs_topic_aware = TOPIC_AWARE_LEVELS[0]
    fcfs_intercept = INTERCEPT_LEVELS[0]
    for rho_idx, rho in enumerate(RHO_LEVELS):
        for mode in SAMPLING_MODES:
            for n_agents in AGENT_LEVELS:
                for rep in range(1, n_replications + 1):
                    configs.append({
                        "topic_aware": fcfs_topic_aware,
                        "nps_intercept": fcfs_intercept,
                        "rho": rho,
                        "rho_idx": rho_idx,
                        "sampling_mode": mode,
                        "discipline": "FCFS",
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

    print("Study 3c — Multi-Predictor NPS Model")
    print(f"  topic_aware:       {TOPIC_AWARE_LEVELS}")
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
                "topic_aware": r["topic_aware"],
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
    """Print hovedresultat: NPS − LRTF advantage opdelt på topic_aware."""
    print("\n" + "=" * 78)
    print("STUDY 3c: NPS − LRTF ADVANTAGE (individual NPS)")
    print("=" * 78)

    rhos = sorted(df["rho"].unique())
    intercepts = sorted(df["nps_intercept"].unique(), reverse=True)

    for topic_aware in [False, True]:
        print(f"\n>>> topic_aware = {topic_aware}")
        header = f"{'Intercept':>10} | " + " | ".join(f"ρ={r:.2f}" for r in rhos)
        print(header)
        print("-" * len(header))

        for nps_int in intercepts:
            row = []
            for rho in rhos:
                nps_sub = df[(df["topic_aware"] == topic_aware)
                              & (df["nps_intercept"] == nps_int)
                              & (df["rho"] == rho)
                              & (df["discipline"] == "NPS")]
                lrtf_sub = df[(df["topic_aware"] == topic_aware)
                               & (df["nps_intercept"] == nps_int)
                               & (df["rho"] == rho)
                               & (df["discipline"] == "LRTF")]
                if len(nps_sub) > 0 and len(lrtf_sub) > 0:
                    adv = nps_sub["avg_individual_nps"].mean() - lrtf_sub["avg_individual_nps"].mean()
                    row.append(f"{adv:+.4f}")
                else:
                    row.append("   n/a ")
            print(f"{nps_int:>10.2f} | " + " | ".join(row))

    # Diagnostik: varians af predicted_nps
    print("\n" + "=" * 78)
    print("DIAGNOSTIK: Var(predicted_nps) pr. (topic_aware × intercept)")
    print("=" * 78)
    print(f"{'topic_aware':>12} | {'intercept':>10} | {'Var':>10}")
    print("-" * 40)
    for topic_aware in [False, True]:
        for nps_int in intercepts:
            sub = df[(df["topic_aware"] == topic_aware)
                      & (df["nps_intercept"] == nps_int)]
            if len(sub) > 0:
                v = sub["predicted_nps_variance"].mean()
                print(f"{str(topic_aware):>12} | {nps_int:>10.2f} | {v:>10.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kør Study 3c Monte Carlo eksperimenter"
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
