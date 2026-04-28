# Study 3 — The Value of Information

Udvidelse af Study 2 der tester hypothesen:

> **NPS-baseret prioritering udkonkurrerer simple heuristikker (LRTF) når
> prædiktionsnøjagtigheden forbedres.**

Vi simulerer "value of information" ved at manipulere korrelationen mellem
prædikteret og faktisk throughput-tid via en latent kompleksitets-variabel Z.

Se [study3.md](study3.md) for den fulde plan og implementeringsdetaljer.

## Filstruktur

```
study3/
├── study3.md                 # Fuld implementeringsplan
├── README.md                 # Denne fil
├── Dockerfile
├── requirements.txt
├── simulation.py             # Fork af study2 med latent Z
├── calibrate_study3.py       # Pre-experiment kalibrering (Option C + BETA_Z)
├── sanity_check.py           # Verificér ρ=0 matcher Study 2
├── run_experiments.py        # Design loop (9.000 runs)
├── generate_plots.py         # Fig. S3.1 – S3.5
└── results/
    ├── calibration.json      # Kalibrerede parametre (committed)
    ├── results.csv           # Aggregerede metrikker (skrives ved kørsel)
    ├── daily_queue_lengths.csv  # Gitignored (stor fil)
    └── fig_s3_*.pdf          # Output-plots
```

## Eksperimentelt design

| Faktor | Niveauer |
|--------|----------|
| **ρ (prædiktionsnøjagtighed)** | 0.00, 0.22, 0.50, 0.85, 1.00 |
| **Sampling mode** | hard (alle aktiviteter ved Φ(z)), soft (z som feature) |
| **Kødisciplin** | FCFS, LRTF, NPS |
| **Antal agenter** | 5, 6, 7 |
| **SLA** | Ingen (Study 2 viste at SLA udligner forskelle) |
| **Replikationer** | 100 |

**Total:** 5 × 2 × 3 × 3 × 100 = **9.000 simulationskørsler**

## Kalibrering

Før eksperimentet køres to kalibreringer:

1. **CALIBRATED_SCALING_FACTOR** (Option C fra study3.md):
   Skalerer Eq. 9 koefficienten så variansen i `predicted_nps` matcher
   Study 2 baseline. Isolerer "information"-effekten fra varians-forskelle.

2. **BETA_Z** (soft mode feature-koefficient):
   Kalibreret så soft mode har korrelation 0.5 mellem `z_actual` og
   `log(duration)` — en moderat korrelation der gør z meningsfuld uden
   at være deterministisk.

Kalibrerede værdier gemmes i `results/calibration.json` og indlæses
automatisk af `simulation.py` ved import.

## Kørsel via Docker

Fra repo-roden, sæt `STUDY=study3` i `.env` og kør:

```bash
echo "STUDY=study3" > .env
docker compose up --build
```

På servere med ældre Docker CLI:

```bash
DOCKER_API_VERSION=1.41 docker compose up --build -d
```

Resultater skrives til `study3/results/` via volume mount.

## Kørsel lokalt

```bash
# 1. Kør kalibrering (kun nødvendigt én gang)
python3 calibrate_study3.py

# 2. Verificér at ρ=0 matcher Study 2
python3 sanity_check.py

# 3. Kør det fulde eksperiment
python3 run_experiments.py --workers 8

# 4. Generér plots
python3 generate_plots.py
```

## Forventet resultat

For hard mode, agents = 6:
- **FCFS:** Flad linje over ρ (uafhængig af prædiktionsnøjagtighed)
- **LRTF:** Let stigende — LRTF bruger kun rangorden
- **NPS:** Stejlt stigende fra medium til høj ρ — NPS udnytter hele
  prædiktionsinformationen

Hvis hypothesen bekræftes i både hard og soft mode, er fundet robust mod
den stærke "perfect activity correlation"-antagelse.

## Status

- [x] simulation.py med latent Z
- [x] calibrate_study3.py + calibration.json
- [x] sanity_check.py (ρ=0 passes tolerance for soft mode, hard mode har
      forventet artefakt dokumenteret i study3.md)
- [x] run_experiments.py
- [x] generate_plots.py
- [x] Fuldt eksperiment kørt (9.000 runs, results/results.csv)
- [x] comparison_report.md (hovedfund: NPS ≡ LRTF uanset ρ)
