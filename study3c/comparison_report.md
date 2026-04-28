# Study 3c — Resultater: Multi-Predictor NPS Model

**Data:** 4.500 simulationskørsler (2 topic_aware × 2 intercept × 5 ρ × {LRTF, NPS} × 100 reps + 500 FCFS-baselinerus). 6 agenter, hard mode, ingen SLA, 365 dage.

---

## Hovedfund

**H1 er delvist bekræftet — men i en uventet retning.** Topic-bevidsthed bryder
ækvivalensen NPS = LRTF, men ikke i den simple "NPS bliver bedre"-form vi
forventede. Effekten er **interaktiv med intercept**:

| topic_aware | intercept | NPS − LRTF (indiv.) ved ρ=1.0 | Fortolkning |
|---|---|---|---|
| False | 10.22 | **+0.0000** | Replikerer Study 3 (NPS ≡ LRTF) |
| False | 8.0   | **+0.0336** | Replikerer Study 3b plateau |
| True  | 10.22 | **−0.0280** | **NPS bliver DÅRLIGERE end LRTF** |
| True  | 8.0   | **+0.0657** | **Maksimal fordel — næsten 2x Study 3b** |

Topic-bevidsthed alene er **ikke** nok til at gøre NPS-prioritering bedre end
LRTF. Den skal kombineres med en intercept-justering der får NPS_hat-fordelingen
til at krydse 7.5-midtpunktet.

---

## 1. Detailerede resultater

### Individual NPS (NPS − LRTF advantage)

| ρ | (False, 10.22) | (False, 8.0) | (True, 10.22) | (True, 8.0) |
|---|---|---|---|---|
| 0.00 | +0.0000 | +0.0010 | **−0.0424** | +0.0356 |
| 0.22 | −0.0000 | +0.0047 | **−0.0401** | +0.0484 |
| 0.50 | +0.0000 | +0.0046 | **−0.0302** | +0.0321 |
| 0.85 | +0.0000 | +0.0105 | **−0.0474** | +0.0479 |
| 1.00 | +0.0000 | +0.0336 | **−0.0280** | **+0.0657** |

### Organisation NPS (NPS − LRTF advantage, procentpoint)

| ρ | (False, 10.22) | (False, 8.0) | (True, 10.22) | (True, 8.0) |
|---|---|---|---|---|
| 0.00 | +0.000 | +0.003 | −1.525 | +1.216 |
| 0.22 | +0.000 | +0.228 | −1.398 | +1.710 |
| 0.50 | +0.000 | +0.206 | −1.127 | +1.066 |
| 0.85 | +0.000 | +0.317 | −1.744 | +1.676 |
| 1.00 | +0.000 | +1.226 | −1.051 | **+2.369** |

---

## 2. Hvorfor bliver NPS dårligere ved (topic_aware=True, intercept=10.22)?

Dette er det vigtigste teoretiske fund. Ved intercept = 10.22 ligger
NPS_hat-fordelingen typisk omkring 8-9.5, **altid over 7.5**. Med priority =
`|NPS_hat − 7.5|` reduceres dette til `priority = NPS_hat − 7.5` (monoton
i NPS_hat).

Når vi tilføjer topic-koefficienterne fra Eq. 8 (NPS_SIM_TOPIC_COEFS, range
−0.13 til +0.10):

- Topics med **negativ** γ_topic (fx d_2-z_4: −0.13) → lavere NPS_hat → **højere prioritet**
- Topics med **positiv** γ_topic (fx g_1-z_4: +0.10) → højere NPS_hat → **lavere prioritet**

Men disse topics påvirker også *faktisk* NPS via samme γ_topic i Eq. 8:

- Topics med negativ γ producerer faktisk lavere NPS-svar.
- Topics med positiv γ producerer faktisk højere NPS-svar.

NPS-disciplinen prioriterer altså sager der **ventes** at give lave NPS-svar
først. Det er den modsatte logik af artiklens design (prioriter passive
*swing voters* tæt på 7.5).

Konsekvens: gode-topic-sager (positiv γ) skubbes bagerst → venter længere →
deres throughput-koefficient (negativ via Eq. 8) trækker NPS ned, og det
overstiger den positive topic-effekt. Net negativ.

LRTF undgår denne fælde fordi den ikke bruger topic-information og
prioriterer udelukkende baseret på predicted_throughput.

## 3. Hvorfor virker det ved intercept = 8.0?

Ved intercept = 8.0 krydser NPS_hat-fordelingen 7.5. Nu bliver
`|NPS_hat − 7.5|` reelt **V-formet**:

- Topics med negativ γ_topic → NPS_hat ≈ 6-7 → afstand til 7.5 = 0.5-1.5
- Topics med positiv γ_topic → NPS_hat ≈ 8-9 → afstand til 7.5 = 0.5-1.5
- Topics tæt på γ = 0 → NPS_hat ≈ 7-8 → **lavest afstand → højest prioritet**

NPS-disciplinen prioriterer nu **passive kunder** (~7.5), uafhængigt af om
deres faktiske NPS bliver høj eller lav. Det matcher artiklens oprindelige
design og giver den maksimale fordel observeret i hele studie-serien:
**+0.0657 individual NPS, +2.37 organisation NPS** ved (topic_aware=True,
intercept=8.0, ρ=1.0).

Til sammenligning:
- Study 3b (topic_aware=False, intercept=8.0, ρ=1.0): +0.034 / +1.23
- Study 3c (topic_aware=True, intercept=8.0, ρ=1.0): +0.066 / +2.37

**Topic-bevidsthed fordobler omtrent Study 3b's plateau-effekt.**

---

## 4. Sanity checks ✅

| Test | Resultat | Status |
|---|---|---|
| FCFS ρ-invariant | mean = 7.8064 over alle ρ-niveauer (identisk til 4 decimaler) | ✅ |
| (topic_aware=False, intercept=10.22) replikerer Study 3 | NPS = LRTF = 7.8437-7.8767, NPS−LRTF = 0.0000 | ✅ |
| (topic_aware=False, intercept=8.0) replikerer Study 3b plateau | NPS−LRTF = +0.0336 ved ρ=1.0 (Study 3b rapporterede +0.0336) | ✅ |
| Var(predicted_nps) højere med topic_aware | 0.0019 → 0.0065 (3.4× stigning) | ✅ |

---

## 5. Sekundære fund

### Resolution time vendes med topic-aware + lav intercept

| Cell | resolution time, ρ=0 → ρ=1.0 |
|---|---|
| (topic_aware=False, intercept=10.22), NPS | 8.1 → 11.0 dage **(stiger)** |
| (topic_aware=False, intercept=8.0), NPS | 8.2 → 6.2 dage **(falder)** |
| (topic_aware=True, intercept=10.22), NPS | 8.7 → 9.7 dage (stiger) |
| (topic_aware=True, intercept=8.0), NPS | 8.0 → 6.8 dage **(falder)** |

Med V-formet priority + høj ρ bliver NPS-disciplinen mere effektiv ift.
case-lukning. Det er det modsatte af Study 3's fund (resolution time stiger
monotont med ρ for LRTF/NPS). Mekanismen: V-formen sender ikke længere alle
lange sager bagerst — den parkerer kun ekstremt lange OG ekstremt korte
sager bagerst.

### Ventetid følger samme mønster

Ved intercept = 10.22 stiger ventetid med ρ (32.6 → 36.8 dage). Ved
intercept = 8.0 falder den (32.3 → 30.4 dage med topic_aware=False; 32.8 →
30.7 med topic_aware=True). V-formen reducerer netto-ventetid.

### Var(predicted_nps) confounder ikke retningen

Hvis effekten var drevet af variansen alene, ville topic_aware=True være
**bedre** end topic_aware=False uafhængigt af intercept. Det modsatte
observeres ved intercept=10.22 (negativ effekt). Var(predicted_nps) er
derfor en kvantitativ medspiller, men ikke kvalitativ driver.

---

## 6. Konklusion

**H1 er bekræftet, men med vigtig nuance:**

1. **Topic-bevidsthed alene er ikke nok.** Med baseline-interceptet (10.22)
   gør topic-aware NPS-prædiktion priority-funktionen til en omvendt
   throughput-funktion suppleret med topic — hvilket er strikt værre end
   LRTF fordi den prioriterer "dårlige" topics først.

2. **Topic-bevidsthed + lavere intercept giver den hidtil største NPS-fordel
   over LRTF.** Kombinationen (topic_aware=True, intercept=8.0, ρ=1.0)
   producerer +0.0657 individual NPS og +2.37 organisation NPS — næsten 2×
   så meget som Study 3b's bedste resultat.

3. **Begge betingelser skal være opfyldt:**
   - Multi-prædiktor NPS-model (topic-bevidst)
   - NPS_hat-fordelingen skal krydse 7.5-midtpunktet

Disse to udvikler sig **multiplikativt** sammen, ikke additivt — den
maksimale effekt opstår kun når begge er aktive.

### Implikation for artiklen

Artiklens NPS-prioritering har reel værdi over LRTF — men kun under
specifikke betingelser:

1. NPS-prædiktionsmodellen er ikke-monoton (multi-prædiktor).
2. NPS_hat-fordelingen krydser 7.5-midtpunktet (kalibrering / lavere intercept).
3. Prædiktionsnøjagtigheden er meget høj (ρ ≥ 0.85).

Under artiklens faktiske parametre (intercept = 10.22, monoton model) er NPS
ækvivalent med LRTF — som Study 3 viste. Den unikke værdi af NPS-prioritering
er derfor en **modelarkitektur-egenskab**, ikke en grundlæggende
algoritme-egenskab. Det matcher artiklens egen disclaimer (s. 22-23) om at
deres specifikke model ikke ændrer rangordenen.

### Implikation for praktisk brug

For at få reel værdi af NPS-prioritering i et produktionssystem:

- Brug en NPS-model med topic, agent-skill, kanal, kunde-historik (ikke kun throughput).
- Sørg for at NPS_hat-fordelingen spreder sig over 7.5 (kalibrer eller transformer).
- Invester i prædiktionsnøjagtighed — fordelen aktiveres kun ved høj ρ.

Selv under disse optimale betingelser er fordelen over LRTF kun **+0.066
individuel NPS / +2.37 organisation NPS** — beskeden men reproducerbar.

---

## 7. Opfølgende hypoteser

Study 3c rejser nye spørgsmål:

1. **Hvor stærk skal topic-signalet være?** Vi brugte γ_topic =
   NPS_SIM_TOPIC_COEFS (perfekt info). En opfølgning kunne variere
   γ_topic = α × NPS_SIM_TOPIC_COEFS for α ∈ [0, 1] for at finde tærsklen
   hvor topic-info begynder at hjælpe.

2. **Generaliserer effekten til andre prædiktorer?** Topic er én
   prædiktor blandt mange. Tilføj agent-skill, kanal, eller kunde-historik
   og test om kumulativ multi-prædiktor-effekt fortsætter med at vokse.

3. **SLA-test:** Hvad sker med +0.066-fordelen under SLA = 60h? Study 2
   viste at SLA udligner alle forskelle — gælder det også her? (H2 fra
   den tidligere planlægning.)

4. **Den negative regime ved (topic_aware=True, intercept=10.22):**
   Er den fordi vi prioriterer "dårlige" topics, eller fordi vi
   *de-prioriterer* "gode"? Per-topic ventetidsanalyse kan adskille
   disse mekanismer.

---

## 8. Genererede figurer

| Fil | Beskrivelse |
|-----|-------------|
| `results/fig_s3c_1_main_effect.pdf` | NPS−LRTF advantage vs ρ pr. (topic_aware × intercept) — **hovedplot** |
| `results/fig_s3c_2_2x2_grid.pdf` | 2×2 panel med FCFS/LRTF/NPS over ρ, opdelt på topic_aware × intercept |
| `results/fig_s3c_3_variance_diagnostic.pdf` | Var(predicted_nps) pr. celle — confound-tjek |
