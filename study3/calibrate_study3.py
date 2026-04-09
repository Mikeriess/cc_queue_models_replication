"""
Pre-experiment kalibrering for Study 3.

Beregner to parametre og gemmer dem i results/calibration.json:

1. **CALIBRATED_SCALING_FACTOR** — skalerer Eq. 9 koefficienten så variansen
   i predicted_nps under den nye Weibull-baserede throughput-prædiktion
   matcher variansen under Study 2's seasonality-baserede prædiktion.
   (Option C fra study3.md afsnit D4.)

2. **BETA_Z** — koefficienten for z_actual som feature i "soft Z" sampling
   mode. Kalibreres så variansen af aktivitetsvarighederne matcher hard Z
   mode så godt som muligt.

Kør FØR run_experiments.py, ellers bruger simulation.py defaults (1.0 og 0.0)
hvilket svarer til uændret Study 2 opførsel.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = RESULTS_DIR / "calibration.json"

# Study 2 resultater (til baseline-varians)
STUDY2_RESULTS = SCRIPT_DIR.parent / "study2" / "results" / "results.csv"


# =============================================================================
# Konstanter (kopieret fra simulation.py for at undgå circular import ved
# første kørsel hvor calibration.json ikke findes endnu)
# =============================================================================

DURATION_INTERCEPT = 1.6645
DURATION_THETA = 0.3908
NPS_PRED_THROUGHPUT_COEF = -0.0949


# =============================================================================
# Study 2 import for at kunne genkøre seasonality-modellen
# =============================================================================

import sys
sys.path.insert(0, str(SCRIPT_DIR.parent / "study2"))
# Vi importerer forsigtigt: kun det vi skal bruge
from simulation import (  # type: ignore
    predict_throughput_time as study2_predict_throughput,
    generate_all_arrivals as study2_generate_arrivals,
    SIM_START_YEAR,
)


# =============================================================================
# Trin 1: Baseline-varians fra Study 2
# =============================================================================

def compute_baseline_variance(n_samples: int = 50000) -> float:
    """
    Beregn Var(log(predicted_throughput + 1)) fra Study 2's seasonality-model.

    Vi sampler n_samples tidspunkter jævnt fordelt over simuleringsperioden
    (jul 2018 – jul 2019) og beregner predicted_throughput for hver. Det giver
    den "naturlige" varians i det gamle prædiktionssystem.
    """
    rng = np.random.default_rng(42)
    # Sampler tidspunkter jævnt fordelt over 365 dage (fraktionelle)
    arrival_times = rng.uniform(0, 365, size=n_samples)

    log_pt_values = np.empty(n_samples)
    for i, t in enumerate(arrival_times):
        pt_minutes = study2_predict_throughput(t)
        log_pt_values[i] = math.log(pt_minutes + 1)

    return float(np.var(log_pt_values))


def compute_new_variance(n_samples: int = 50000) -> float:
    """
    Beregn Var(log(predicted_throughput + 1)) under Study 3's Weibull-baserede
    prædiktion fra z_pred ~ N(0, 1).

    Uafhængig af ρ fordi den marginale fordeling af predicted_throughput er
    samme uanset korrelationen med z_actual.
    """
    rng = np.random.default_rng(1337)
    z_pred = rng.normal(0.0, 1.0, size=n_samples)
    u_pred = norm.cdf(z_pred)
    u_pred = np.clip(u_pred, 1e-9, 1 - 1e-9)

    scale_hours = math.exp(DURATION_INTERCEPT)
    predicted_hours = scale_hours * (-np.log(1.0 - u_pred)) ** DURATION_THETA
    predicted_minutes = predicted_hours * 60.0

    log_pt_values = np.log(predicted_minutes + 1)
    return float(np.var(log_pt_values))


def calibrate_scaling_factor() -> dict:
    """Beregn CALIBRATED_SCALING_FACTOR (Option C)."""
    print("Trin 1: Varians-kalibrering for Eq. 9 (Option C)")
    print("-" * 60)

    baseline_var = compute_baseline_variance()
    new_var = compute_new_variance()

    print(f"  Baseline varians (Study 2):  {baseline_var:.6f}")
    print(f"  Ny varians (Study 3):        {new_var:.6f}")
    print(f"  Ratio (baseline/ny):         {baseline_var/new_var:.4f}")

    scaling_factor = math.sqrt(baseline_var / new_var)
    new_coef = NPS_PRED_THROUGHPUT_COEF * scaling_factor

    print(f"  CALIBRATED_SCALING_FACTOR:   {scaling_factor:.6f}")
    print(f"  Original coef (-0.0949) → {new_coef:.6f}")
    print()

    return {
        "scaling_factor": scaling_factor,
        "baseline_var": baseline_var,
        "new_var": new_var,
        "original_coef": NPS_PRED_THROUGHPUT_COEF,
        "rescaled_coef": new_coef,
    }


# =============================================================================
# Trin 2: Kalibrering af BETA_Z
# =============================================================================

def compute_hard_mode_duration_var(n_samples: int = 50000) -> float:
    """
    Mål variansen i log(duration) under hard Z mode.

    I hard mode bruger alle aktiviteter u_fixed = Φ(z_actual). Vi bruger
    intercept-only scale (samme som predict_throughput_from_z) for at måle
    den "rene" bidrag fra u_fixed.
    """
    rng = np.random.default_rng(2024)
    z = rng.normal(0.0, 1.0, size=n_samples)
    u = norm.cdf(z)
    u = np.clip(u, 1e-9, 1 - 1e-9)

    scale = math.exp(DURATION_INTERCEPT)
    durations = scale * (-np.log(1.0 - u)) ** DURATION_THETA
    log_dur = np.log(durations + 1e-9)
    return float(np.var(log_dur))


def compute_soft_mode_duration_var(beta_z: float, n_samples: int = 50000) -> float:
    """
    Mål variansen i log(duration) under soft Z mode med en given BETA_Z.

    I soft mode er varigheden:
        duration = exp(alpha + BETA_Z * z_actual) * Weibull_random(shape)
    """
    rng = np.random.default_rng(2025)
    z = rng.normal(0.0, 1.0, size=n_samples)
    weibull_samples = rng.weibull(1.0 / DURATION_THETA, size=n_samples)

    scale = np.exp(DURATION_INTERCEPT + beta_z * z)
    durations = scale * weibull_samples
    log_dur = np.log(durations + 1e-9)
    return float(np.var(log_dur))


def compute_soft_mode_correlation(beta_z: float, n_samples: int = 100000) -> float:
    """
    Beregn korrelationen mellem z_actual og log(duration) i soft mode.

    I soft mode: log(duration) = (alpha + BETA_Z * z) + log(Weibull_random)
    Analytisk: corr = BETA_Z / sqrt(BETA_Z² + Var(log Weibull))
    """
    rng = np.random.default_rng(2025)
    z = rng.normal(0.0, 1.0, size=n_samples)
    weibull_samples = rng.weibull(1.0 / DURATION_THETA, size=n_samples)

    scale = np.exp(DURATION_INTERCEPT + beta_z * z)
    durations = scale * weibull_samples
    log_dur = np.log(durations + 1e-9)

    return float(np.corrcoef(z, log_dur)[0, 1])


def calibrate_beta_z(target_correlation: float = 0.5) -> dict:
    """
    Find BETA_Z så soft mode giver en meningsfuld korrelation mellem
    z_actual og log(duration).

    Motivation: i hard mode er correlation(z, log(duration)) = 1 (deterministisk).
    I soft mode vil vi have en moderat korrelation der efterligner "z påvirker
    men bestemmer ikke aktivitetsvarigheden". Target = 0.5 er et rimeligt
    valg der gør aktivitetsvarigheder afhængige af z men ikke determineret
    af det.

    Analytisk: corr = BETA_Z / sqrt(BETA_Z² + Var(log Weibull_random))
    For Weibull med shape 1/θ: Var(log Weibull) ≈ π²/6 · θ² ≈ 0.251

    Args:
        target_correlation: Ønsket korrelation mellem z_actual og log(duration)

    Returns:
        Dict med beta_z og diagnostics
    """
    print("Trin 2: Kalibrering af BETA_Z (soft Z mode)")
    print("-" * 60)
    print(f"  Target korrelation: {target_correlation}")
    print(f"  (hard mode har implicit korrelation = 1.0)")

    hard_var = compute_hard_mode_duration_var()
    print(f"  Hard mode Var(log duration):  {hard_var:.6f}")

    # Binær søgning over beta_z ∈ [0, 2]. Monotonisk stigende i beta_z.
    lo, hi = 0.0, 2.0
    for _ in range(40):
        mid = (lo + hi) / 2
        corr = compute_soft_mode_correlation(mid)
        if corr < target_correlation:
            lo = mid
        else:
            hi = mid
        if abs(corr - target_correlation) < 1e-4:
            break

    beta_z = (lo + hi) / 2
    final_corr = compute_soft_mode_correlation(beta_z)
    final_var = compute_soft_mode_duration_var(beta_z)

    print(f"  Kalibreret BETA_Z:            {beta_z:.6f}")
    print(f"  Opnået korrelation:           {final_corr:.4f}")
    print(f"  Soft mode Var(log duration):  {final_var:.6f}")
    print()

    return {
        "beta_z": beta_z,
        "target_correlation": target_correlation,
        "achieved_correlation": final_corr,
        "hard_mode_var": hard_var,
        "soft_mode_var": final_var,
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Study 3 — Pre-experiment kalibrering")
    print("=" * 60)
    print()

    scaling_result = calibrate_scaling_factor()
    beta_z_result = calibrate_beta_z()

    output = {
        "scaling_factor": scaling_result["scaling_factor"],
        "beta_z": beta_z_result["beta_z"],
        "baseline_var": scaling_result["baseline_var"],
        "new_var": scaling_result["new_var"],
        "rescaled_coef": scaling_result["rescaled_coef"],
        "hard_mode_var": beta_z_result["hard_mode_var"],
        "soft_mode_var": beta_z_result["soft_mode_var"],
        "target_correlation": beta_z_result["target_correlation"],
        "achieved_correlation": beta_z_result["achieved_correlation"],
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Kalibrering gemt i: {OUTPUT_FILE}")
    print()
    print("Nu kan simulation.py indlæse disse værdier ved næste import.")


if __name__ == "__main__":
    main()
