# Eksperimentelt design og resultater

## Monte Carlo-simulering

**Monte Carlo-simulering** er en metode hvor man gentager et stokastisk (tilfældigt) eksperiment mange gange for at estimere forventede værdier og usikkerhed. I stedet for at løse et problem analytisk lader vi computeren "spille" scenariet igennem tusindvis af gange og observerer fordelingen af udfald.

I Study 3 kører vi simulationen **100 gange per betingelse** med forskellige random seeds. For hver betingelse beregner vi:

- **Gennemsnit** over de 100 replikationer $\to$ estimat for den forventede værdi
- **Standardafvigelse** $\to$ estimat for usikkerheden
- **Konfidensintervaller** $\to$ intervaller der med høj sandsynlighed indeholder den sande værdi

Hvorfor 100? Det er en afvejning: nok til at få stabile estimater og smalle konfidensintervaller, men ikke så mange at kørselstiden bliver uhåndterbar (9.000 kørsler i alt).

---

## Fuldt faktorielt design

Study 3 bruger et **fuldt faktorielt design**: vi tester *alle* kombinationer af alle faktorer.

### Faktorer

| Faktor | Niveauer | Beskrivelse |
|--------|----------|-------------|
| $\rho$ (prædiktionsnøjagtighed) | 5: $\{0.00, \; 0.22, \; 0.50, \; 0.85, \; 1.00\}$ | Korrelation mellem prædikteret og faktisk kompleksitet |
| Sampling mode | 2: $\{\text{hard}, \; \text{soft}\}$ | Hvordan $Z_{\text{actual}}$ påvirker varigheder (se kapitel 3) |
| Kødisciplin | 3: $\{\text{FCFS}, \; \text{LRTF}, \; \text{NPS}\}$ | Prioriteringsalgoritme |
| Antal agenter | 3: $\{5, \; 6, \; 7\}$ | Kapacitet i servicecentret |
| Replikation | 100 | Antal Monte Carlo-gentagelser |

### Totalt antal kørsler

$$5 \times 2 \times 3 \times 3 \times 100 = 9{,}000 \text{ simulationskørsler}$$

Hvert kørsel simulerer et helt servicecenter over en flerarig periode med hundredvis af sager. Det fulde eksperiment producerer et komplet billede af hvordan alle faktorer og deres interaktioner påvirker udfaldet.

---

## Paret seeding --- variansreduktion

### Problemet

I Monte Carlo-simulering introducerer tilfældig variation (støj) usikkerhed i vores estimater. Når vi sammenligner to betingelser --- fx NPS ved $\rho = 0$ vs $\rho = 1$ --- kan støj fra sagsankomster, Weibull-varigheder og Markov-kæder sløre den sande forskel.

### Løsningen: paret seeding

Tricket er at bruge **de samme random seeds** for alt der *ikke* skal variere mellem betingelser, og kun lade den relevante støjkilde variere. Konkret:

| Random number generator | Kontrol | Varierer med $\rho$? |
|------------------------|---------|-----------------------|
| `rng_arrivals` | Sagsankomster (tidspunkter, topics) | **Nej** --- identiske sager |
| `rng_actual` | Faktisk sagskompleksitet ($Z_{\text{actual}}$) | **Nej** --- samme virkelighed |
| `rng_pred_noise` | Prædiktionsstøj ($\varepsilon$) | **Ja** --- ændres med $\rho$ |
| `rng_simulation` | NPS-sampling, agenteffekter, Markov-overgange | **Nej** --- identisk simulation |

### Seed-derivering

For at sikre reproducerbarhed og uafhængighed af seeds beregnes de systematisk:

```
base        = hash("study3", replication_number)
arrivals    = base + 1.000.000
actual      = base + 2.000.000
pred_noise  = base + 3.000.000 + rho_idx
simulation  = base + 4.000.000
```

Bemærk: `pred_noise` er den *eneste* seed der afhænger af `rho_idx`. Alle andre seeds er identiske på tværs af $\rho$-niveauer.

### Effekt

Sammenligningen "NPS ved $\rho = 0$ vs NPS ved $\rho = 1$" bruger **præcis de samme sager** med de samme ankomsttider, topics, kompleksiteter og agenteffekter. Kun prædiktionsnøjagtigheden ændres. Denne teknik giver en **dramatisk reduktion i varians** og gør det muligt at opdage selv meget små forskelle.

Det er det simulationsmæssige ækvivalent af et **paired $t$-test**: vi sammenligner matched pairs i stedet for uafhængige stikprøver.

---

## Sanity checks

Før vi fortolker resultaterne, validerer vi at eksperimentet er korrekt opsat med to centrale sanity checks.

### FCFS $\rho$-invarians

**Test:** FCFS (First Come First Served) bruger *ikke* prædiktioner --- sager betjenes i ankomstrækkefølge. Derfor skal FCFS-resultater være **identiske** over alle $\rho$-niveauer.

**Resultat:** Range i individual NPS for FCFS over alle $\rho$ = **0.0000**. $\checkmark$

Forklaring: Paret seeding sikrer at FCFS ser præcis de samme sager med de samme varigheder uanset $\rho$. Prædiktionerne (som varierer med $\rho$) bruges aldrig af FCFS. Denne invarians bekræfter at seed-designet fungerer korrekt.

### $\rho = 0$ vs Study 2

**Test:** Ved $\rho = 0$ er prædiktionerne ren støj --- svarende til Study 2's tilfældige prædiktioner. Study 3 ved $\rho = 0$ skal derfor matche Study 2's resultater.

**Acceptkriterier:**

| Metric | Tolerance |
|--------|-----------|
| Queue length | $\pm 10\%$ |
| Organisation NPS | $\pm 1$ |
| % closed cases | $\pm 2$ procentpoint |

Begge sanity checks bestås, hvilket giver os tillid til at eksperimentet er korrekt implementeret.

---

## Resultater

### Hovedfund: NPS $\equiv$ LRTF over alle betingelser

**Hypotesen blev AFVIST.** NPS-prioritering divergerer *ikke* fra LRTF ved højere prædiktionsnøjagtighed. NPS og LRTF producerer **identiske resultater** med en forskel på præcis 0.0000 --- på tværs af alle 5 $\rho$-niveauer, begge sampling modes og alle 3 agent-niveauer.

Eksempel (hard mode, 6 agenter):

| $\rho$ | FCFS | LRTF | NPS | NPS $-$ LRTF |
|--------|------|------|-----|--------------|
| 0.00 | 7.8227 | 7.8725 | 7.8725 | **0.0000** |
| 0.22 | 7.8227 | 7.8613 | 7.8613 | **0.0000** |
| 0.50 | 7.8227 | 7.8521 | 7.8521 | **0.0000** |
| 0.85 | 7.8227 | 7.8538 | 7.8538 | **0.0000** |
| 1.00 | 7.8227 | 7.8524 | 7.8524 | **0.0000** |

### FCFS-invarians bekræftet

FCFS er perfekt konstant over alle $\rho$ (range = 0.0000), som forventet ved paret seeding.

### NPS/LRTF > FCFS holder stadig

Trods ækvivalensen mellem NPS og LRTF har begge stadig en klar fordel over FCFS:

| Agenter | NPS/LRTF $-$ FCFS (hard, $\rho = 0$) |
|---------|---------------------------------------|
| 5 | $+0.088$ |
| 6 | $+0.050$ |
| 7 | $+0.015$ |

Fordelen aftager med flere agenter --- identisk med Study 2. Med tilstrækkelig kapacitet forsvinder kødisciplinens betydning.

### Resolution time stiger med $\rho$ for LRTF/NPS

| $\rho$ | FCFS | LRTF/NPS |
|--------|------|----------|
| 0.00 | 17.1 dage | 8.0 dage |
| 0.50 | 17.1 dage | 9.4 dage |
| 1.00 | 17.1 dage | 10.9 dage |

Ved høj $\rho$ vælger LRTF/NPS konsekvent de lange sager, og det tager længere tid at lukke dem. FCFS er upåvvirket.

### Ventetid stiger med $\rho$ for LRTF/NPS

| $\rho$ | FCFS | LRTF/NPS |
|--------|------|----------|
| 0.00 | 7.6 dage | 32.0 dage |
| 0.50 | 7.6 dage | 34.5 dage |
| 1.00 | 7.6 dage | 36.9 dage |

Højere prædiktionsnøjagtighed giver LRTF/NPS bedre evne til at sortere sager, men konsekvensen er at uprioriterede sager venter endnu længere.

### Organisation NPS falder svagt med $\rho$ for LRTF/NPS

| $\rho$ | FCFS | LRTF/NPS |
|--------|------|----------|
| 0.00 | 18.65 | 20.47 |
| 0.22 | 18.65 | 20.04 |
| 0.50 | 18.65 | 19.83 |
| 0.85 | 18.65 | 19.77 |
| 1.00 | 18.65 | 19.79 |

Højere prædiktionsnøjagtighed giver en marginal forringelse af organisation NPS for LRTF/NPS, fordi de "korrekt prioriterede" lange sager skubbes længere bagerst i køen.

---

## Konklusion

NPS-prioritering er **strukturelt ækvivalent** med LRTF pga. Eq. 9's monotonicitet (se kapitel 5 for det fulde bevis). Hypothesen --- at NPS divergerer fra LRTF ved høj $\rho$ --- er **afvist**.

### Implikation

**LRTF er en enklere, billigere algoritme med identisk effekt.** Den kræver ingen NPS-prædiktionsmodel, ingen machine learning, og ingen feature engineering. Den sorterer blot sager efter forventet behandlingstid --- og producerer præcis den samme kørækkefølge som den langt mere komplekse NPS-baserede prioritering.

### Fremtidig retning

For at NPS-prioritering skal tilbyde en *unik* fordel over LRTF, kræves en **ikke-monoton NPS-model** --- fx:

- En model med multiple prædiktorer (topic, agenthistorik, kundehistorik) der bryder den monotone sammenhæng med throughput
- En model der producerer prædiktioner på *begge sider* af 7.5-midtpunktet med tilstrækkelig hyppighed
- En direkte estimeret prioritetsfunktion (fx via reinforcement learning) i stedet for en to-trinsprædiktion (prædiker NPS $\to$ beregn prioritet)
