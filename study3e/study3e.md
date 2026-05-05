# Study 3e — Multinomial-shape sensitivity for rank-binned NPS prioritisation

**Plan and scope. Author: Riess. Date: 2026-05-05.**

## 1. Motivation

Study 3d showed that rank-binning the predicted NPS distribution to match the
empirical multinomial is the *first* intervention in our chain
(2 → 3 → 3b → 3c → 3d) that breaks NPS ≡ LRTF at the paper's actual
calibration (`intercept = 10.22`). The mechanism the paper attributes value
to is "prioritise predicted passives, convert them to promoters." Under the
empirical multinomial, only ~14.5 % of cases land in bins 7 + 8 (the
prioritised passive class), and ~62 % land in bin 10 (a large tied bulk
resolved by random tie-break).

Study 3d cannot disentangle three coexisting mechanisms:

1. **Passive-priority.** Cases binned to 7 / 8 are served first.
2. **Bulk-class size.** Cases binned to 10 form a large tied class
   resolved by random tie-break.
3. **Rank preservation.** Bin assignments are monotone in the raw
   `N̂PS` (and therefore in throughput).

Because the empirical multinomial fixes a single point in the
(passive-mass, bulk-mass) space, Study 3d cannot tell us *which* of these
mechanisms drives the observed NPS_BINNED − LRTF advantage, nor how
sensitive the advantage is to the chosen target shape.

This study (3e) systematically varies the *shape* of the target multinomial
while holding the rank-binning machinery and the rest of the simulation
fixed. The mode is held at 7.5 (symmetric between bins 7 and 8 — the
"passive-priority" zone), and the mass at the mode is swept from 0 % to
100 %. The remaining mass is distributed symmetrically over the other
nine bins.

## 2. Hypotheses

> **H1.** Organisation NPS for NPS_BINNED is non-monotone in `f` (the
> fraction of mass placed in bins 7 + 8). It rises with `f` from a
> baseline near LRTF as the prioritised passive class grows, then falls
> as the discipline collapses toward FCFS once `f` is large enough that
> too many cases tie at the top priority.

> **H2.** At `f = 0` (no mass in 7 + 8 → top priority class is empty,
> first-served class is bins 6 / 9), NPS_BINNED still beats LRTF on
> organisation NPS at high ρ, demonstrating that the value of
> rank-binning does **not** depend on explicit passive prioritisation.

> **H3.** At `f = 1` (all mass in 7 + 8 → every case ties at priority
> 0.5), NPS_BINNED reduces to FCFS within sampling error. Sanity check
> on the mechanism.

> **H4.** The argmax of organisation NPS over `f` is **larger** than the
> empirical share of bins 7 + 8 (0.145). The empirical multinomial is
> not the operationally optimal target for NPS-priority — it was chosen
> to match observed responses, not to maximise discipline performance.

Falsification criterion: if the org-NPS-vs-`f` curve is flat (i.e.
NPS_BINNED's advantage over LRTF is independent of target shape), all
four hypotheses are simultaneously falsified, and the conclusion is that
rank-binning's effect is structural-only — driven by ties-and-tie-breaking
rather than by the placement of the prioritised class.

## 3. Theoretical argument

### 3.1 What `f` controls

For target multinomial `p = (p₀ … p₁₀)` with mode at 7.5 and total mass
`f = p₇ + p₈`:

- **`f = 0.0`** — bins 7 + 8 are empty. Top priority class has size 0.
  First-served class is bins 6 + 9 (priority 1.5). NPS_BINNED still
  partitions cases into priority levels but skips the passive zone.
- **`f = 0.145`** — Study 3d's empirical baseline.
- **`f = 0.50`** — half of all cases are predicted passives. Top class
  is large; ties dominate within it.
- **`f = 1.0`** — every case has `predicted_nps_binned ∈ {7, 8}`,
  priority 0.5. All ties → random tie-break = stochastic FCFS-within-arrivals.

### 3.2 What we can decompose

If H1 holds (non-monotone curve with interior peak), the peak `f*`
quantifies the optimal *passive-priority budget* for this calibration.
The shape of the curve gives a clean decomposition:

- The slope at `f = 0` measures the marginal value of moving a case
  from "intermediate priority" to "top priority."
- The slope at `f = 1` measures the marginal cost of forcing
  more ties into the top class.
- The peak height (org NPS at `f*`) − LRTF org NPS measures the
  **maximum achievable advantage** of the rank-binning architecture
  under this calibration. If even the optimum is small, the discipline
  has limited theoretical headroom independent of which target is used.

### 3.3 What stays fixed

Rank preservation is by construction (Spearman = 1.000 for all `f`).
Eq. 8, Eq. 9, ρ levels, paired seeding, agents, intercept, SLA — all
unchanged from Study 3d. Only the target multinomial varies.

## 4. Experimental design

### 4.1 Factors

| Factor | Levels | Rationale |
|---|---|---|
| **Discipline** | FCFS, LRTF, SRTF, NPS, **NPS_BINNED** | Same set as 3d; FCFS/LRTF/SRTF/NPS results are invariant in `f` and reused across the sweep |
| **f** (mass at bins 7+8) | 0.00, 0.05, 0.10, 0.145, 0.20, 0.30, 0.50, 0.80, 1.00 | 9 levels, including empirical baseline |
| **ρ** | 0.0, 0.5, 1.0 | Reduced from 5 levels — Study 3d already mapped the ρ axis. Three points (no info / partial / perfect) suffice for sensitivity |
| **Sampling mode** | hard | Same as 3d |
| **Agents** | 6 | Critical-load setting |
| **NPS intercept** | 10.22 | Paper baseline |
| **SLA** | none | Study 2 showed SLA erases discipline differences |
| **Replications** | 100 | Standard |

### 4.2 Run count

- NPS_BINNED is the only discipline that depends on `f`:
  9 (f) × 3 (ρ) × 100 (rep) = **2,700 runs**
- FCFS / LRTF / SRTF / NPS depend only on ρ and replication (and FCFS not
  even on ρ). They are run **once** per (ρ, rep) and reused across `f`:
  4 × 3 × 100 = **1,200 runs**
- **Grand total: 3,900 runs.**

For comparison: Study 3d was 2,500 runs across 5 ρ × 5 disciplines × 100 reps.

### 4.3 Paired seeding

Inherited from Study 3d unchanged. `tie_break_key` drawn from
`rng_arrivals` is invariant in `f` and ρ — so a given case has the same
tie-break key whether `f = 0.05` or `f = 0.80`. Cross-`f` differences at
fixed (replication, ρ) are due *entirely* to the binning, not RNG drift.

### 4.4 Family of target distributions

The target multinomial is built from two parameters:

- **`f`**: total mass at bins 7 + 8. Split evenly between 7 and 8
  (so `p₇ = p₈ = f/2`).
- **Falloff shape on the remaining bins**: held fixed across `f` levels.

Default falloff: **uniform on the remaining 9 bins** (`p_k = (1−f)/9`
for `k ∈ {0,1,2,3,4,5,6,9,10}`). This is the cleanest choice — it
isolates the passive-mass effect from any specific tail shape.

We considered also varying the falloff (e.g. truncated geometric,
empirical-shape on tails), but for the *first* version of Study 3e,
the uniform-tail choice is the minimal-confounder design. A
follow-up Study 3e-shape can add tail-shape variation if needed.

The 9 target distributions will be saved at
`study3e/results/multinomials/p_f{f:.2f}.json`.

## 5. Method

### 5.1 Build target multinomial

```python
def build_target(f: float) -> list[float]:
    p = [0.0] * 11
    p[7] = f / 2
    p[8] = f / 2
    rest = (1 - f) / 9
    for k in (0, 1, 2, 3, 4, 5, 6, 9, 10):
        p[k] = rest
    assert abs(sum(p) - 1.0) < 1e-12
    return p
```

For `f = 0`, all mass is on the 9 non-passive bins (1/9 each ≈ 0.111).
For `f = 1`, all mass on bins 7 and 8 (0.5 each).

### 5.2 Apply rank-binning per (replication, ρ, f)

Identical to Study 3d's `apply_rank_binning(cases, target)` — only the
`target` argument changes between runs.

### 5.3 Discipline

`NPS_BINNED` is unchanged: priority `|predicted_nps_binned − 7.5|`,
ties broken by `tie_break_key`. The discipline definition does not
depend on `f`; only the bin assignments do.

## 6. Sanity checks

| Check | Pass criterion |
|---|---|
| **Rank preservation per `f`** | Spearman correlation between raw `N̂PS` and `predicted_nps_binned` = 1.000 for all 9 `f` levels |
| **Target conformance per `f`** | Per-rep histogram matches `p(f)` exactly modulo a single rounding leftover absorbed into bin 10 |
| **`f = 0` empty top class** | No case has `predicted_nps_binned ∈ {7, 8}` |
| **`f = 1` collapse** | Every case has `predicted_nps_binned ∈ {7, 8}`. NPS_BINNED org NPS within 1 SE of FCFS at every ρ |
| **`f = 0.145` reproduction** | NPS_BINNED at `f = 0.145` (≈ empirical) reproduces Study 3d's empirical-multinomial cell within MC noise |
| **FCFS / LRTF / SRTF / NPS invariance** | These four disciplines should match Study 3d cells at the matching ρ levels (we are reusing the same rng) |

## 7. Output and metrics

For each (discipline, ρ, replication, f):

**Standard** (inherited from 3d):
- `avg_individual_nps`, `organisation_nps`
- `avg_queue_length`, `avg_waiting_time_days`, `avg_capacity_utilisation`
- `percent_cases_closed`, `percent_cases_closed_last_335`
- `avg_case_resolution_time_days`
- `percent_detractors`, `percent_passives`, `percent_promoters`

**New in 3e:**
- `target_f`: the `f` value used for this run (NaN for FCFS/LRTF/SRTF/NPS)
- `top_class_size`: realised count of cases with priority = 0.5
- `bulk_class_size`: realised count of largest tied class

## 8. Plots

| File | Content |
|---|---|
| `fig_s3e_1_org_nps_vs_f.pdf` | **Headline.** Organisation NPS vs `f` for NPS_BINNED at three ρ levels; horizontal lines for LRTF / SRTF / FCFS reference. Argmax marked. |
| `fig_s3e_2_segment_shares_vs_f.pdf` | Three-panel: % detractors, % passives, % promoters vs `f` at ρ = 1.0 |
| `fig_s3e_3_advantage_vs_f.pdf` | NPS_BINNED − LRTF advantage vs `f`, one curve per ρ |
| `fig_s3e_4_target_distributions.pdf` | The nine target multinomials, faceted; visualises the design space |
| `fig_s3e_5_class_sizes_vs_f.pdf` | Top-priority class size and bulk-class size as functions of `f` (mechanism diagnostic) |
| `fig_s3e_6_operational_vs_f.pdf` | 2×2 panel: avg waiting time, avg resolution time, % closed, avg queue length vs `f` at ρ = 1.0 |

## 9. Expected outcomes

### 9.1 Three regime hypotheses

| Regime | Pattern | Interpretation |
|---|---|---|
| **Inverted U (H1 confirmed)** | Org NPS rises with `f` to an interior peak at `f* ∈ (0, 1)`, then falls toward FCFS at `f = 1`. Argmax `f*` likely in [0.15, 0.40] | Passive-priority mechanism is real and quantified. The empirical `f = 0.145` is operationally close-to-optimal but not optimal — possibly slightly underweighted. |
| **Monotone increasing** | Org NPS rises with `f` and asymptotes near `f = 1` | Implausible given H3 (collapse to FCFS at `f = 1`); would falsify our model of the mechanism. |
| **Flat** | Org NPS independent of `f` | Falsifies H1, H2, H4. Implies rank-binning's value is purely structural (ties + rank preservation), not about target shape. Would be the most surprising and most publishable result. |

### 9.2 Smoke-test prediction (informal)

At `f ≈ 0.30`, the top priority class doubles relative to empirical
(14.5 → 30 %), the bulk-bin-10 class drops from 62 % to ~13 %, and the
discipline now has more priority-class structure than Study 3d's
empirical version. We expect a small org-NPS *increase* over the
empirical baseline at ρ = 1.0 — but not a large one, because the
rank-binning ceiling is still bounded by ρ.

## 10. Implementation

Filed at `study3e/`. Mirrors Study 3d's structure:

```
study3e/
├── README.md                          # status + how-to-run
├── study3e.md                         # this document
├── Dockerfile, requirements.txt
├── simulation.py                      # fork of study3d/simulation.py
├── run_experiments.py                 # 3,900-run grid
├── generate_plots.py                  # 6 plots
└── results/
    ├── calibration.json               # copy from study3d
    ├── multinomials/                  # 9 saved target distributions
    │   ├── p_f0.00.json
    │   ├── ...
    │   └── p_f1.00.json
    ├── results.csv                    # output
    └── fig_s3e_*.pdf
```

### 10.1 Changes vs `study3d/simulation.py`

- **`apply_rank_binning`** signature unchanged — already takes a `target`
  argument. Just called with different targets per run.
- **`run_single_simulation()`**: accepts a `target_f: float | None`
  parameter; for FCFS/LRTF/SRTF/NPS this is `None` and the function
  ignores it; for NPS_BINNED, the target multinomial is built via
  `build_target(target_f)` and passed to `apply_rank_binning`.
- **Output dict**: adds `target_f`, `top_class_size`, `bulk_class_size`.
- **`run_experiments.py`**: outer loop over `f` for NPS_BINNED only;
  FCFS/LRTF/SRTF/NPS run once per (ρ, rep) and their results are
  written into all 9 `f` rows by replication.

No existing study (study2 / 3 / 3b / 3c / 3d) is modified.

### 10.2 Compute estimate

Study 3d ran 2,500 runs in ~3 h on Frigg. Study 3e is ~1.5× the runs
(3,900) and the per-run work is identical. Estimated wall time: **~5 h
on Frigg with the same worker count**. Quick mode (5 reps × 60 days)
should complete in under a minute.

## 11. Limitations and follow-ups

1. **Single intercept.** As in Study 3d, `intercept = 10.22` only.
   Whether the optimal `f*` shifts at lower intercepts is open.
2. **Uniform tail.** The 9-bin tail is uniform, not empirically shaped.
   A Study 3e-shape variant could vary the tail (truncated geometric vs
   empirical) at fixed `f` to disentangle tail-shape from passive-mass.
3. **Symmetric placement.** Mode at 7.5, with `p₇ = p₈ = f/2`. We do
   not test asymmetric placements (e.g. all `f` in bin 7, all `f` in
   bin 8). A natural follow-up since asymmetry corresponds to
   "prioritise low passives" vs "prioritise high passives."
4. **No SLA.** Same caveat as Study 3d.
5. **Random tie-break only.** ~`f` (top class) and ~max(p_k) (bulk) of
   cases tie. Deterministic tie-breaks (FCFS-within-class,
   SRTF-within-class) are the natural ablation — but belong in a
   separate study (3f-tiebreak) to keep this study's design clean.
6. **Reuse of FCFS/LRTF/SRTF/NPS results across `f`.** Defensible
   because these disciplines do not consume `predicted_nps_binned` —
   but worth a sanity check that the reused values match per-`f` reruns
   for one cell (e.g. ρ = 0.5, NPS at `f = 0.50` should match NPS at
   `f = 0.145`).

## 12. Status

- [ ] this plan document (`study3e.md`)
- [ ] `build_target(f)` + saved 9 multinomials at `results/multinomials/`
- [ ] `simulation.py` (fork of 3d) with `target_f` parameter
- [ ] `run_experiments.py` (3,900-run grid)
- [ ] `generate_plots.py` (6 plots)
- [ ] Smoke test (1 rep × 60 days × 9 f × 3 ρ)
- [ ] Quick mode (5 reps × 60 days)
- [ ] Full experiment on Frigg
- [ ] `comparison_report.md` after results land
- [ ] `Study3e_Report.md` for coauthor review
