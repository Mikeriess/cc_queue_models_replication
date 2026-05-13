"""
Experiment runner for Study 4b — Sinusoidal arrivals × topic-aware NPS
predictor.

Forks Study 4's runner. Adds ρ_topic ∈ {0.0, 0.5, 1.0} as a new sweep
axis. ρ_topic = 0.0 cells are paired-seeded with Study 4 (same arrivals,
same actual events, no topic term in the predictor) — a self-contained
within-study baseline.

Design (24,000 runs total):
    Disciplines: 5   (FCFS, LRTF, SRTF, NPS, NPS_BINNED@f=0.20)
    Amplitudes:  4   (0.00, 0.25, 0.50, 0.75)
    Periods:     2   (14d, 28d)
    ρ_thrpt:     2   (0.5, 1.0)
    ρ_topic:     3   (0.0, 0.5, 1.0)
    Replications: 100
    Total:           24,000
"""

import argparse
import math
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd

from simulation import (
    run_single_simulation,
    _arrival_linear_pred,
)


DISCIPLINES_REF = ["FCFS", "LRTF", "SRTF", "NPS"]
RHO_LEVELS = [0.5, 1.0]
RHO_IDX_MAP = {0.5: 2, 1.0: 4}
RHO_TOPIC_LEVELS = [0.0, 0.5, 1.0]
AMPLITUDE_LEVELS = [0.00, 0.25, 0.50, 0.75]
PERIOD_LEVELS_DAYS = [14.0, 28.0]
SAMPLING_MODES = ["hard"]
AGENT_LEVELS = [6]
NPS_INTERCEPT = 10.22
NPS_BINNED_TARGET_F = 0.20

N_REPLICATIONS = 100
D_END = 365
PHASE = 0.0


def generate_experiment_configs(n_replications: int = N_REPLICATIONS,
                                 d_end: int = D_END) -> list:
    configs = []

    for amp in AMPLITUDE_LEVELS:
        for period in PERIOD_LEVELS_DAYS:
            for rho in RHO_LEVELS:
                rho_idx = RHO_IDX_MAP[rho]
                for rho_topic in RHO_TOPIC_LEVELS:
                    for mode in SAMPLING_MODES:
                        for n_agents in AGENT_LEVELS:
                            for rep in range(1, n_replications + 1):
                                common = {
                                    "rho": rho,
                                    "rho_idx": rho_idx,
                                    "rho_topic": rho_topic,
                                    "sampling_mode": mode,
                                    "n_agents": n_agents,
                                    "nps_intercept": NPS_INTERCEPT,
                                    "sla_hours": None,
                                    "replication": rep,
                                    "d_end": d_end,
                                    "amplitude": amp,
                                    "period_days": period,
                                    "phase": PHASE,
                                }
                                for disc in DISCIPLINES_REF:
                                    configs.append({**common, "discipline": disc})
                                configs.append({
                                    **common,
                                    "discipline": "NPS_BINNED",
                                    "target_f": NPS_BINNED_TARGET_F,
                                })

    return configs


def print_baseline_arrival_diagnostics(d_end: int = D_END) -> None:
    rates = []
    for d in range(d_end):
        linear_pred = _arrival_linear_pred(float(d))
        rate_per_day = 24.0 / math.exp(linear_pred)
        rates.append(rate_per_day)

    rates_arr = pd.Series(rates)
    print("=" * 72)
    print("BASELINE ARRIVAL-RATE DIAGNOSTICS (year/month/weekday)")
    print("=" * 72)
    print(f"  Mean: {rates_arr.mean():.3f}/day | std: {rates_arr.std():.3f} | "
          f"min: {rates_arr.min():.3f} | max: {rates_arr.max():.3f}")
    print(f"  Coefficient of variation: {rates_arr.std()/rates_arr.mean():.3f}")
    print(f"  Expected cases over {d_end} days: {sum(rates):.0f}")
    print()


def run_experiments(n_workers: int = None,
                     n_replications: int = N_REPLICATIONS,
                     d_end: int = D_END,
                     output_file: str = "results/results.csv") -> pd.DataFrame:
    if n_workers is None:
        n_workers = cpu_count()

    configs = generate_experiment_configs(n_replications, d_end)
    total = len(configs)

    print("Study 4b — Sinusoidal arrivals × topic-aware NPS predictor")
    print(f"  Disciplines:       {DISCIPLINES_REF + ['NPS_BINNED']}")
    print(f"  Amplitudes (A):    {AMPLITUDE_LEVELS}")
    print(f"  Periods (P, days): {PERIOD_LEVELS_DAYS}")
    print(f"  ρ_throughput:      {RHO_LEVELS}")
    print(f"  ρ_topic:           {RHO_TOPIC_LEVELS}")
    print(f"  Sampling modes:    {SAMPLING_MODES}")
    print(f"  Agents:            {AGENT_LEVELS}")
    print(f"  NPS intercept:     {NPS_INTERCEPT}")
    print(f"  NPS_BINNED f:      {NPS_BINNED_TARGET_F}")
    print(f"  Replications:      {n_replications}")
    print(f"  Sim length:        {d_end} days (30-day burn-in)")
    print(f"  Total runs:        {total}")
    print(f"  CPU cores:         {n_workers}")
    print()

    print_baseline_arrival_diagnostics(d_end)

    start_time = time.time()
    print(f"Starting {total} simulations...")

    with Pool(processes=n_workers) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(run_single_simulation, configs)):
            results.append(result)
            if (i + 1) % 500 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                pct = (i + 1) / total * 100
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (total - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{total}] {pct:.1f}% — "
                      f"{elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")

    total_time = time.time() - start_time
    print(f"\nDone! {total_time:.1f}s ({total_time/60:.1f} min)")

    daily_q_records = []
    daily_a_records = []
    aggregate_records = []

    for r in results:
        daily_q = r.pop("_daily_queue_lengths")
        daily_a = r.pop("_daily_arrivals")
        aggregate_records.append(r)
        for day, qlen in enumerate(daily_q):
            daily_q_records.append({
                "discipline": r["discipline"],
                "rho": r["rho"],
                "rho_topic": r["rho_topic"],
                "amplitude": r["amplitude"],
                "period_days": r["period_days"],
                "n_agents": r["n_agents"],
                "replication": r["replication"],
                "day": day,
                "queue_length": qlen,
            })
        for day, n in enumerate(daily_a):
            daily_a_records.append({
                "discipline": r["discipline"],
                "rho": r["rho"],
                "rho_topic": r["rho_topic"],
                "amplitude": r["amplitude"],
                "period_days": r["period_days"],
                "n_agents": r["n_agents"],
                "replication": r["replication"],
                "day": day,
                "arrivals": n,
            })

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(aggregate_records)
    df.to_csv(output_file, index=False)
    print(f"\nResults saved: {output_file}")

    out_path = Path(output_file)
    daily_q_file = out_path.with_name("daily_queue_lengths.csv.gz")
    pd.DataFrame(daily_q_records).to_csv(daily_q_file, index=False)
    print(f"Daily queue lengths: {daily_q_file}")
    print(f"  ({len(daily_q_records):,} rows, ~{daily_q_file.stat().st_size / 1e6:.1f} MB)")

    daily_a_file = out_path.with_name("daily_arrivals.csv.gz")
    pd.DataFrame(daily_a_records).to_csv(daily_a_file, index=False)
    print(f"Daily arrivals: {daily_a_file}")
    print(f"  ({len(daily_a_records):,} rows, ~{daily_a_file.stat().st_size / 1e6:.1f} MB)")

    return df


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 110)
    print("STUDY 4b — ORG NPS BY (DISCIPLINE × A × P × ρ_thr × ρ_topic)")
    print("=" * 110)

    for rho in sorted(df["rho"].unique()):
        for P in sorted(df["period_days"].unique()):
            for rt in sorted(df["rho_topic"].unique()):
                print(f"\n>>> ρ_thr = {rho}, P = {P:.0f}d, ρ_topic = {rt}")
                header = f"{'A':>6} | " + " | ".join(f"{d:>10}"
                                                      for d in ["FCFS", "LRTF",
                                                                "SRTF", "NPS",
                                                                "NPS_BINNED"])
                print(header)
                print("-" * len(header))
                for A in sorted(df["amplitude"].unique()):
                    row = [f"{A:>6.2f}"]
                    for disc in ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]:
                        sub = df[(df["discipline"] == disc) &
                                 (df["rho"] == rho) &
                                 (df["amplitude"].round(3) == round(A, 3)) &
                                 (df["period_days"].round(1) == round(P, 1)) &
                                 (df["rho_topic"].round(3) == round(rt, 3))]
                        if len(sub) > 0:
                            row.append(f"{sub['organisation_nps'].mean():>+10.3f}")
                        else:
                            row.append("       n/a")
                    print(" | ".join(row))


def print_sanity_checks(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("SANITY CHECKS")
    print("=" * 80)

    # 1. Topic match rates (predictor diagnostic)
    print("\n1. Topic match rate by ρ_topic (Study 4b predictor diagnostic):")
    for rt in sorted(df["rho_topic"].unique()):
        sub = df[df["rho_topic"].round(3) == round(rt, 3)]
        if len(sub) > 0:
            m = sub["topic_match_rate"].mean()
            print(f"   ρ_topic={rt:.2f}: {m:.3f} (expected ~{rt + (1-rt)/10:.3f})")

    # 2. Var(predicted_nps) by ρ_topic
    print("\n2. Var(predicted_nps) by ρ_topic:")
    for rt in sorted(df["rho_topic"].unique()):
        for rho in sorted(df["rho"].unique()):
            sub = df[(df["rho_topic"].round(3) == round(rt, 3)) &
                     (df["rho"] == rho)]
            if len(sub) > 0:
                v = sub["predicted_nps_var"].mean()
                print(f"   ρ_topic={rt:.2f}, ρ_thr={rho}: Var(pred_nps) = {v:.5f}")

    # 3. corr(pred, actual NPS)
    print("\n3. corr(predicted_nps, actual NPS response) by ρ_topic:")
    for rt in sorted(df["rho_topic"].unique()):
        for rho in sorted(df["rho"].unique()):
            sub = df[(df["rho_topic"].round(3) == round(rt, 3)) &
                     (df["rho"] == rho)]
            if len(sub) > 0:
                c = sub["pred_actual_corr"].mean()
                print(f"   ρ_topic={rt:.2f}, ρ_thr={rho}: corr = {c:+.4f}")

    # 4. NPS ≡ LRTF (H5 check)
    print("\n4. H5 — NPS ≡ LRTF across ρ_topic?")
    print("   Expected at ρ_topic=0 (no topic term), should diverge at ρ_topic>0.")
    for rt in sorted(df["rho_topic"].unique()):
        max_d = 0.0
        for rho in sorted(df["rho"].unique()):
            for P in sorted(df["period_days"].unique()):
                for A in sorted(df["amplitude"].unique()):
                    n = df[(df["discipline"] == "NPS") &
                           (df["rho"] == rho) &
                           (df["rho_topic"].round(3) == round(rt, 3)) &
                           (df["period_days"].round(1) == round(P, 1)) &
                           (df["amplitude"].round(3) == round(A, 3))]["organisation_nps"].mean()
                    l = df[(df["discipline"] == "LRTF") &
                           (df["rho"] == rho) &
                           (df["rho_topic"].round(3) == round(rt, 3)) &
                           (df["period_days"].round(1) == round(P, 1)) &
                           (df["amplitude"].round(3) == round(A, 3))]["organisation_nps"].mean()
                    if not (math.isnan(n) or math.isnan(l)):
                        max_d = max(max_d, abs(n - l))
        print(f"   ρ_topic={rt:.2f}: max |NPS − LRTF| over all (A,P,ρ_thr) = {max_d:.4f} pp")

    # 5. Mean preservation
    print("\n5. Mean-rate preservation (arrivals_after_burnin by A):")
    for P in sorted(df["period_days"].unique()):
        sub = df[(df["period_days"].round(1) == round(P, 1)) &
                 (df["rho_topic"].round(3) == 0.0)]
        print(f"   P={P:.0f}d (ρ_topic=0):")
        for A in sorted(df["amplitude"].unique()):
            s = sub[sub["amplitude"].round(3) == round(A, 3)]
            if len(s) > 0:
                n = s["arrivals_after_burnin"].mean()
                e = s["arrivals_after_burnin"].std()
                print(f"     A={A:.2f}: {n:.1f} ± {e:.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Study 4b experiments")
    parser.add_argument("--quick", action="store_true",
                        help="5 reps × 90 days (smoke pipeline)")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--replications", type=int, default=N_REPLICATIONS)
    parser.add_argument("--days", type=int, default=D_END)
    parser.add_argument("--output", type=str, default="results/results.csv")
    args = parser.parse_args()

    if args.quick:
        print("*** QUICK MODE ***\n")
        df = run_experiments(args.workers, 5, 90, args.output)
    else:
        df = run_experiments(args.workers, args.replications, args.days, args.output)

    print_summary(df)
    print_sanity_checks(df)
