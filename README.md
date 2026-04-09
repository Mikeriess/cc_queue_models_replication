# CC Queue Models — Reproduktionsarbejde

Reproduktioner og udvidelser af Monte Carlo-kø-simuleringer fra
Riess & Scholderer (2026), "Customer-service queuing based on predicted
loyalty outcomes".

## Struktur

```
cc_queue_models_replication/
├── .env                  # Vælger hvilket studie docker compose kører
├── docker-compose.yml    # Top-level orchestration
├── study2/               # Reproduktion af artiklens Study 2
│   ├── simulation.py
│   ├── run_experiments.py
│   ├── generate_plots.py
│   ├── comparison_report.md
│   ├── CALIBRATION_NOTES.md
│   ├── Dockerfile
│   ├── requirements.txt
│   └── results/          # Output fra kørsel (CSV + PDF-figurer)
└── study3/               # Udvidelse/opfølgning (placeholder)
    ├── README.md
    ├── simulation.py
    ├── run_experiments.py
    ├── Dockerfile
    └── requirements.txt
```

## Kørsel

1. Vælg studie ved at redigere `.env`:

   ```bash
   echo "STUDY=study2" > .env   # eller STUDY=study3
   ```

2. Byg og kør:

   ```bash
   docker compose up --build
   ```

   På servere med ældre Docker CLI:

   ```bash
   DOCKER_API_VERSION=1.41 docker compose up --build -d
   ```

3. Resultater skrives automatisk til `${STUDY}/results/` via volume mount.

## Study 2 — status

Fuldt reproduceret. Alle 8 hovedpåstande fra artiklen er bekræftet.
Se [study2/comparison_report.md](study2/comparison_report.md) for detaljer
og [study2/CALIBRATION_NOTES.md](study2/CALIBRATION_NOTES.md) for
implementeringsnoter.

## Study 3 — status

Placeholder. Se [study3/README.md](study3/README.md) for foreslåede retninger.
