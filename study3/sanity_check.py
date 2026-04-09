"""
Sanity check: verificér at Study 3 ved ρ=0 matcher Study 2.

Kører 30 replikationer af FCFS, 6 agenter, no SLA, ρ=0 i begge sampling modes,
og sammenligner med Study 2 baseline for samme betingelse.
"""
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from simulation import run_single_simulation


def run_rep(params):
    r = run_single_simulation(params)
    r.pop("_daily_queue_lengths")
    return r


def main():
    # Indlæs Study 2 baseline
    s2_path = Path(__file__).parent.parent / "study2" / "results" / "results.csv"
    s2_df = pd.read_csv(s2_path)
    s2_base = s2_df[
        (s2_df["discipline"] == "FCFS")
        & (s2_df["n_agents"] == 6)
        & (s2_df["sla_hours"].isna())
    ]

    print("=" * 60)
    print("Sanity check: ρ=0 vs Study 2 baseline")
    print("=" * 60)
    print(f"\nStudy 2 baseline (FCFS, 6 agenter, no SLA, N={len(s2_base)}):")
    print(f"  queue length:     {s2_base['avg_queue_length'].mean():.2f} ± {s2_base['avg_queue_length'].std():.2f}")
    print(f"  capacity util:    {s2_base['avg_capacity_utilisation'].mean():.4f}")
    print(f"  % closed:         {s2_base['percent_cases_closed'].mean():.4f}")
    print(f"  indiv NPS:        {s2_base['avg_individual_nps'].mean():.4f}")
    print(f"  org NPS:          {s2_base['organisation_nps'].mean():.2f}")
    print()

    for mode in ["hard", "soft"]:
        configs = [
            {
                "discipline": "FCFS",
                "n_agents": 6,
                "sla_hours": None,
                "replication": rep,
                "rho": 0.0,
                "rho_idx": 0,
                "sampling_mode": mode,
                "d_end": 365,
            }
            for rep in range(1, 31)
        ]

        with Pool(8) as pool:
            results = pool.map(run_rep, configs)

        df = pd.DataFrame(results)
        print(f"Study 3 ρ=0 {mode} mode (N=30):")
        print(f"  queue length:     {df['avg_queue_length'].mean():.2f} ± {df['avg_queue_length'].std():.2f}")
        print(f"  capacity util:    {df['avg_capacity_utilisation'].mean():.4f}")
        print(f"  % closed:         {df['percent_cases_closed'].mean():.4f}")
        print(f"  indiv NPS:        {df['avg_individual_nps'].mean():.4f}")
        print(f"  org NPS:          {df['organisation_nps'].mean():.2f}")

        # Sammenligning
        q_pct = abs(df["avg_queue_length"].mean() - s2_base["avg_queue_length"].mean()) / s2_base["avg_queue_length"].mean() * 100
        onps_diff = abs(df["organisation_nps"].mean() - s2_base["organisation_nps"].mean())
        pc_pp = abs(df["percent_cases_closed"].mean() - s2_base["percent_cases_closed"].mean()) * 100

        print(f"\n  vs Study 2:")
        print(f"    queue length: {q_pct:.1f}% forskel")
        print(f"    org NPS:      {onps_diff:.2f} enheder")
        print(f"    % closed:     {pc_pp:.2f}pp")
        print()


if __name__ == "__main__":
    main()
