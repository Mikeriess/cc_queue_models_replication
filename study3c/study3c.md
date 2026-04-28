# Study 3c — Multi-Predictor NPS Model: Plan og baggrund

## 1. Motivation

Tre studier ledte frem til denne plan:

- **Study 2** reproducerede artiklens kvalitative fund: NPS-prioritering > FCFS,
  marginal forskel mellem NPS og LRTF, SLA udligner.
- **Study 3** testede "Value of Information"-hypothesen ved at kontrollere
  prædiktionsnøjagtigheden ρ. Fund: NPS ≡ LRTF over alle ρ ∈ {0, 0.22, 0.5,
  0.85, 1.0} — fordi Eq. 9 er monoton i throughput og NPS_hat > 7.5 for
  alle sager.
- **Study 3b** brød ækvivalensen ved at sænke interceptet kunstigt så
  NPS_hat-fordelingen krydser 7.5. Resultat: skarp transition + plateau,
  maksimum +0.0375 individual NPS-fordel ved intercept ≤ 8.75 og ρ = 1.0.

Study 3's konklusion afsluttede med en eksplicit anbefaling:

> *"For at NPS-prioritering skal divergere fra LRTF, kræves en ikke-monoton
> NPS-model, fx en NPS-model med multiple prædiktorer (topic, agent,
> historik) der bryder monotonicitet."*

Study 3c implementerer netop dette — uden at falde tilbage på den kunstige
intercept-manipulation fra 3b.

## 2. Hypotese (H1)

> **H1:** Når NPS-prædiktionsmodellen suppleres med topic-koefficienter
> (γ_topic), bryder priority-funktionen `|NPS_hat − 7.5|` sin monotone
> afhængighed af predicted_throughput. NPS-prioritering vil derfor
> divergere fra LRTF allerede ved baseline-interceptet (α = 10.22), og
> divergensen vokser monotont med ρ.

**Falsifikation:** Hvis NPS−LRTF advantage forbliver ≈ 0 selv ved fuld
topic-information og ρ = 1.0, er hypothesen afvist.

## 3. Teoretisk argument

Den simulerede NPS-respons (Eq. 8) afhænger allerede af topic via
`NPS_SIM_TOPIC_COEFS` (range: −0.13 til +0.10). Eq. 9 ignorerer topic — en
modelmangel. Når vi tilføjer topic til Eq. 9:

```
NPS_hat = α + β·log(throughput+1) + γ_topic[topic] − 1
```

To sager med samme predicted_throughput men forskellig topic får forskellige
NPS_hat. Konsekvenser:

- Sortering efter `|NPS_hat − 7.5|` ≠ sortering efter throughput
- LRTF kan ikke replikere sortering (LRTF har kun adgang til
  predicted_throughput)
- NPS-disciplinen får asymmetrisk informationsfordel

Dette er den realistiske fortolkning af en to-trins NPS-model. En NPS-model
der kun bruger throughput er en degeneret specialtilfælde.

## 4. Eksperimentelt design

| Faktor | Niveauer | Begrundelse |
|---|---|---|
| **topic_aware** | False, True | False = Study 3 baseline; True = γ_topic = NPS_SIM_TOPIC_COEFS |
| **ρ** | 0.0, 0.22, 0.5, 0.85, 1.0 | Identisk med Study 3 → direkte sammenligning |
| **nps_intercept** | 10.22, 8.0 | 10.22 = baseline; 8.0 = Study 3b plateau-zone |
| **Disciplin** | FCFS, LRTF, NPS | Standard |
| **Agenter** | 6 | Kritisk load (Study 3b-konvention) |
| **Sampling mode** | hard | Study 3 viste soft bekræfter samme mønster |
| **SLA** | None | Som Study 3; SLA × multi-prædiktor er separat hypotese (H2) |
| **Replikationer** | 100 | Standard |

**Total:** 2 × 5 × 2 × 3 × 1 × 100 = **6.000 runs**.

### Faktoriel struktur

LRTF og NPS køres for hele krydset (2 × 2 × 5 = 20 celler × 100 reps × 2
discipliner = 4.000 runs). FCFS er invariant i topic_aware, intercept og ρ,
men køres for alle ρ-niveauer for at matche paret seeding (5 × 100 = 500
runs). Totalt 4.500 produktive runs + 1.500 redundante celler hvis vi kørte
fuldt grid for FCFS — vi kører et reduceret fcfs-grid for at spare tid.

Faktisk total: 2×2×5×2×100 (LRTF+NPS) + 5×100 (FCFS) = **4.500 runs**.

> Bemærk: dette afviger fra det estimat der står i README/study3c.md's
> hovedoverskrift (6.000). Den korrekte tælling er ovenstående 4.500.

### Paret seeding

`derive_seeds(replication, rho_idx)` arves fra Study 3b uændret. `topic_aware`
og `nps_intercept` påvirker kun deterministiske beregninger — ingen RNG-draw
er afhængig af dem.

## 5. Implementering

### Topic-koefficienter

Vi bruger `NPS_PRED_TOPIC_COEFS = NPS_SIM_TOPIC_COEFS` — dvs. perfekt
topic-information. Det er den mest optimistiske test af H1: hvis NPS ikke
slår LRTF her, vil ingen anden topic-prædiktor heller gøre det.

Hvis H1 bekræftes, kan en opfølgning teste støjede topic-prædiktorer
(γ_topic = α × NPS_SIM_TOPIC_COEFS + ε for α ∈ [0, 1]) for at kortlægge
hvor robust effekten er.

### Diagnostik: varians af predicted_nps

Topic-tilføjelsen øger variansen af NPS_hat. Dette er en potentiel
confound — større spread giver mere differentieret prioritering uafhængigt
af shape. Vi gemmer `Var(predicted_nps)` for hver simulation og rapporterer
det som diagnostik.

Hvis Var-stigningen er beskeden (< 50% af en ε), betragter vi shape-effekten
som veldefineret. Hvis variansen eksploderer, er en fase 2-rekalibrering
nødvendig (svarende til Study 3's CALIBRATED_SCALING_FACTOR-mekanisme).

## 6. Forventede resultater

| Cell | Forventet NPS − LRTF (indiv.) |
|---|---|
| topic_aware=False, intercept=10.22 | ≈ 0.000 (replikerer Study 3) |
| topic_aware=False, intercept=8.0   | +0.023 til +0.037 (replikerer 3b) |
| topic_aware=True, intercept=10.22 | **>0** — primær test |
| topic_aware=True, intercept=8.0    | Største effekt forventet |

### Sanity checks

- FCFS skal være invariant ift. topic_aware, intercept og ρ.
- LRTF skal være invariant ift. topic_aware (LRTF bruger ikke
  predicted_nps).
- NPS ved topic_aware=False, intercept=10.22 skal matche Study 3-resultater
  (NPS = LRTF, individual NPS ≈ 7.85).

## 7. Falsifikation og fortolkning

**Hvis H1 bekræftes:** Artiklens NPS-prioritering har reel værdi over LRTF
ved realistiske multi-prædiktor-modeller. Det rehabiliterer den
oprindelige tilgang og motiverer videre arbejde med rigere NPS-modeller.

**Hvis H1 afvises:** Selv en topic-bevidst NPS-model er ækvivalent med
LRTF. Det ville være et stærkt resultat, der tyder på at NPS-prioriteringens
unikke værdi kun realiseres under meget specifikke betingelser
(intercept-justering eller dybere strukturelle modelændringer).

I begge tilfælde er resultatet fagligt værdifuldt.

## 8. Opfølgningsmuligheder

1. **Støjet topic-information:** Variér γ_topic = α × NPS_SIM_TOPIC_COEFS
   for α ∈ {0, 0.25, 0.5, 0.75, 1.0}.
2. **Andre prædiktorer:** Tilføj agent-skill, kanal, kunde-historik som
   yderligere features.
3. **SLA-interaktion:** Test om SLA = 60h udsletter topic_aware-fordelen.
4. **Direkte estimeret prioritetsfunktion:** Træn en ML/RL-model der
   direkte optimerer NPS-respons, og brug den som upper bound.
