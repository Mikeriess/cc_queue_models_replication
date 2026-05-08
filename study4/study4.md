# Study 4 — Plan and design rationale

## Motivation

Studies 2 → 3e established that under the paper's stationary arrival
process, the practical ceiling on organisation NPS is small relative to
FCFS, and SRTF / NPS_BINNED at the optimal `f` are statistically
indistinguishable (Study 3e §5). The diagnosis was structural: the queue
reaches a tight steady state, so priority discipline has limited variance
to exploit.

Study 4 attacks that diagnosis directly. Instead of inventing new
disciplines, it changes the substrate: arrivals oscillate around a fixed
long-run mean. If priority disciplines genuinely require non-trivial
queue dynamics to differentiate, this should make them differentiate.
A null result would be its own contribution: it would establish that
the disciplinary tie observed in Study 3e is robust to non-stationary
load, not just stationary load.

## Arrival-rate modification

```
λ(t) = λ̄(t) · (1 + A · sin(2π · t / P + φ))
```

- `λ̄(t)`: existing year/month/day/weekday base rate (Study 2 model)
- `A ∈ [0, 1)`: modulation amplitude. A = 0 reproduces Study 3e
- `P`: period in days
- `φ`: phase. Pinned to 0 — simulation starts at the rising-edge mean

**Mean preservation.** ∫sin = 0 over each full period, so the long-run
mean rate equals `λ̄(t)`. We verify this empirically via the
`arrivals_after_burnin` summary in `run_experiments.py`.

## Why these periods (14d, 28d)?

The existing arrival model captures variation at three scales:
- **Within-day:** none (rate is piecewise-constant per day).
- **Within-week:** `weekday` coefficient gives 5× rate variation across
  the week — *partially overlapping* with a P=7d sine.
- **Within-year:** `month` and `day` coefficients capture seasonal and
  monthly trends.

Daily P=1d would primarily stress the agent-schedule interaction
(business hours vs sinusoidal arrivals), not the priority disciplines.
P=7d would partially alias with the existing weekday step function,
making interpretation harder. **P=14d and P=28d are orthogonal to the
existing weekly seasonality** and long enough that the queue can
accumulate meaningfully during a peak before draining during the lull.

## Why these amplitudes (0, 0.25, 0.50, 0.75)?

The implicit "effective amplitude" already in the baseline (from the
year/month/weekday model) is reported by
`print_baseline_arrival_diagnostics()`. Empirically this sits around
~0.4–0.6 (peak weekday rate vs trough), so adding `A = 0.25` is a modest
overlay, `A = 0.50` is comparable to the existing variation, and
`A = 0.75` is large but not extreme. `A = 1.0` would have zero arrival
rate at trough — degenerate and unlikely to converge in a single period
of burn-in.

## Why deterministic phase φ = 0?

- **Reproducibility:** every replication starts at the same phase, so
  any phase-dependent transient is consistent across reps.
- **Comparability:** A = 0 is exactly seed-equivalent to Study 3e at
  the same (ρ, rep) pair, because the A = 0 fast path uses a single
  uniform draw per inter-arrival (matching Study 3e's
  `simulate_inter_arrival_time`).
- **Cleaner aggregates:** with a random phase the cyclic structure
  averages out across reps; with a fixed phase we keep it.

## Why these disciplines?

- **FCFS:** baseline, ρ-invariant, A-invariant in expectation but kept
  for paired-seeded comparison.
- **LRTF:** Study 3 monotonicity-collapse partner of NPS.
- **SRTF:** Study 3e operational winner; key competitor for NPS_BINNED.
- **NPS:** the paper's `|N̂PS − 7.5|` rule. Included to test H5
  (NPS ≡ LRTF under non-stationary load).
- **NPS_BINNED at f = 0.20:** the Study 3e operational optimum.
  Tied with SRTF in the stationary regime; Study 4 tests whether
  non-stationary load breaks the tie in either direction.

## Why these ρ levels?

We dropped ρ = 0 (uninformative predictor — already mapped in
Study 3e) and kept ρ = 0.5 (mid-information) and ρ = 1.0
(perfect prediction). H2 and H3 are sharpest at high ρ, so ρ = 1.0 is
the headline cell. ρ = 0.5 confirms whether effects are continuous
or knife-edged in prediction quality.

## Implementation: thinning algorithm

Lewis thinning generates non-homogeneous Poisson arrivals using a
piecewise-constant upper bound `λ_max`. Within each day, `λ_base` is
constant (Study 2 model), so the only variation is the sinusoid. We
restart thinning at each day boundary (where `λ_base` may jump).

```
function next_arrival(t, A, P, φ):
    while True:
        day = floor(t)
        next_boundary = day + 1
        λ_base = 24 / exp(linear_pred(day))
        λ_max = λ_base · (1 + A)
        u = uniform(0, 1)
        candidate = t + (-log(1 - u) / λ_max)
        if candidate ≥ next_boundary:
            t = next_boundary; continue
        u_accept = uniform(0, 1)
        ratio = (1 + A · sin(2π · candidate / P + φ)) / (1 + A)
        if u_accept ≤ ratio:
            return candidate - t_initial
        t = candidate
```

**Acceptance rate** is bounded by `1/(1 + A)` worst-case, so even at
`A = 0.75` we expect ≤ 1.75 candidates per accepted arrival.

**A = 0 fast path:** a single uniform draw with no acceptance step,
identical to Study 3e's `simulate_inter_arrival_time`. This guarantees
A = 0 cells are bit-for-bit identical to Study 3e at the same seed.

## Sanity checks

| Check | Pass condition |
|---|---|
| A=0 vs Study 3e | A=0, P=any: `arrivals_after_burnin` matches Study 3e at the same (ρ, rep) |
| Mean rate preserved | std(`arrivals_after_burnin`) across A < 1% of mean at fixed (P, ρ) |
| NPS ≡ LRTF (H5) | `\|orgNPS(NPS) − orgNPS(LRTF)\|` < 0.1 at all (A, P, ρ) |
| Cyclic-steady-state | `\|orgNPS_first_half − orgNPS_second_half\|` < 0.3 pp at all cells |
| Phase deterministic | Two reps with same seed at same (A, P) give identical arrivals |

## Stability concerns

At `A = 0.75`, peak rate is 1.75× the mean. With 6 agents at the paper
calibration (mean utilisation ~85% in Study 2), peaks push utilisation
past 1.0 — the queue grows during peaks. The system is only stable
across a full cycle if mean utilisation < 1.0 (which it is). The pilot
run `run_experiments.py --pilot` runs (A=0.75, P=28, FCFS) for 5 reps
and prints peak queue length to confirm the system doesn't blow up.

If pilot fails (queue grows monotonically without draining), drop
`A_max` to 0.50 in the final grid.

## Calibration

No new calibration. `results/calibration.json` and
`results/empirical_nps_multinomial.json` are copies of Study 3e's. We
are varying the *arrival process*, not the predictor or the NPS model.

## Honest caveats (to be repeated in `comparison_report.md`)

1. **Out-of-calibration regime.** The NPS model coefficients were
   estimated on data from a system with the existing arrival pattern.
   At `A = 0.75` we are well outside the original calibration. Findings
   should be framed as qualitative regime exploration, not point
   predictions of real-world organisational NPS.
2. **30-day burn-in.** Tight for P=28 (one full period). The
   cyclic-steady-state diagnostic flags cells where this is inadequate.
3. **Single agent count and intercept.** 6 agents, intercept=10.22.
   Cross with Study 3b's intercept axis is open.
4. **No SLA.** Consistent with Study 3 chain. A small SLA-cross
   sweep is an obvious follow-up.
