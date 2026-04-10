# Study 3 — Resultater: The Value of Information

**Data:** 9.000 simulationskørsler (5 ρ × 2 modes × 3 discipliner × 3 agenter × 100 reps).

---

## Hovedfund: NPS ≡ LRTF uanset prædiktionsnøjagtighed

**Hypotesen blev AFVIST.** NPS-prioritering divergerer IKKE fra LRTF ved
højere prædiktionsnøjagtighed. NPS og LRTF producerer **identiske resultater**
(forskel = 0.0000) på tværs af alle 5 ρ-niveauer, begge sampling modes og
alle 3 agent-niveauer.

### Individual NPS, hard mode, agents = 6

| ρ | FCFS | LRTF | NPS | NPS − LRTF |
|---|------|------|-----|-----------|
| 0.00 | 7.8227 | 7.8725 | 7.8725 | **0.0000** |
| 0.22 | 7.8227 | 7.8613 | 7.8613 | **0.0000** |
| 0.50 | 7.8227 | 7.8521 | 7.8521 | **0.0000** |
| 0.85 | 7.8227 | 7.8538 | 7.8538 | **0.0000** |
| 1.00 | 7.8227 | 7.8524 | 7.8524 | **0.0000** |

---

## Forklaring: Monotoni i NPS-modellen

Årsagen er fundamentalt strukturel. NPS-prædiktionsmodellen (Eq. 9) er:

```
NPS_hat = 10.2211 − 0.0949 × log(predicted_throughput + 1) − 1
```

Dette er en **monotont aftagende funktion** af predicted_throughput. Prioritetsscoren
(Eq. 1) er `|NPS_hat − 7.5|`, der er monoton i det regime hvor NPS_hat > 7.5.

Da langt de fleste sager har NPS_hat > 7.5 (fordi den gennemsnitlige NPS er
~8-9), producerer `|NPS_hat − 7.5|` den **samme rangorden** som predicted
throughput time. Sortering efter ascending `|NPS_hat − 7.5|` giver præcis
den samme kø-rækkefølge som sortering efter descending predicted_throughput
(= LRTF).

**Prædiktionsnøjagtigheden har ingen effekt**, fordi den monotone transformation
bevarer rangordenen uanset om prædiktionerne er støjede eller præcise. Mere
information giver bedre prædiktioner, men de bedre prædiktioner producerer
den samme sortering.

### Implikation for artiklen

Artiklen bemærker dette selv (s. 22-23): *"this second model is linear and does
not affect the priority order of the cases"* og *"a large majority of the cases
ended up on the same side of that mid-point"*.

Vores Study 3 formaliserer denne observation: **NPS ≈ LRTF er ikke en
artefakt af lav prædiktionsnøjagtighed — det er en strukturel konsekvens
af den monotone NPS-model.** For at NPS-prioritering skal divergere fra
LRTF, kræves en **ikke-monoton** NPS-model, fx:

- En NPS-model med multiple prædiktorer (topic, agent, historik) der bryder
  monotonicitet
- En NPS-model der producerer prædiktioner på begge sider af 7.5-midtpunktet
  med tilstrækkelig hyppighed
- En direkte estimeret prioritetsfunktion (fx via reinforcement learning)
  i stedet for en to-trinsprædiktion

---

## Sanity checks

### FCFS ρ-invariance ✅

FCFS er perfekt konstant over ρ (range = 0.0000), som forventet ved
paret seeding. Bekræfter at eksperimentet er korrekt sat op.

### NPS > FCFS holder stadig ✅

Trods NPS = LRTF har begge stadig en klar fordel over FCFS:

| Agents | NPS/LRTF − FCFS (hard, ρ=0) |
|--------|-----------------------------|
| 5 | +0.088 |
| 6 | +0.050 |
| 7 | +0.015 |

Forskellen aftager monotont med agenter — identisk med Study 2.

---

## Sekundære fund

### Resolution time stiger med ρ i hard mode

| ρ | FCFS | LRTF/NPS |
|---|------|----------|
| 0.00 | 17.1d | 8.0d |
| 0.50 | 17.1d | 9.4d |
| 1.00 | 17.1d | 10.9d |

Ved høj ρ vælger LRTF/NPS konsekvent de lange sager, og det tager længere
tid at lukke dem. FCFS er upåvirket.

### Ventetid stiger med ρ i hard mode

| ρ | FCFS | LRTF/NPS |
|---|------|----------|
| 0.00 | 7.6d | 32.0d |
| 0.50 | 7.6d | 34.5d |
| 1.00 | 7.6d | 36.9d |

Højere prædiktionsnøjagtighed giver LRTF/NPS bedre evne til at sortere
sager, men konsekvensen er at uprioriterede sager venter endnu længere.

### Soft mode bekræfter mønsteret

Soft mode (BETA_Z=0.285, korrelation 0.5 mellem z og duration) viser
det samme mønster: NPS = LRTF over alle ρ. Den lavere aktivitetskorrelation
ændrer intet ved det fundamentale monotoni-problem.

---

## Organisation NPS (hard mode, agents = 6)

| ρ | FCFS | LRTF/NPS |
|---|------|----------|
| 0.00 | 18.65 | 20.47 |
| 0.22 | 18.65 | 20.04 |
| 0.50 | 18.65 | 19.83 |
| 0.85 | 18.65 | 19.77 |
| 1.00 | 18.65 | 19.79 |

Organisation NPS falder svagt med stigende ρ for LRTF/NPS. Højere
prædiktionsnøjagtighed giver en marginal forringelse af organisation NPS
fordi de "korrekt prioriterede" lange sager skubbes længere bagerst i køen.

---

## Konklusion

Study 3 fandt at **NPS-prioritering er ækvivalent med LRTF under alle
testede prædiktionsnøjagtigheder**. Hypothesen — at NPS divergerer fra
LRTF ved højere ρ — er afvist. Årsagen er strukturel: Eq. 9's monotone
NPS-model bevarer rangordenen fra throughput-prædiktionen, og `|NPS − 7.5|`
sorteringen virker kun som tie-breaker når prædiktioner spænder over 7.5.

**Positiv implikation:** LRTF er en enklere, billigere algoritme end NPS.
Vores resultater bekræfter at LRTF er et fuldt substituerende alternativ
til NPS-prioritering i det nuværende setup.

**Fremtidig retning:** For at NPS-prioritering skal tilbyde en unik fordel
over LRTF, kræves en **ikke-monoton NPS-model** der producerer fundamentalt
anderledes rangordener end throughput-based prioritering.

---

## Genererede figurer

| Fil | Beskrivelse |
|-----|-------------|
| `results/fig_s3_1_nps_vs_rho.pdf` | Individual NPS vs ρ (3 agents × 2 modes) |
| `results/fig_s3_2_nps_advantage.pdf` | NPS − LRTF advantage vs ρ (diagnostisk) |
| `results/fig_s3_3_org_nps.pdf` | Organisation NPS vs ρ |
| `results/fig_s3_4_resolution_time.pdf` | Case resolution time vs ρ |
| `results/fig_s3_5_waiting_time.pdf` | Waiting time vs ρ |
