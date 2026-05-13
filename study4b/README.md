# Study 4b — Sinusoidal arrivals × topic-aware NPS predictor

Extension of Study 4 that adds a topic term to the NPS prediction model
(Eq. 9) and varies its accuracy via a new parameter `ρ_topic`.

## Background

Study 4 confirmed that priority disciplines extract more value when load
fluctuates (best−FCFS gap grew from +2.45 to +3.4 pp at A=0.75). But
SRTF and NPS_BINNED remained statistically tied, and the NPS ≡ LRTF
collapse held exactly. Both happen because the paper's predicted-NPS
formula (Eq. 9) is monotone in predicted throughput, so it carries no
information SRTF doesn't already have.

Study 3c showed that adding a topic term to Eq. 9 breaks the monotone
structure. Study 4b combines that mechanism with Study 4's sinusoidal
arrivals to test whether *enriched predictors × non-stationary load*
finally unlocks NPS_BINNED.

## The new parameter ρ_topic

ρ_topic ∈ [0, 1] is the probability that the predictor sees the correct
topic. The mechanism mirrors how throughput-ρ controls predictor
accuracy:

```
with prob ρ_topic:    predicted_topic = actual_topic
with prob (1-ρ_topic): predicted_topic = uniform random over CASE_TOPICS
predicted_nps = intercept + β·log(predicted_throughput+1)
                + NPS_PRED_TOPIC_COEFS[predicted_topic] − 1
```

- **ρ_topic = 0.0**: skip the draw entirely; no topic term. Identical
  to Study 4 (bit-identical paired seeding).
- **ρ_topic = 0.5**: 50% on purpose + 5% by chance ≈ 55% correct.
- **ρ_topic = 1.0**: perfect topic info; matches Study 3c's
  `topic_aware=True`.

`NPS_PRED_TOPIC_COEFS = NPS_SIM_TOPIC_COEFS` — perfect knowledge of the
topic *effect* given a topic guess (Study 3c convention). The accuracy
knob is only on the topic-prediction step, not on the coefficient
estimates.

## Hypotheses

| H | Claim |
|---|---|
| **H4b.1** | At ρ_topic > 0, NPS ≠ LRTF — topic breaks the strict throughput-monotonicity of `\|N̂PS − 7.5\|`. |
| **H4b.2** | NPS_BINNED finally beats SRTF at ρ_topic ≈ 1 and A ≈ 0.5–0.75 — combining the rank-binning coarsening with a non-monotone predictor. |
| **H4b.3** | The advantage grows monotonically in ρ_topic. |
| **H4b.4** | Magnitude bounded by `range(NPS_SIM_TOPIC_COEFS)` ≈ ±0.13 — small in absolute terms. |

## Experimental design (24,000 runs)

| Factor | Levels |
|---|---|
| Discipline | FCFS, LRTF, SRTF, NPS, NPS_BINNED (at f = 0.20) |
| Amplitude A | 0.00, 0.25, 0.50, 0.75 |
| Period P | 14 days, 28 days |
| ρ_throughput | 0.5, 1.0 |
| **ρ_topic** | **0.0, 0.5, 1.0** |
| Phase φ | 0 |
| Agents | 6 |
| NPS intercept | 10.22 |
| Replications | 100 |
| Sim length / burn-in | 365 / 30 days |

**Total: 5 × 4 × 2 × 2 × 3 × 100 = 24,000 runs.**

## Sanity checks (printed by `run_experiments.py`)

1. **Topic match rate** by ρ_topic — should match expected `ρ + (1-ρ)/10`.
2. **Var(predicted_nps)** by ρ_topic — should grow with ρ_topic (more
   predictor variance from topic term, both at full strength and noisy).
3. **corr(predicted_nps, actual NPS response)** — predictor performance
   diagnostic; should grow with both ρ_throughput and ρ_topic.
4. **NPS ≡ LRTF check by ρ_topic** — should be ≈ 0 at ρ_topic = 0 and
   non-zero at ρ_topic > 0 (H4b.1).
5. **Mean rate preservation** — `arrivals_after_burnin` constant across
   A at fixed (P, ρ_thr).

## Run via Docker

```bash
echo "STUDY=study4b" > .env
docker compose up --build
```

## Run locally

```bash
cd study4b

# smoke test (in-process); prints predictor diagnostic at ρ_topic ∈ {0, 0.5, 1}
python3 simulation.py

# quick (5 reps × 90 days)
python3 run_experiments.py --quick

# full experiment (24,000 runs)
python3 run_experiments.py --workers 8

# generate figures
python3 generate_plots.py
```

## File structure

```
study4b/
├── README.md
├── study4b.md
├── Dockerfile
├── requirements.txt
├── simulation.py        # fork of study4 + rho_topic mechanism
├── run_experiments.py   # 24,000-run grid + sanity checks
├── generate_plots.py    # 8 figures
└── results/
    ├── calibration.json               # copied from study4
    ├── empirical_nps_multinomial.json # copied from study4
    ├── results.csv                    # generated
    ├── daily_queue_lengths.csv.gz     # generated
    ├── daily_arrivals.csv.gz          # generated
    └── fig_s4b_*.pdf                  # 8 plots
```

## Status

- [x] simulation.py with rho_topic + predictor diagnostics
- [x] run_experiments.py (24,000-run grid + sanity checks)
- [x] generate_plots.py (8 plots)
- [x] Dockerfile + requirements.txt
- [ ] Smoke test (run on research server)
- [ ] Full experiment (24,000 runs on Frigg)
- [ ] comparison_report.md
