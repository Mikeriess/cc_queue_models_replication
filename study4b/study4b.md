# Study 4b — Plan and design rationale

## Motivation

Study 4 confirmed two things:
- **Diagnosis correct:** Priority disciplines extract more value under
  non-stationary load. FCFS−best gap grew from +2.45 (A=0) to +3.4 pp
  (A=0.75) at ρ_thr=1, P=28.
- **Algorithm ceiling unchanged:** SRTF and NPS_BINNED stayed tied
  within MC noise. NPS ≡ LRTF exactly. The non-stationary load amplified
  the existing structure but did not unlock new differentiation.

Study 3c established that adding a topic term to Eq. 9 is one way to
break the throughput-monotonicity of `|N̂PS − 7.5|`. But at the paper's
intercept (10.22), the effect was small (Study 3c: small at intercept
10.22, larger at intercept 8.0). Open question: does combining
topic-awareness with the larger queue dynamics of Study 4 produce a
meaningful effect at the paper baseline?

## The ρ_topic mechanism

The throughput-ρ axis is implemented as a Gaussian correlation that
preserves the marginal distribution of the predictor while reducing its
correlation with the actual value. The natural categorical analog:

```
predicted_topic =
    actual_topic        with probability ρ_topic
    Uniform(CASE_TOPICS) with probability (1 − ρ_topic)

predicted_nps = intercept + β · log(predicted_throughput + 1)
                + NPS_PRED_TOPIC_COEFS[predicted_topic] − 1
```

`NPS_PRED_TOPIC_COEFS = NPS_SIM_TOPIC_COEFS` — the predictor knows the
true topic *effects*, but may be wrong about which topic a case has.
This isolates "topic accuracy" from "coefficient knowledge".

### Properties

- ρ_topic = 0 → no topic term (RNG never consumed; bit-identical to
  Study 4 paired seeding).
- ρ_topic = 1 → perfect topic info (matches Study 3c topic_aware=True).
- Effective accuracy at ρ_topic = 0.5 is 0.55 (0.5 on purpose + 0.5/10
  by chance from uniform draw over 10 topics).

### Paired seeding

A dedicated `rng_topic_pred` stream is added to `derive_seeds()`, keyed
only on replication (not ρ_topic_idx). The same case at the same
(rep, A, P, ρ_throughput) gets the same coin flips for "is the topic
prediction correct" across ρ_topic levels. This makes within-rep
comparisons across ρ_topic clean.

## What about variance confound?

Var(predicted_nps) grows with ρ_topic because the topic term contributes
its own variance to the predictor. This is a known confound — Study 3c
flagged it as the rationale for the CALIBRATED_SCALING_FACTOR mechanism.

We do **not** rescale the throughput coefficient here. Instead, we
report `Var(predicted_nps)` as a diagnostic alongside results, so a
reader can judge whether observed effects on org NPS scale with
information content (the substantive question) or with predictor
variance (a mechanical confound).

The topic coefficient range is small (±0.13), so the variance
contribution is bounded. Empirically the confound should be modest.

## Hypotheses (testable with this design)

### H4b.1 — Topic breaks NPS ≡ LRTF

At ρ_topic = 0, `|N̂PS − 7.5|` is monotone in throughput and ranks cases
identically to LRTF. At ρ_topic > 0, topic enters the predictor; cases
with the same throughput but different (predicted) topics get different
NPS_hat. **Prediction:** `|orgNPS(NPS) − orgNPS(LRTF)|` grows with
ρ_topic.

### H4b.2 — NPS_BINNED unlocks at high ρ_topic and high A

Study 3e showed that rank-binning's value comes from coarsening +
random tie-breaking, not from explicit passive prioritisation. With a
non-monotone underlying predictor (topic-aware), the rank-binning's
*coarsening step* operates on a *different ordering* than throughput.
Combined with Study 4's queue-dynamics amplification, this might be
where NPS_BINNED finally pulls ahead of SRTF.

**Prediction:** `orgNPS(NPS_BINNED) − orgNPS(SRTF)` increases with
ρ_topic at A ≥ 0.50.

### H4b.3 — Monotone in ρ_topic

If the topic signal is genuinely informative, more accurate topic info
should monotonically improve any topic-aware discipline (NPS and
NPS_BINNED).

### H4b.4 — Effect size bound

Topic coefficients span ±0.13. The maximum impact on `|N̂PS − 7.5|`
from a perfect topic predictor (at ρ_topic = 1) is one topic shift in
the predictor, ~0.26 in NPS_hat. This is small relative to the
inter-discipline gaps Study 4 found (typically ~1–2 pp org NPS). So we
expect the *direction* to confirm H4b.1–3 but the *magnitude* to be
small.

## Why include ρ_topic = 0.0 in the grid?

It is mathematically equivalent to Study 4 (no topic term). Including
it gives:
- A within-study baseline that doesn't require cross-CSV joins
- Paired seeding for `Δ` plots across ρ_topic
- A trivial sanity check (any ρ_topic = 0 cell should match Study 4
  within MC noise)

The extra cost is one third of the total run-count, which is the
acceptable price for a self-contained experiment.

## Expected runtime

Study 4 was 8,000 runs. Study 4b is 24,000 runs — 3× the compute. Given
the same per-run cost (~equal model complexity), expected runtime is
about 3× Study 4's wall-clock. The added complexity per run (one extra
RNG, one categorical draw, one dict lookup) is negligible.

## Honest caveats (carry-over from Study 4)

1. **Mean-rate discrepancy at A=0 vs A>0** (~9% more arrivals at A>0
   from the thinning sampler vs original Study 3e sampler). Within
   fixed A, comparisons are clean.
2. **Cyclic-steady-state at A=0.25–0.5, P=14** — burn-in tight; flag
   in sanity check.
3. **Calibration drift** — NPS coefficients fit on stationary data;
   extrapolation at A=0.75 is qualitative.

## New caveats specific to Study 4b

1. **"Perfect coefficient knowledge"** — the predictor knows the true
   `NPS_PRED_TOPIC_COEFS`. A real-world predictor would have to
   estimate them, introducing further noise. ρ_topic isolates the
   "which topic" accuracy question.
2. **Random-uniform fallback at ρ_topic = 0.5/0.0** — predicting a
   uniformly-random topic adds noise to predicted_nps that is not
   informative. This is realistic for a poorly-trained classifier but
   may underestimate what a real "moderate" predictor would do (which
   would have biased errors).
3. **No interaction with intercept** — fixed at 10.22 (paper baseline)
   throughout. Cross with Study 3b's intercept axis is a Study 4c
   question.
