# Study 3b — Counterfactual Probe: Distribution Crossing Midpoint

Udvidelse af Study 3 der tester hypothesen:

> **NPS-prioritering divergerer fra LRTF når NPS_hat-fordelingen krydser
> midtpunktet 7.5** — fordi |NPS_hat − 7.5| da bliver V-formet og giver
> en fundamentalt anden rangorden end LRTF.

## Baggrund

Study 3 fandt at NPS ≡ LRTF over alle ρ-niveauer. Årsag: NPS_hat er en
monotont aftagende funktion af throughput, og med intercept = 10.22 er
NPS_hat > 7.5 for alle sager. Priority-scoren |NPS_hat − 7.5| er derfor
monoton — identisk rangorden som LRTF.

Study 3b tester om dette ændrer sig når interceptet sænkes.

## Eksperimentelt design

| Faktor | Niveauer |
|--------|----------|
| **NPS intercept** | 10.22 (original), 9.0, 8.0, 7.5 |
| **ρ** | 0.00, 0.22, 0.50, 0.85, 1.00 |
| **Sampling mode** | hard (kun) |
| **Disciplin** | FCFS, LRTF, NPS |
| **Agenter** | 6 (fikseret) |
| **Replikationer** | 100 |

**Total:** 4 × 5 × 1 × 3 × 1 × 100 = **6.000 runs**

## Forventet resultat

- **intercept = 10.22:** NPS = LRTF (replikerer Study 3)
- **intercept = 9.0:** NPS begynder at divergere marginalt
- **intercept = 8.0:** NPS_hat krydser 7.5 → V-formet priority → NPS ≠ LRTF
- **intercept = 7.5:** Maksimal divergens

Divergensen afhænger af ρ: ved ρ = 0 (ingen information) giver det tilfældig
sortering, men ved ρ = 0.85 (god prædiktion) er V-formen informativ.

## Kørsel

```bash
echo "STUDY=study3b" > .env
docker compose up --build
```

Eller lokalt:
```bash
cd study3b
python3 run_experiments.py --workers 8
python3 generate_plots.py
```
