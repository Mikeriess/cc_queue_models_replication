"""
Experiment runner for Study 4 — Sinusoidal arrival rate sensitivity.

Sweeps the arrival-rate amplitude A while holding the long-run mean rate
constant (∫sin = 0). Period grid covers two scales orthogonal to the
existing weekday seasonality (P ∈ {14d, 28d}). Disciplines include the
full study-3e set plus the paper's raw NPS rule (so H5: NPS ≡ LRTF can
be re-checked under non-stationary load).

Design (8,000 runs total):
    NPS_BINNED at f=0.20:   4 (A) × 2 (P) × 2 (ρ) × 100 reps = 1,600
    LRTF, SRTF, NPS:        4 (A) × 2 (P) × 2 (ρ) × 100 reps × 3 = 4,800
    FCFS:                   4 (A) × 2 (P) × 2 (ρ) × 100 reps = 1,600
    Total:                                                      8,000

(FCFS and the f-invariant disciplines are still grid-replicated across ρ
to keep paired seeding consistent with prior studies; A=0 cells across
P collapse to identical arrival sequences but are kept separate for grid
bookkeeping.)
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
    sinusoidal_factor,
)


# =============================================================================
# EXPERIMENT DESIGN
# =============================================================================

DISCIPLINES_REF = ["FCFS", "LRTF", "SRTF", "NPS"]
RHO_LEVELS = [0.5, 1.0]
RHO_IDX_MAP = {0.5: 2, 1.0: 4}
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
                for mode in SAMPLING_MODES:
                    for n_agents in AGENT_LEVELS:
                        for rep in range(1, n_replications + 1):
                            common = {
                                "rho": rho,
                                "rho_idx": rho_idx,
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


# =============================================================================
# DIAGNOSTICS
# =============================================================================

def print_baseline_arrival_diagnostics(d_end: int = D_END) -> None:
    """
    Computes the implicit amplitude already present in study2/3 from the
    year/month/day/weekday structure. Reports std(λ_base)/mean(λ_base) over
    the simulation horizon — an "effective amplitude" the sinusoid is added
    on top of.
    """
    rates = []
    for d in range(d_end):
        linear_pred = _arrival_linear_pred(float(d))
        rate_per_day = 24.0 / math.exp(linear_pred)
        rates.append(rate_per_day)

    rates_arr = pd.Series(rates)
    mean_r = rates_arr.mean()
    std_r = rates_arr.std()
    min_r = rates_arr.min()
    max_r = rates_arr.max()

    print("=" * 72)
    print("BASELINE ARRIVAL-RATE DIAGNOSTICS (existing year/month/weekday)")
    print("=" * 72)
    print(f"  Mean rate (cases/day):   {mean_r:.3f}")
    print(f"  Std  rate (cases/day):   {std_r:.3f}")
    print(f"  Min  rate (cases/day):   {min_r:.3f}")
    print(f"  Max  rate (cases/day):   {max_r:.3f}")
    print(f"  Coefficient of variation (std/mean): {std_r/mean_r:.3f}")
    print(f"  (max - min) / (2 * mean): {(max_r - min_r) / (2 * mean_r):.3f}")
    print("    ↑ informal 'effective amplitude' already present in baseline")
    print(f"  Total expected cases over {d_end} days: {sum(rates):.0f}")
    print()


def print_amplitude_summary() -> None:
    """Print expected peak/trough rate factors for each A used in the grid."""
    print("Sinusoidal modulation grid (long-run mean preserved):")
    print(f"  {'A':>5} | {'peak factor':>12} | {'trough factor':>14}")
    print(f"  {'-'*5}-+-{'-'*12}-+-{'-'*14}")
    for amp in AMPLITUDE_LEVELS:
        print(f"  {amp:>5.2f} | {1+amp:>12.2f} | {1-amp:>14.2f}")
    print()


# =============================================================================
# RUNNER
# =============================================================================

def run_experiments(n_workers: int = None,
                     n_replications: int = N_REPLICATIONS,
                     d_end: int = D_END,
                     output_file: str = "results/results.csv") -> pd.DataFrame:
    if n_workers is None:
        n_workers = cpu_count()

    configs = generate_experiment_configs(n_replications, d_end)
    total = len(configs)

    print("Study 4 — Sinusoidal arrival rate sensitivity")
    print(f"  Disciplines:       {DISCIPLINES_REF + ['NPS_BINNED']}")
    print(f"  Amplitudes (A):    {AMPLITUDE_LEVELS}")
    print(f"  Periods (P, days): {PERIOD_LEVELS_DAYS}")
    print(f"  ρ levels:          {RHO_LEVELS}")
    print(f"  Sampling modes:    {SAMPLING_MODES}")
    print(f"  Agents:            {AGENT_LEVELS}")
    print(f"  NPS intercept:     {NPS_INTERCEPT}")
    print(f"  NPS_BINNED f:      {NPS_BINNED_TARGET_F}")
    print(f"  Replications:      {n_replications}")
    print(f"  Sim length:        {d_end} days (30-day burn-in, 335-day measurement)")
    print(f"  Total runs:        {total}")
    print(f"  CPU cores:         {n_workers}")
    print()

    print_amplitude_summary()
    print_baseline_arrival_diagnostics(d_end)

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


# =============================================================================
# SUMMARY + SANITY CHECKS
# =============================================================================

def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 100)
    print("STUDY 4: ORG NPS BY (DISCIPLINE × A × P × ρ)")
    print("=" * 100)

    rhos = sorted(df["rho"].unique())
    periods = sorted(df["period_days"].unique())
    amps = sorted(df["amplitude"].unique())

    for rho in rhos:
        for P in periods:
            print(f"\n>>> ρ = {rho}, P = {P:.0f}d")
            header = f"{'A':>6} | " + " | ".join(f"{d:>10}"
                                                  for d in ["FCFS", "LRTF", "SRTF",
                                                            "NPS", "NPS_BINNED"])
            print(header)
            print("-" * len(header))
            for A in amps:
                row = [f"{A:>6.2f}"]
                for disc in ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]:
                    sub = df[(df["discipline"] == disc) &
                             (df["rho"] == rho) &
                             (df["amplitude"].round(3) == round(A, 3)) &
                             (df["period_days"].round(1) == round(P, 1))]
                    if len(sub) > 0:
                        row.append(f"{sub['organisation_nps'].mean():>+10.3f}")
                    else:
                        row.append("       n/a")
                print(" | ".join(row))


def print_sanity_checks(df: pd.DataFrame) -> None:
    print("\n" + "=" * 72)
    print("SANITY CHECKS")
    print("=" * 72)

    # 1. Mean rate preservation across A (per ρ, per P)
    print("\n1. Mean-rate preservation (mean arrivals after burn-in, by A):")
    print("   Should be constant within MC noise across A at fixed (P, ρ).")
    for P in sorted(df["period_days"].unique()):
        for rho in sorted(df["rho"].unique()):
            print(f"   P={P:.0f}d, ρ={rho}:")
            for A in sorted(df["amplitude"].unique()):
                sub = df[(df["amplitude"].round(3) == round(A, 3)) &
                         (df["period_days"].round(1) == round(P, 1)) &
                         (df["rho"] == rho)]
                if len(sub) > 0:
                    n = sub["arrivals_after_burnin"].mean()
                    s = sub["arrivals_after_burnin"].std()
                    print(f"     A={A:.2f}: arrivals_after_burnin = {n:.1f} ± {s:.1f}")

    # 2. NPS ≡ LRTF (H5)
    print("\n2. H5 — NPS ≡ LRTF across A?")
    print("   |orgNPS(NPS) − orgNPS(LRTF)| should be ≈ 0 at all A, P, ρ.")
    for P in sorted(df["period_days"].unique()):
        for rho in sorted(df["rho"].unique()):
            for A in sorted(df["amplitude"].unique()):
                lrtf = df[(df["discipline"] == "LRTF") &
                          (df["rho"] == rho) &
                          (df["amplitude"].round(3) == round(A, 3)) &
                          (df["period_days"].round(1) == round(P, 1))]["organisation_nps"].mean()
                nps = df[(df["discipline"] == "NPS") &
                         (df["rho"] == rho) &
                         (df["amplitude"].round(3) == round(A, 3)) &
                         (df["period_days"].round(1) == round(P, 1))]["organisation_nps"].mean()
                if not (math.isnan(lrtf) or math.isnan(nps)):
                    diff = nps - lrtf
                    flag = "" if abs(diff) < 0.1 else "  ⚠"
                    print(f"   P={P:.0f}, ρ={rho}, A={A:.2f}: "
                          f"NPS−LRTF = {diff:+.4f}{flag}")

    # 3. Cyclic-steady-state diagnostic (first vs second half of measurement window)
    print("\n3. Cyclic-steady-state — orgNPS first half vs second half:")
    print("   Difference should be < 0.3 pp; >0.5 pp at high A flags burn-in inadequacy.")
    for P in sorted(df["period_days"].unique()):
        for A in sorted(df["amplitude"].unique()):
            sub = df[(df["amplitude"].round(3) == round(A, 3)) &
                     (df["period_days"].round(1) == round(P, 1))]
            if len(sub) > 0:
                d1 = sub["organisation_nps_first_half"].mean()
                d2 = sub["organisation_nps_second_half"].mean()
                flag = "" if abs(d2 - d1) < 0.3 else "  ⚠"
                print(f"   P={P:.0f}, A={A:.2f}: "
                      f"first={d1:+.2f}, second={d2:+.2f}, diff={d2-d1:+.2f}{flag}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Study 4 Monte Carlo experiments")
    parser.add_argument("--quick", action="store_true",
                        help="5 reps × 90 days (smoke pipeline)")
    parser.add_argument("--pilot", action="store_true",
                        help="Stability pilot at (A=0.75, P=28, FCFS), 5 reps × 365 days")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--replications", type=int, default=N_REPLICATIONS)
    parser.add_argument("--days", type=int, default=D_END)
    parser.add_argument("--output", type=str, default="results/results.csv")
    args = parser.parse_args()

    if args.pilot:
        print("*** PILOT MODE — stability check at worst-case cell ***\n")
        print_amplitude_summary()
        print_baseline_arrival_diagnostics(args.days)
        configs = []
        for rep in range(1, 6):
            configs.append({
                "discipline": "FCFS",
                "n_agents": 6,
                "sla_hours": None,
                "replication": rep,
                "rho": 1.0,
                "rho_idx": 4,
                "sampling_mode": "hard",
                "d_end": args.days,
                "amplitude": 0.75,
                "period_days": 28.0,
                "phase": 0.0,
                "nps_intercept": NPS_INTERCEPT,
            })
        from simulation import run_single_simulation as _run
        for cfg in configs:
            r = _run(cfg)
            print(f"  rep={cfg['replication']}: "
                  f"arrivals={r['total_cases_arrived']} "
                  f"(after burn-in={r['arrivals_after_burnin']}), "
                  f"closed={r['percent_cases_closed']:.1%}, "
                  f"avg_q={r['avg_queue_length']:.1f}, "
                  f"peak_q={r['peak_queue_length']}, "
                  f"orgNPS={r['organisation_nps']:+.2f}")
        raise SystemExit(0)

    if args.quick:
        print("*** QUICK MODE ***\n")
        df = run_experiments(args.workers, 5, 90, args.output)
    else:
        df = run_experiments(args.workers, args.replications, args.days, args.output)

    print_summary(df)
    print_sanity_checks(df)
