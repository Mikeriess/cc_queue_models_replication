# Study 3 (placeholder)

Denne mappe er reserveret til Study 3 — en udvidelse af analysen fra
Study 2. Specifikt formål og eksperimentelt design er endnu ikke defineret.

## Foreslåede retninger

Nogle naturlige udvidelser af Study 2:

1. **Sensitivitetsanalyse** af arrival rate, resource-effekter og throughput-model.
2. **Udvidet parameter-sweep:** flere SLA-niveauer (24h, 48h, 72h, 96h) og
   flere agent-niveauer (1-20).
3. **Alternative kødiscipliner:** weighted fair queuing, deadline-based
   scheduling, reinforcement learning-baseret prioritering.
4. **Preemptive vs. non-preemptive:** effekten af at tillade sagsafbrydelse.
5. **Heterogene agenter:** specialisering efter case topic.
6. **Dynamisk bemanding:** shift-baseret kapacitet der justeres over tid.
7. **Robusthed mod model-fejl:** hvad sker der hvis throughput-prædiktionen
   er systematisk skæv?

## Filstruktur

```
study3/
├── README.md            # Denne fil
├── Dockerfile           # Docker-setup (samme mønster som study2)
├── requirements.txt     # Python-afhængigheder
├── simulation.py        # Simuleringsmotor (placeholder)
├── run_experiments.py   # Eksperimentkørsel (placeholder)
└── results/             # Genereres ved kørsel
```

## Kørsel via Docker

Sæt `STUDY=study3` i `.env` i repo-roden, og kør:

```bash
docker compose up --build
```
