# Study 3d — Rank-binned NPS Prediction: Plan and scope

## 1. Motivation

The studies in this repo build on a chain of progressively narrower findings:

- **Study 2** reproduced the paper's central qualitative claim — NPS-prioritization beats FCFS — and confirmed the paper's own observation that NPS ≈ LRTF in practice.
- **Study 3** isolated *why* NPS ≡ LRTF: Eq. 9 is monotonic in throughput, and under paper calibration NPS_hat > 7.5 for every case, so `|NPS_hat − 7.5|` reduces to a monotonic re-labeling of throughput. Confirmed across all five ρ levels.
- **Study 3b** broke the equivalence by sweeping `nps_intercept` low enough to flip the entire predicted distribution below 7.5. Maximum +0.0375 individual NPS / +1.39 organisation-NPS over LRTF, and only at unphysically low intercepts.
- **Study 3c** showed that adding topic-coefficients to Eq. 9 yields a similar — and somewhat larger — improvement, but only when intercept is also lowered. At the paper's baseline (intercept = 10.22), topic-aware NPS-prediction is *worse* than LRTF.

The density-plot diagnostics in `study3c/plot_nps_distribution.py` made the underlying issue concrete:

- **Predicted NPS** (Eq. 9) lives in a 0.5-unit band around 8.7 with std ≈ 0.04.
- **Realized NPS** (Eq. 8) spans the full 0–10 scale: ~30% detractors, ~24% passives, ~46% promoters under FCFS at baseline.
- The 7.5 midpoint sits in a region where the predictor places literally zero probability mass — but where roughly half of all real responses end up.

This study fixes the prediction–realisation scale mismatch with a **quantile / rank-binning transformation**: force the predicted distribution to have the same multinomial shape as the empirical (case-company) NPS responses, while preserving the rank-order from Eq. 9.

The paper itself flags exactly this follow-up (p. 23):

> *"In follow-up studies, the distribution of the individual NPS responses should be systematically varied (as opposed to be kept constant and equal to the distribution observed in the calibration data, as was done in the present research) to identify the conditions under which the NPS-based prioritisation discipline will diverge from the LRTF discipline."*

## 2. Hypothesis

> **H₃d.** When predicted NPS is rank-binned to match the empirical multinomial supplied by the paper authors (n = 1,898, weighted mean = 8.828), the resulting `NPS_BINNED` discipline (a) breaks ≡ LRTF at the paper's baseline calibration, (b) shifts the realised response distribution toward promoters and away from detractors compared to FCFS / LRTF / SRTF / NPS, and (c) achieves this without any change to `nps_intercept` or to the prediction model itself.

**Falsification criterion.** If `NPS_BINNED` produces detractor / passive / promoter shares within sampling error of NPS or LRTF — or if it shifts shares in the *wrong* direction (more detractors / fewer promoters) — H₃d is rejected.

## 3. Theoretical argument

### 3.1 Why rank-binning breaks NPS ≡ LRTF

Under continuous Eq. 9 with intercept = 10.22, every case's predicted NPS lies in a tight band [8.6, 9.0]. The priority `|NPS_hat − 7.5|` is therefore monotone in `NPS_hat` (the abs never folds), and `NPS_hat` is monotone in `−log(throughput)`. So sorting by ascending priority is equivalent to sorting by descending throughput → identical to LRTF. Empirically this gives identical case orderings to 6 decimal places (Study 3 finding).

After rank-binning to the empirical multinomial:
- ~14.5% of cases (those with the longest predicted throughputs) get binned to 7 or 8 → priority 0.5 → **first** to be served.
- ~14.7% get binned to 6 or 9 → priority 1.5.
- ~65% (the bulk) get binned to 10 → priority 2.5 → large tied class resolved by random tie-break.
- ~3.7% get binned to 0 → priority 7.5 → **last** to be served.

The ordering is no longer monotone in throughput. In particular, the cases binned to 7 or 8 are those with the *longest* predicted throughputs (since rank-binning is ascending by raw NPS_hat = descending by throughput up to the band cutoff). Among the rest, the random tie-break introduces a stochastic component that LRTF does not have.

### 3.2 Why this should redistribute segments

The empirical multinomial has 75.8% promoters and 9.7% detractors. NPS-priority's stated goal is to "convert passives into promoters" by serving them first. Under the original continuous formulation, this goal is invisible to the discipline — there are no predicted passives to serve. Under rank-binning, ~14.5% of cases are *labeled* as predicted passives and served first. If the prediction is at all informative (ρ > 0), some of those will indeed be on the passive/detractor side of the realised distribution, and faster service should improve their realised NPS. This is the mechanism by which the segment shares should shift.

### 3.3 What we don't yet know

Several things could blunt or reverse the expected effect:

- **The 65% "promoter" class with random tie-break.** Most cases land here. Random tie-break means starvation of the tail (the bottom 5%) is replaced by stochastic delay across the whole bulk. Whether that helps or hurts on net depends on capacity.
- **Predictive validity of bin 7/8.** With ρ = 0.22 (the paper's empirical level), being "predicted passive" carries weak information. The discipline only helps to the extent that ρ is informative — same caveat as Study 3.
- **Trade-offs vs SRTF.** SRTF closes more cases overall (more short cases get served). NPS_BINNED has a different objective and may close *fewer* cases but with better segment composition. Both are valid outcomes; we should measure both.

## 4. Experimental design

### 4.1 Factors

| Factor | Levels | Rationale |
|---|---|---|
| **Discipline** | FCFS, LRTF, SRTF, NPS, **NPS_BINNED** | Replicates Study 2's full set; adds the new discipline directly comparable to NPS |
| **ρ** | 0.0, 0.22, 0.5, 0.85, 1.0 | Same five levels used in Study 3 |
| **Sampling mode** | hard | Study 3 showed soft confirms the same pattern |
| **Agents** | 6 | Critical-load setting (Study 3b/3c convention) |
| **NPS intercept** | 10.22 | Paper baseline. The whole point is to see if rank-binning works *without* the intercept hack |
| **topic_aware** | False | Isolate the binning mechanism. Topic-aware × binning is a future study |
| **SLA** | None | Paper showed SLA = 60h erases all discipline differences |
| **Replications** | 100 | Standard |

### 4.2 Run count

- LRTF, SRTF, NPS, NPS_BINNED across all 5 ρ × 100 reps = **2,000 runs**
- FCFS across all 5 ρ × 100 reps (kept for paired seeding) = **500 runs**
- **Grand total: 2,500 runs**

### 4.3 Paired seeding

Inherited from Study 3 unchanged (`derive_seeds(replication, rho_idx)`):
- `arrivals`, `actual`, `simulation` depend only on replication.
- `pred_noise` varies with `rho_idx`.
- `tie_break_key` is drawn from `rng_arrivals` so it's invariant in ρ — the same case has the same random tie-break key across all ρ levels for a given replication.

This means cross-discipline differences at fixed (replication, ρ) are due entirely to the discipline, not to RNG drift.

## 5. Method — rank-binning

### 5.1 The procedure

Given the empirical multinomial `p = (p₀, …, p₁₀)` and `N` cases:

1. Sort the cases ascending by raw `predicted_nps`.
2. Compute cumulative bin allocations:
   `cum_alloc[k] = round(cumsum(p)[k] · N)`, with `cum_alloc[10]` forced to `N`.
3. Cases at sorted positions `[cum_alloc[k-1], cum_alloc[k])` get `predicted_nps_binned = k`.
4. Run the simulation; the `NPS_BINNED` discipline sorts the visible queue by `(|predicted_nps_binned − 7.5|, tie_break_key)` ascending.

The bin allocation is deterministic given `(N, p)` — there's no per-rep stochasticity in the binning itself. Variability across replications enters through:
- Which cases get *which* raw `predicted_nps` (depends on arrivals + ρ noise).
- The tie-break key within each priority class (drawn from `rng_arrivals`).

### 5.2 Empirical multinomial

Provided by the paper authors (n = 1,898 valid responses, weighted mean = 8.828). Levels 0 and 0.1 from the original frequency table merged into bin 0:

| Bin | Count | Prob | Priority |NPS−7.5| |
|-----|-------|---------|---|
| 0   | 71    | 0.0374  | 7.5 |
| 1   | 11    | 0.0058  | 6.5 |
| 2   | 9     | 0.0047  | 5.5 |
| 3   | 9     | 0.0047  | 4.5 |
| 4   | 10    | 0.0053  | 3.5 |
| 5   | 48    | 0.0253  | 2.5 |
| 6   | 26    | 0.0137  | 1.5 |
| **7** | **74** | **0.0390** | **0.5** ← top priority |
| **8** | **201** | **0.1059** | **0.5** ← top priority |
| 9   | 253   | 0.1333  | 1.5 |
| 10  | 1186  | 0.6249  | 2.5 |

Stored at `results/empirical_nps_multinomial.json`.

### 5.3 Random tie-break

Within a priority class, ties are resolved via `case.tie_break_key ∈ [0, 1)` drawn at case creation from `rng_arrivals`. This makes ordering deterministic per (replication, ρ) but unbiased across replications.

## 6. Sanity checks

| Check | Pass criterion |
|---|---|
| **Rank preservation** | Spearman correlation between `predicted_nps` (raw) and `predicted_nps_binned` = 1.000 |
| **Target conformance** | Per-rep histogram of binned values matches `p` (cumulative-rounding ensures exact match modulo a single leftover absorbed into bin 10) |
| **FCFS invariance** | FCFS results match Study 2 baseline; FCFS does not consume `predicted_nps` |
| **NPS / LRTF reproducibility** | NPS and LRTF cells should reproduce study3c topic-blind, intercept-10.22 cells |
| **NPS ≡ LRTF preserved** | NPS and LRTF should agree to within MC noise (Study 3 finding holds at this calibration regardless of binning) |

## 7. Output and metrics

For each (discipline, ρ, replication):

**Standard** (inherited):
- `avg_individual_nps`, `organisation_nps`
- `avg_queue_length`, `avg_waiting_time_days`, `avg_capacity_utilisation`
- `percent_cases_closed`, `percent_cases_closed_last_335`
- `avg_case_resolution_time_days`

**New in Study 3d** — the headline metrics:
- `percent_detractors` (NPS 0–6)
- `percent_passives` (NPS 7–8)
- `percent_promoters` (NPS 9–10)

## 8. Plots

| File | Content |
|---|---|
| `fig_s3d_1_segment_proportions.pdf` | **Headline.** Stacked bar of detr/pass/prom % per discipline + organisation-NPS bars |
| `fig_s3d_2_binning_sanity.pdf` | Three-panel verification: raw NPS_hat density, binned histogram, achieved-vs-target proportions |
| `fig_s3d_3_metrics_vs_rho.pdf` | 2×2 panel: individual NPS, org NPS, % promoters, % detractors over ρ by discipline |
| `fig_s3d_4_advantage.pdf` | NPS_BINNED − reference advantage over ρ for FCFS, LRTF, NPS as references |

## 9. Expected outcomes

Three possible outcome regimes:

| Regime | Pattern | Interpretation |
|---|---|---|
| **Confirmation** | NPS_BINNED has lower detr%, similar prom%, higher org NPS than LRTF | H₃d confirmed — rank-binning is a sufficient mechanism for NPS-priority's value |
| **Trade-off** | NPS_BINNED has lower detr% AND lower prom% than LRTF (the smoke test signal) | Rank-binning saves passives from becoming detractors at the cost of promoter conversion. Net org NPS depends on the balance |
| **Null / negative** | NPS_BINNED ≈ LRTF or worse | The continuous-vs-binned distinction is irrelevant; the LRTF-equivalent ranking dominates whatever priority structure is layered on top. Would falsify H₃d |

The single-rep smoke test gave a hint of *Regime 2* (trade-off): NPS_BINNED at ρ=1.0 produced 0.311 detr / 0.303 pass / 0.385 prom, vs LRTF's 0.344 / 0.189 / 0.467. With 100 replications we'll know whether that pattern is real and how it depends on ρ.

## 10. Implementation

Filed at `study3d/`. Mirrors the structure of study3c:

```
study3d/
├── README.md                          # status + how-to-run
├── study3d.md                         # this document
├── Dockerfile, requirements.txt
├── simulation.py                      # fork of study3c/simulation.py
├── run_experiments.py                 # 2,500-run grid
├── generate_plots.py                  # 4 plots
└── results/
    ├── calibration.json               # copy from study3c
    ├── empirical_nps_multinomial.json # paper-author-supplied target
    ├── results.csv                    # output
    └── fig_s3d_*.pdf
```

### 10.1 Changes vs `study3c/simulation.py`

- **New constant.** `EMPIRICAL_NPS_MULTINOMIAL` loaded from `results/empirical_nps_multinomial.json` at import time.
- **New `Case` fields.** `predicted_nps_binned: int` (0..10) and `tie_break_key: float` (drawn from `rng_arrivals` at creation).
- **New function.** `apply_rank_binning(cases, target_multinomial)` mutates `cases` in place to assign `predicted_nps_binned`.
- **New discipline.** `queue_management()` adds an `NPS_BINNED` branch that sorts by `(|predicted_nps_binned − 7.5|, tie_break_key)`.
- **`simulate_timeline()` change.** Calls `apply_rank_binning` once per simulation when `discipline == "NPS_BINNED"`.
- **`run_single_simulation()` output dict.** Adds `percent_detractors`, `percent_passives`, `percent_promoters`.
- **Removed.** `topic_aware` parameter (Study 3c-specific) — Study 3d isolates the binning mechanism.

No existing study (study2, study3, study3b, study3c) is modified.

## 11. Limitations and follow-ups

1. **Single intercept.** We test only `nps_intercept = 10.22` (paper baseline). A natural follow-up is to confirm rank-binning still helps at low intercept (where Study 3b found NPS ≠ LRTF for unrelated reasons).
2. **Empirical-vs-uniform multinomial.** The empirical distribution is heavily promoter-skewed (76% in 9–10), which means most cases end up in a single tied class. Comparing to a uniform target (`p_k = 1/11`) would isolate "rank-binning per se" from "the specific shape of the empirical distribution".
3. **No SLA test.** Study 2 showed SLA erases all discipline differences. We assume that result still holds; if SLA changes the picture, that's a fourth study.
4. **No topic-aware × binning interaction.** Study 3c found topic-awareness is double-edged. Combining it with binning could either compound benefits or compound harms — open question.
5. **Random tie-break vs deterministic.** ~65% of cases tied at priority 2.5. Random tie-break injects stochasticity. A deterministic tie-break (FCFS within class) might give a cleaner discipline definition and more stable results.

## 12. Status

- [x] empirical multinomial saved
- [x] simulation.py with rank-binning + NPS_BINNED discipline
- [x] run_experiments.py
- [x] generate_plots.py
- [x] Dockerfile + requirements.txt
- [x] Smoke test (single rep × 60 days × 5 disciplines): pipeline OK, NPS_BINNED behaves differently from LRTF
- [x] Quick mode (5 reps × 60 days × 125 runs): 2.3s, full pipeline OK, all four plots generate
- [ ] Full experiment on Frigg (2,500 runs × 365 days)
- [ ] `comparison_report.md` after results land
