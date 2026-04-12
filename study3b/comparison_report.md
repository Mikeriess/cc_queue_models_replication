# Study 3b — Resultater: Counterfactual Probe

**Data:** 6.000 simulationskørsler (4 intercept × 5 ρ × 3 discipliner × 1 agent-niveau × 100 reps).

---

## Hovedfund

### 1. Interceptet bryder NPS ≡ LRTF — men effekten er beskeden

Ved intercept = 10.22 (original) er NPS ≡ LRTF (forskel = 0.0000) — replikerer Study 3.

Ved lavere intercepts divergerer NPS fra LRTF, og effekten er størst ved **ρ = 0.85**:

| Intercept | NPS − LRTF (ρ=0.85, indiv. NPS) | NPS − LRTF (ρ=0.85, org. NPS) |
|-----------|--------------------------------|-------------------------------|
| 10.22 | 0.0000 | 0.00 |
| 9.00 | +0.0028 | +0.19 |
| 8.00 | **+0.0303** | **+0.97** |
| 7.50 | **+0.0303** | **+0.97** |

### 2. Intercept 7.5 og 8.0 er identiske

Overraskende: intercept = 7.5 og 8.0 producerer **præcis de samme resultater**
over alle ρ-niveauer. Det skyldes at begge intercepts er lave nok til at
NPS_hat-fordelingen krydser 7.5 for en tilstrækkelig andel af sagerne — den
V-formede priority-funktion er "fuldt aktiveret" ved begge.

### 3. Effekten kræver BÅDE lavt intercept OG høj ρ

NPS − LRTF advantage som funktion af intercept × ρ (individual NPS):

| Intercept | ρ=0.00 | ρ=0.22 | ρ=0.50 | ρ=0.85 | ρ=1.00 |
|-----------|--------|--------|--------|--------|--------|
| 7.5/8.0 | −0.009 | +0.011 | +0.009 | **+0.030** | +0.012 |
| 9.0 | −0.009 | +0.005 | +0.001 | +0.003 | +0.006 |
| 10.22 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Nøgleobservation: effekten **peaker ved ρ = 0.85** og falder igen ved ρ = 1.00.
Det tyder på at den V-formede priority-funktion fungerer bedst med god men ikke
perfekt prædiktion. Ved ρ = 1.00 (perfekt information) sorterer LRTF allerede
optimalt — NPS's V-form tilføjer intet ekstra.

### 4. Absolut effektstørrelse er lille

Den maximale NPS-advantage over LRTF er **+0.030 NPS-point** (individual) og
**+0.97 procentpoint** (organisation). Til sammenligning er advantage over FCFS
ca. +0.05 NPS-point (individual) og +2 (organisation).

NPS-prioritering tilbyder altså en **marginal** forbedring over LRTF
(ca. halvdelen af LRTF's fordel over FCFS) — og kun under to betingelser:

1. NPS-modellen producerer prædiktioner der spreder sig over begge sider af 7.5
2. Prædiktionsnøjagtigheden er moderat-til-høj (ρ ≈ 0.85)

### 5. FCFS er perfekt ρ- og intercept-invariant ✅

Range = 0.0000 for FCFS over alle betingelser. Paret seeding virker korrekt.

---

## Konklusion

Study 3b bekræfter at **NPS-prioritering KAN divergere fra LRTF**, men kun
under specifik betingelser:

1. **NPS-fordelingen skal krydse midtpunktet** — dette kræver enten et lavere
   intercept (som her) eller en ikke-monoton NPS-model med topic-effekter
2. **Prædiktionsnøjagtigheden skal være moderat-til-høj** — ρ ≈ 0.85 er sweet spot
3. **Selv under optimale betingelser er effekten beskeden** — +0.03 NPS-point

**Praktisk implikation:** LRTF forbliver det foretrukne alternativ til FCFS.
NPS-prioritering tilbyder kun marginal forbedring under urealistisk gunstige
betingelser (lav-intercept NPS-model + høj prædiktionsnøjagtighed). Artiklens
hovedresultat — at prioritering baseret på predicted throughput time giver
højere kundeloyalitet — er robust, men den specifikke NPS-baserede
prioriteringsformel (Eq. 1) tilbyder ikke unik værdi over LRTF.

---

## Genererede figurer

| Fil | Beskrivelse |
|-----|-------------|
| `results/fig_s3b_1_nps_advantage_vs_intercept.pdf` | Hovedresultat: NPS−LRTF advantage vs intercept × ρ |
| `results/fig_s3b_2_nps_by_intercept.pdf` | Individual NPS pr. disciplin for hvert intercept |
| `results/fig_s3b_3_org_nps_by_intercept.pdf` | Organisation NPS pr. disciplin × intercept |
