# Implementation Plan: Study 3 (The Value of Information)

## Objective

To demonstrate that the NPS-based prioritization algorithm outperforms simple
heuristics (like LRTF) when prediction accuracy improves. We simulate "the
value of information" by manipulating the correlation between predicted
throughput time and actual throughput time, without changing the underlying
distribution of case durations.

---

## Part 1: Original Design (Technical Strategy)

We introduce a **latent variable Z** representing "case complexity". This
variable drives both the actual duration (reality) and the predicted duration
(estimation), allowing us to control the correlation ρ between them.

### Step A: Initialize Latent Variable (Algorithm 3: Case Arrival)

When a new case is generated, assign it a fixed complexity score drawn from a
standard normal distribution.

- **Action:** Add attributes `z_actual`, `u_actual`, `z_pred` to the `Case` object.
- **Logic:**
  - `z_actual ~ N(0, 1)`
  - `u_actual = Φ(z_actual)`   *(standard normal CDF → uniform percentile)*
  - `z_pred = ρ · z_actual + sqrt(1 - ρ²) · ε`, where `ε ~ N(0, 1)`

### Step B: Modify Reality Generation (Algorithm 7: Next Activity)

Replace the random uniform sampling in `simulate_activity_duration` with a
**fixed percentile** derived from the case's latent complexity. This ensures
that "complex" cases (high `z_actual`) always get long durations while
preserving the original Weibull distribution shape from Study 1.

- **Current logic:**
  ```python
  duration_hours = scale * rng.weibull(shape)
  # where scale = exp(α + Σ Xᵢβᵢ), shape = 1/θ
  ```
- **New logic:** replace the randomly sampled Weibull variate with the
  inverse CDF at the case's fixed percentile `u_actual`:
  ```python
  duration_hours = scale * (-log(1 - u_actual)) ** theta
  ```
- **All activities of the same case use the same `u_actual`.** Do NOT change
  the Weibull parameters (α ≈ 1.66, θ ≈ 0.39); we only change *how* we sample.

### Step C: Modify Prediction Logic (Algorithm 3)

Replace the seasonality-only throughput prediction with one derived from `z_pred`:

- **New logic:**
  ```python
  u_pred = Φ(z_pred)
  predicted_throughput_hours = scale_default * (-log(1 - u_pred)) ** theta
  predicted_throughput_minutes = predicted_throughput_hours * 60   # unit fix
  ```
- `scale_default` is computed using the Weibull intercept only (no case-specific
  features), since the prediction happens before features are known. This is
  equivalent to `exp(DURATION_INTERCEPT) = exp(1.6645) ≈ 5.28` hours.

---

## Part 2: Implementation Decisions (Based on Review)

The following decisions address issues identified in the technical review of
the original plan.

### D1. Report in ρ, not in R²

- X-axis of final plots will be **ρ** (latent correlation), not implied R².
- Rationale: ρ is a clean, well-defined parameter. Mapping to observed R² on
  throughput time is confounded by activity count variance, start delays, and
  waiting time — and would require empirical calibration that adds no value to
  the research question.

### D2. Unit consistency fix

- The Weibull-based `predicted_throughput` is generated in **hours** but must
  be converted to **minutes** (multiply by 60) before storing on the Case, to
  maintain compatibility with Eq. 9 which was fit on minute-scale inputs.
- Rationale: preserves semantic compatibility with the existing NPS prediction
  model without requiring re-fitting.

### D3. Robustness check: hard Z vs soft Z ⭐ NEW

We run the experiment with **two sampling modes** to test the sensitivity of
the findings to the strong "all activities at same percentile" assumption.

- **Hard Z (primary design):** Every activity in a case uses `u_actual` as its
  percentile. Creates maximum signal from Z to actual throughput time.
- **Soft Z (robustness):** `z_actual` enters the Weibull linear predictor as
  an additive feature:
  ```python
  linear_pred = DURATION_INTERCEPT + ... + BETA_Z * z_actual
  ```
  Activities still have individual random variation, but complex cases have
  longer mean activity durations. `BETA_Z` is calibrated so that the variance
  contribution of `z_actual` is roughly comparable to the hard-Z condition.

Both modes are run across all ρ levels. If the main finding (NPS advantage at
high ρ) holds under both modes, the result is robust to the modeling choice.

### D4. NPS prediction variance control (Option C) ⭐ NEW

The NPS prediction model (Eq. 9) was fit when `predicted_throughput` came from
the low-R² seasonality model (narrow variance). Replacing that with the new
Weibull-based prediction changes the variance of `log(predicted_throughput + 1)`,
which in turn changes the variance of `predicted_nps` — potentially confounding
the comparison between ρ levels.

**Solution:** Scale the Eq. 9 coefficient so that the variance of `predicted_nps`
in the new approach matches the variance under Study 2's baseline. This keeps
the "noise level" of the priority scores constant across ρ levels, isolating
the pure information effect.

**Key observation:** The *marginal* distribution of `predicted_throughput` in
the new approach does NOT depend on ρ — it is always the Weibull distribution
corresponding to `u_pred ~ Uniform(0, 1)`. Therefore, the variance scaling
factor is **a single constant**, computed once before the experiment begins.

**Calibration procedure (one-time, pre-experiment):**

```python
# 1. Measure baseline variance from Study 2 data
baseline_var = Var(log(study2_predicted_throughput + 1))

# 2. Measure new-approach variance from a pilot sample
z_pilot = rng.normal(0, 1, 10000)
pt_pilot = exp(DURATION_INTERCEPT) * 60 * (-log(1 - Phi(z_pilot))) ** theta
new_var = Var(log(pt_pilot + 1))

# 3. Scaling factor
scaling_factor = sqrt(baseline_var / new_var)

# 4. Rescaled Eq. 9 coefficient
NPS_PRED_COEF_STUDY3 = NPS_PRED_THROUGHPUT_COEF * scaling_factor
```

The scaling factor is stored as a constant in `simulation.py` and applied for
all ρ levels.

### D5. Sample size: 100 replications per condition

Matches Study 2. Combined with paired seeding (D6) this gives strong
statistical power for the ρ-comparison.

### D6. Paired seeding for variance reduction

Across the ρ levels, use **the same seed** for case arrivals and `z_actual`
generation. Only the `ε` noise in `z_pred` varies (by incorporating `rho_idx`
into its seed). This pairs observations across ρ levels and dramatically
reduces variance in the `NPS - LRTF` comparison.

```python
# Independent per replication, identical across rho levels
rng_arrivals = np.random.default_rng(seed + 1_000_000)
rng_actual = np.random.default_rng(seed + 2_000_000)
# Varies with rho level
rng_pred_noise = np.random.default_rng(seed + 3_000_000 + rho_idx)
```

### D7. Sanity check: ρ = 0 must match Study 2 ⭐ MUST-PASS

Before running the full experiment, verify that at **ρ = 0** the Study 3
simulation produces results statistically indistinguishable from Study 2.
Both use the same arrival process, same activity distribution, same queue
management. The only difference is that Study 3 samples activity durations
via `u_actual` instead of `rng.weibull(shape)`, which should give the same
marginal distribution.

**Acceptance criterion:** For FCFS at 6 agents, no SLA:
- `avg_queue_length` within 10% of Study 2 baseline
- `organisation_nps` within 1 unit of Study 2 baseline
- `percent_cases_closed` within 2 percentage points

If these criteria fail, there is a bug in the implementation.

---

## Part 3: Experimental Design

### Factors

| Factor | Levels | Notes |
|--------|--------|-------|
| **ρ (prediction accuracy)** | 0.00, 0.22, 0.50, 0.85, 1.00 | 5 levels incl. 0 and 1 for bounds |
| **Sampling mode** | hard, soft | Robustness check |
| **Queue discipline** | FCFS, LRTF, NPS | FCFS as baseline (should be ρ-invariant) |
| **Number of agents** | 5, 6, 7 | 6 is primary, 5 and 7 for robustness |
| **Service level** | None | SLA fixed to None — Study 2 showed SLA eliminates discipline differences |

**Replications:** 100 per condition.

**Total runs:** 5 × 2 × 3 × 3 × 100 = **9,000 simulations**.

### Rationale for ρ levels

| Level | Interpretation |
|-------|----------------|
| 0.00 | Null case: prediction is pure noise. NPS ≈ FCFS expected. |
| 0.22 | Baseline: approximately matches Study 2's real-world performance. |
| 0.50 | Medium: e.g., basic NLP on case emails. |
| 0.85 | High: e.g., sophisticated ML / human-in-the-loop. |
| 1.00 | Upper bound: perfect information. Establishes theoretical ceiling. |

### Expected outcome (hypothesis)

For agent count = 6, sampling mode = hard Z:

- **FCFS:** Flat across ρ (should be independent of prediction accuracy).
  This is a hard check that the experiment is set up correctly.
- **LRTF:** Slight increase with ρ (LRTF uses only rank order, which becomes
  more accurate at higher ρ).
- **NPS:** Steep increase with ρ (NPS uses the magnitude of prediction, which
  becomes more informative).

---

## Part 4: Required Output

### Primary figure (Fig. S3.1)

**Title:** "The value of information: customer NPS as a function of prediction accuracy"

- **X-axis:** ρ (latent correlation), 5 levels
- **Y-axis:** Average simulated individual NPS (or organisation NPS, as secondary panel)
- **Series:** 3 queue disciplines (FCFS, LRTF, NPS)
- **Error bars:** 95% CI from paired replications
- **Panels:** 2 panels for sampling mode (hard Z, soft Z) as robustness check
- **Hypothesis visualization:** NPS curve should diverge upward from LRTF at ρ ≥ 0.5

### Diagnostic figure (Fig. S3.2)

**Title:** "NPS advantage over LRTF as a function of prediction accuracy"

- **X-axis:** ρ
- **Y-axis:** `mean(NPS) − mean(LRTF)` for individual NPS
- **Series:** 3 agent levels (5, 6, 7)
- **Interpretation:** At ρ = 0, expect zero (no information); at ρ = 1, expect
  positive advantage. The slope indicates the value of improving prediction.

### Secondary figures

- **Fig. S3.3:** Same as S3.1 but for organisation NPS (scale −100 to +100)
- **Fig. S3.4:** Case resolution time vs ρ (to check that improvements come
  from better scheduling, not changed processing time)
- **Fig. S3.5:** Waiting time vs ρ (to track the NPS/waiting-time tradeoff
  from Study 2 — does it change with ρ?)

---

## Part 5: Code Changes Required

### 5.1 New `Case` attributes in `simulation.py`

```python
@dataclass
class Case:
    # ... existing fields ...
    z_actual: float = 0.0       # latent complexity N(0,1)
    u_actual: float = 0.5       # = Phi(z_actual), used for activity sampling
    z_pred: float = 0.0         # perceived complexity (correlated with z_actual)
```

### 5.2 Modified `simulate_activity_duration`

```python
def simulate_activity_duration(case_topic, activity_type, activity_number,
                                resource_effect, rng,
                                u_fixed=None, z_feature=0.0):
    linear_pred = (DURATION_INTERCEPT
                   + DURATION_TOPIC_COEFS.get(case_topic, 0.0)
                   + DURATION_ACTIVITY_COEFS.get(activity_type, 0.0)
                   + DURATION_ACTIVITY_NUMBER_COEF * activity_number
                   + resource_effect
                   + BETA_Z * z_feature)          # <-- soft Z mode

    scale = math.exp(linear_pred)
    shape = 1.0 / DURATION_THETA

    if u_fixed is not None:
        # Hard Z mode: deterministic from percentile
        duration_hours = scale * (-math.log(1 - u_fixed)) ** DURATION_THETA
    else:
        # Baseline random sampling
        duration_hours = scale * rng.weibull(shape)

    return duration_hours
```

### 5.3 New throughput prediction from Z_pred

```python
def predict_throughput_from_z(z_pred: float) -> float:
    """
    Map latent Z_pred to predicted throughput time in minutes.

    Uses the Weibull inverse CDF with a default scale (intercept only),
    since case-specific features are not known at prediction time.
    """
    from scipy.stats import norm
    u_pred = norm.cdf(z_pred)
    # Clip to avoid -inf at u_pred = 1
    u_pred = min(u_pred, 1 - 1e-9)

    scale = math.exp(DURATION_INTERCEPT)  # hours
    predicted_hours = scale * (-math.log(1 - u_pred)) ** DURATION_THETA
    return predicted_hours * 60.0          # convert to minutes
```

### 5.4 Rescaled Eq. 9 coefficient

```python
# Computed once via calibration script (D4)
NPS_PRED_COEF_STUDY3 = NPS_PRED_THROUGHPUT_COEF * CALIBRATED_SCALING_FACTOR

def predict_nps_study3(predicted_throughput_minutes: float) -> float:
    log_throughput = math.log(predicted_throughput_minutes + 1)
    return (NPS_PRED_INTERCEPT
            + NPS_PRED_COEF_STUDY3 * log_throughput) - 1
```

### 5.5 Modified `generate_all_arrivals`

```python
def generate_all_arrivals(d_end, rng_arrivals, rng_actual, rng_pred_noise,
                          rho: float, sampling_mode: str = "hard"):
    cases = []
    # ... existing arrival time generation using rng_arrivals ...

    for case in cases:
        z_actual = rng_actual.normal(0, 1)
        epsilon = rng_pred_noise.normal(0, 1)
        z_pred = rho * z_actual + math.sqrt(1 - rho**2) * epsilon

        case.z_actual = z_actual
        case.u_actual = norm.cdf(z_actual)
        case.z_pred = z_pred
        case.predicted_throughput = predict_throughput_from_z(z_pred)
        case.predicted_nps = predict_nps_study3(case.predicted_throughput)

    return cases
```

### 5.6 Modified `next_activity` (use `case.u_actual`)

```python
def next_activity(case, start_delay, agent, rng,
                  effective_start=None, sampling_mode="hard"):
    # ... existing logic ...

    if sampling_mode == "hard":
        duration_hours = simulate_activity_duration(
            case.case_topic, next_act, activity_number,
            agent.resource_effect, rng,
            u_fixed=case.u_actual
        )
    else:  # soft mode
        duration_hours = simulate_activity_duration(
            case.case_topic, next_act, activity_number,
            agent.resource_effect, rng,
            u_fixed=None, z_feature=case.z_actual
        )
    # ... rest unchanged ...
```

### 5.7 New `run_experiments.py` design loop

```python
RHO_LEVELS = [0.00, 0.22, 0.50, 0.85, 1.00]
SAMPLING_MODES = ["hard", "soft"]
DISCIPLINES = ["FCFS", "LRTF", "NPS"]
AGENT_LEVELS = [5, 6, 7]
N_REPLICATIONS = 100

configs = []
for rho_idx, rho in enumerate(RHO_LEVELS):
    for mode in SAMPLING_MODES:
        for disc in DISCIPLINES:
            for agents in AGENT_LEVELS:
                for rep in range(1, N_REPLICATIONS + 1):
                    configs.append({
                        "rho": rho,
                        "rho_idx": rho_idx,
                        "sampling_mode": mode,
                        "discipline": disc,
                        "n_agents": agents,
                        "sla_hours": None,
                        "replication": rep,
                        "d_end": 365,
                    })
```

### 5.8 Seed derivation for paired replications

```python
def derive_seeds(replication, rho_idx):
    base = hash(("study3", replication)) % (2**31)
    return {
        "arrivals": base + 1_000_000,
        "actual": base + 2_000_000,
        "pred_noise": base + 3_000_000 + rho_idx,  # only this varies by rho
        "simulation": base + 4_000_000,
    }
```

---

## Part 6: Pre-implementation Protocol

Execute in order. Do not start the main experiment until all steps pass.

### Step 1: Calibrate BETA_Z and scaling factor

Write a small calibration script (`calibrate_study3.py`) that:

1. Computes `baseline_var` from Study 2's `predicted_throughput` column in
   `study2/results/results.csv`.
2. Generates 10,000 samples of `z_pred ~ N(0,1)` and computes the new-approach
   predicted throughput. Measures `new_var`.
3. Computes `CALIBRATED_SCALING_FACTOR = sqrt(baseline_var / new_var)`.
4. Writes the factor to a file for use by the simulation.

For **BETA_Z** (soft mode only): run a small simulation varying `BETA_Z` until
the variance contribution from `z_feature` matches the implicit variance
contribution in hard mode. A reasonable starting point: `BETA_Z ≈ DURATION_THETA`
(i.e., ~0.39).

### Step 2: Run ρ = 0 sanity check

Run Study 3 at ρ = 0 with sampling_mode = hard, FCFS, 6 agents, 100
replications. Compare to Study 2 results under identical conditions.

**Acceptance criteria (from D7):**
- `avg_queue_length`: within 10% of Study 2 baseline
- `organisation_nps`: within 1 unit
- `percent_cases_closed`: within 2 pp

If any criterion fails, debug before proceeding.

### Step 3: Pilot run

Run 10 replications for the full experimental grid (9,000 / 10 = 900 runs) to:

- Verify no bugs in the design loop
- Estimate per-run wall time and total expected runtime
- Sanity-check the direction of the effect (NPS should increase with ρ in
  hard mode; FCFS should be flat)

### Step 4: Full run

All 9,000 simulations on 24 cores. Estimated time: ~15-30 minutes based on
Study 2 timing (5,600 runs ≈ 5-8 minutes on 24 cores).

### Step 5: Generate plots and comparison report

Follow the same pattern as Study 2:
- `study3/generate_plots.py` → PDFs in `study3/results/`
- `study3/comparison_report.md` → summary with key findings

---

## Part 7: File structure (final)

```
study3/
├── study3.md                       # This plan (updated)
├── README.md                       # Short overview
├── Dockerfile                      # Same pattern as study2
├── requirements.txt                # numpy, scipy, pandas, matplotlib
├── simulation.py                   # Fork of study2/simulation.py with Study 3 additions
├── calibrate_study3.py             # Pre-experiment calibration (Step 1)
├── run_experiments.py              # Design loop + multiprocessing
├── generate_plots.py               # Fig. S3.1 – S3.5
├── comparison_report.md            # Results write-up (generated after run)
└── results/
    ├── calibration.json            # BETA_Z, CALIBRATED_SCALING_FACTOR
    ├── results.csv                 # Aggregate per-run metrics
    ├── daily_queue_lengths.csv     # (gitignored)
    ├── fig_s3_1_nps_vs_rho.pdf
    ├── fig_s3_2_nps_advantage.pdf
    ├── fig_s3_3_org_nps.pdf
    ├── fig_s3_4_resolution_time.pdf
    └── fig_s3_5_waiting_time.pdf
```

---

## Open questions / risks

1. **Is BETA_Z calibration well-defined?** The soft mode requires choosing
   BETA_Z to match the variance from hard mode. If the two modes are fundamentally
   hard to align, the robustness check may be less clean. Mitigation: define
   BETA_Z so that soft mode gives the same R² between z_actual and the sum of
   activity durations as hard mode.

2. **Effect at intermediate ρ might be non-monotonic** if the NPS prediction
   model interacts poorly with the underlying distribution. Mitigation: the
   ρ = 0 and ρ = 1 bounds provide sanity checks, and FCFS-invariance is a
   strong diagnostic.

3. **Paired seeding subtlety:** `rng_arrivals` produces cases, but the number
   of cases generated in a fixed time window depends on the RNG state (which
   depends on the inter-arrival sampling). Must ensure that the same ρ
   comparisons see the same number of cases. Mitigation: `rng_arrivals` is
   seeded independently of `rho_idx`, so it produces identical sequences.
