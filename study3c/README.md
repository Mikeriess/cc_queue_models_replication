# Study 3c — Multi-Predictor NPS Model

Udvidelse af Study 3 / 3b der tester hypothesen:

> **NPS-prioritering divergerer fra LRTF når NPS-prædiktionsmodellen
> suppleres med topic-koefficienter** — fordi topic bryder den monotone
> afhængighed af predicted_throughput, så `|NPS_hat − 7.5|` ikke længere
> giver samme rangorden som LRTF.

## Baggrund

Study 3 fandt at NPS ≡ LRTF over alle ρ — fordi Eq. 9 er monoton i throughput
og NPS_hat > 7.5 for alle sager (intercept = 10.22).

Study 3b viste at man kan bryde NPS = LRTF ved at sænke interceptet (krydser
7.5-midtpunktet → V-formet priority). Maksimal effekt: +0.0375 individual NPS,
+1.39 organisation NPS — ved et ufysisk lavt intercept (≤ 8.75).

Study 3c angriber problemet fra en mere realistisk vinkel: i stedet for at
manipulere intercept, **udvider vi prædiktionsmodellen med topic-effekter**.
Det er en strukturel ændring i NPS-modellen, ikke en kunstig parametrisk
forskydning.

## Eksperimentelt design

| Faktor | Niveauer |
|--------|----------|
| **topic_aware** | False (Study 3 baseline), True (γ_topic = NPS_SIM_TOPIC_COEFS) |
| **NPS intercept** | 10.22 (baseline), 8.0 (Study 3b plateau-zone) |
| **ρ** | 0.0, 0.22, 0.5, 0.85, 1.0 |
| **Sampling mode** | hard |
| **Disciplin** | FCFS, LRTF, NPS |
| **Agenter** | 6 (kritisk load) |
| **Replikationer** | 100 |

**Total:** 4.000 LRTF/NPS runs (2 × 2 × 5 × 2 × 100) + 500 FCFS runs (FCFS er invariant
i topic_aware og intercept; køres kun for ét grid med alle ρ for paret seeding) = **4.500 runs**.

## Forventet resultat

| Betingelse | Forventning |
|---|---|
| topic_aware=False, intercept=10.22 | NPS = LRTF (replikerer Study 3) |
| topic_aware=False, intercept=8.0 | NPS > LRTF med +0.023-0.037 (replikerer Study 3b plateau) |
| **topic_aware=True, intercept=10.22** | **NPS > LRTF — primær test af H1** |
| topic_aware=True, intercept=8.0 | NPS > LRTF, formentlig størst effekt |

## Diagnostik

Tilføjelse af γ_topic øger variansen i NPS_hat. Det er en potentiel confound
(større spread → bedre sortering uafhængigt af topic-shape). Vi rapporterer
`Var(predicted_nps)` i hver celle (`fig_s3c_3_variance_diagnostic.pdf`) for at
kontrollere for dette. Hvis effekten er drevet af spread alene, så er fase 2
en varians-rekalibrering analogt med Study 3's `CALIBRATED_SCALING_FACTOR`.

## Kørsel via Docker

Fra repo-roden:

```bash
echo "STUDY=study3c" > .env
docker compose up --build
```

På servere med ældre Docker CLI:

```bash
DOCKER_API_VERSION=1.41 docker compose up --build -d
```

## Kørsel lokalt

```bash
# Smoke test (1 rep, 30 dage)
python3 simulation.py

# Quick mode (5 reps, 60 dage)
python3 run_experiments.py --quick

# Fuldt eksperiment
python3 run_experiments.py --workers 8

# Generér plots
python3 generate_plots.py
```

## Filstruktur

```
study3c/
├── README.md            # Denne fil
├── study3c.md           # Fuld plan og baggrundsdokumentation
├── Dockerfile
├── requirements.txt
├── simulation.py        # Fork af study3b med topic_aware-faktor
├── run_experiments.py   # 6.000-run grid
├── generate_plots.py    # 3 plots
└── results/
    ├── calibration.json # Kopieret fra study3b (samme kalibrering anvendes)
    ├── results.csv      # Genereres ved kørsel
    └── fig_s3c_*.pdf    # Output-plots
```

## Status

- [x] simulation.py med topic_aware-udvidelse
- [x] run_experiments.py
- [x] generate_plots.py
- [ ] Smoke test
- [ ] Fuldt eksperiment kørt
- [ ] comparison_report.md
