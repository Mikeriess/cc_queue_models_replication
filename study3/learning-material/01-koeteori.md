# Køteori og prioriteringsstrategier

Dette kapitel introducerer de køteoretiske begreber der ligger til grund for Study 3's simulation. Vi ser på hvordan sager ankommer, venter, og bliver behandlet --- og især på hvordan *rækkefølgen* af behandling påvirker det samlede resultat.

---

## 1. Hvad er en kø?

En kø opstår når efterspørgslen efter en ressource overstiger kapaciteten. Det er et hverdagsfænomen:

- **Hospital akutmodtagelse**: Patienter ankommer med varierende hastesgrad. En triagesygeplejerske vurderer hvem der skal behandles først --- ikke nødvendigvis den der ankom først, men den der har størst behov.
- **Lufthavns-checkin**: Passagerer stiller sig i kø. Business-class får en separat (hurtigere) kø. Her prioriteres efter billettype snarere end ankomsttidspunkt.
- **Kundeservicecenter** (Study 3's domæne): Sager ankommer løbende via email, telefon eller chat. De skal behandles af et begrænset antal agenter. Noeglespørgsmålet er: *i hvilken rækkefølge skal sagerne behandles?*

I alle tilfælde har vi de samme grundelementer:

1. **Ankomstproces**: Sager ankommer over tid (i Study 3 via en Poisson-lignende model, se `simulation.py`).
2. **Servicetid**: Hver sag tager en vis tid at behandle (modelleret med en Weibull-fordeling, se kapitel 2).
3. **Antal servere** (agenter): Begrænset kapacitet --- i Study 3 testes med 5, 6 eller 7 agenter.
4. **Kødisciplin**: Reglen der bestemmer rækkefølgen. Det er dette vi eksperimenterer med.

---

## 2. FCFS --- First Come First Served

Den simpleste og mest intuitive kødisciplin: **først til mølle**.

### Princip

Sager behandles i den rækkefølge de ankommer. Ingen sag "springer over" andre.

### Matematisk

Sorteer køen efter `arrival_time` i stigende rækkefølge:

$$\text{prioritet}(c) = t_{\text{arrival}}(c)$$

Den sag med lavest $t_{\text{arrival}}$ får højest prioritet.

### Fordele og ulemper

| Fordele | Ulemper |
|---------|---------|
| Simpelt og "fair" | Ignorerer forskelle i sagers kompleksitet |
| Ingen information krævet | Lange sager kan blokere systemet |
| Deterministisk rækkefølge | Ingen mulighed for at optimere kundetilfredshed |

FCFS fungerer som **baseline** i Study 3 --- det er den strategi der ikke bruger nogen prædiktiv information overhovedet.

---

## 3. LRTF --- Longest Remaining Time First

En heuristisk strategi der prioriterer de sager som forventes at tage længst tid.

### Princip

Ved at tage de lange sager først reduceres risikoen for at de hober sig op og blokerer systemet. Intuitivt: hvis en lang sag venter, vokser dens bidrag til køens samlede ventetid for hvert tidsstep den forbliver i køen.

### Matematisk

Sorteer køen efter `predicted_throughput` i faldende rækkefølge:

$$\text{prioritet}(c) = -\hat{T}_{\text{throughput}}(c)$$

Den sag med højest forudsagt throughput-tid får højest prioritet (lavest prioritetsscore).

### Krav til information

LRTF kræver et estimat af den forventede behandlingstid. I Study 3 beregnes dette fra den latente variabel $Z_{\text{pred}}$ via Weibull inverse CDF (se kapitel 2). Det vigtige er at LRTF kun bruger throughput-estimatet --- den bruger *ikke* NPS-modellen.

### Hvorfor er LRTF interessant?

LRTF er en simpel heuristik der udnytter prædiktiv information, men uden den ekstra kompleksitet af en NPS-model. Study 3's kernehypotese er at NPS-baseret prioritering bør klare sig *bedre* end LRTF når prædiktionsnøjagtigheden ($\rho$) stiger. Hvis NPS-prioritering ikke slår LRTF, er NPS-modellens ekstra kompleksitet ikke retfærdiggjort.

---

## 4. NPS-baseret prioritering

Den mest sofistikerede strategi i Study 3: prioriter sager der er tættest på "tipping point" for kundetilfredshed.

### Princip

NPS (Net Promoter Score) klassificerer kunder i tre grupper:

| Kategori | NPS-score | Fortolkning |
|----------|-----------|-------------|
| Promoter | 9--10 | Loyal, anbefaler virksomheden |
| Passive | 7--8 | Tilfreds men ikke entusiastisk |
| Detractor | 0--6 | Utilfreds, risiko for negativ omtale |

Ideen bag NPS-prioritering er at fokusere på de sager der befinder sig tæt på grænsen mellem Detractor og Passive/Promoter. En sag med $\hat{\text{NPS}} \approx 7.5$ er en sag der kan "tippes" --- enten til en tilfreds kunde (med hurtig service) eller til en utilfreds kunde (med langsom service).

### Matematisk

Prioritetsscoren beregnes som afstanden til midtpunktet:

$$\text{prioritetsscore}(c) = |\hat{\text{NPS}}(c) - 7.5|$$

Køen sorteres i **stigende** rækkefølge: den sag med *lavest* score (tættest på 7.5) får højest prioritet.

I kode (fra `queue_management()` i `simulation.py`):

```python
ordered = sorted(visible,
                 key=lambda c: abs(c.predicted_nps - NPS_MIDPOINT))
```

### Krav til information

NPS-prioritering kræver:

1. Et estimat af throughput-tid (som LRTF).
2. En NPS-prædiktionsmodel der oversætter throughput til forventet NPS.

Så NPS-strategien bygger *ovenpå* den information LRTF bruger, med et ekstra modellag.

### Hvornår virker det?

NPS-prioritering bør være mest effektiv når:

- Prædiktionen er præcis nok ($\rho$ høj) til at identificere de "rigtige" tipping-point-sager.
- Systemet er tilstrækkeligt belastet til at prioriteringsvalg gør en forskel.

Study 3 tester netop dette ved at variere $\rho$ systematisk.

---

## 5. SLA-override

I praksis har kundeservicecentre ofte en **Service Level Agreement** (SLA): en garanti for at sager behandles inden for en vis tidsramme (fx 24 timer).

### Mekanisme

SLA-override er en sikkerhedsmekanisme der "bumper" sager til fronten af køen når de nærmer sig SLA-brud --- uanset hvilken kødisciplin der ellers er valgt. I `simulation.py` implementeres det ved at:

1. Beregne ventetiden for hver sag: $w(c) = t_{\text{nu}} - t_{\text{arrival}}(c)$.
2. Identificere sager hvor $w(c) \geq \text{SLA}_{\text{threshold}} - 1$ dag.
3. Flytte disse sager til fronten af køen, sorteret efter ankomsttid (ældste først).

### I Study 3: SLA deaktiveret

I Study 3 sættes `SLA = None` (deaktiveret). Grunden er at Study 2 viste at SLA-override udligner forskellene mellem kødiscipliner: når alle sager alligevel tvinges igennem inden tidsfristen, bliver det mindre vigtigt hvilken rækkefølge de behandles i. For at isolere effekten af kødisciplin og prædiktionsnøjagtighed slås SLA derfor fra.

---

## 6. Kapacitet og belastning

Antallet af agenter bestemmer systemets **belastningsgrad** ($\rho_{\text{system}}$, ikke at forveksle med korrelationsparameteren $\rho$). Belastningsgraden er forholdet mellem ankomstrate og servicekapacitet.

Study 3 tester tre niveauer:

| Agenter | Belastning | Effekt |
|---------|-----------|--------|
| 5 | Høj (overbelastet) | Køen vokser; disciplinen gør stor forskel |
| 6 | Moderat ("sweet spot") | Køen er stabil; forskelle mellem discipliner er tydelige |
| 7 | Lav (underbelastet) | Køen er næsten altid tom; disciplinen har minimal effekt |

**Agent count = 6** bruges som primært analyseniveau fordi det giver tilstrækkelig belastning til at kødisciplinen har effekt, uden at systemet bryder sammen.

### Intuition

Tænk på et supermarked:

- **5 kasser åbne** (overbelastet): Køen vokser hele tiden. Det er *meget* vigtigt hvem der får lov til at gå til kassen først.
- **6 kasser åbne** (balanceret): Køen svinger, men stabiliserer sig. Prioriteringsstrategien har en mærkbar effekt.
- **7 kasser åbne** (underbelastet): Der er næsten aldrig kø. Det er ligegyldigt hvem der går først --- alle bliver betjent hurtigt.

---

## 7. Implementation i simulation.py

Kødisciplinerne er implementeret i funktionen `queue_management()` i `simulation.py`. Funktionen:

1. Filtrerer køen til kun at inkludere **synlige** sager (ankommet og med status `"waiting"`).
2. Sorterer de synlige sager baseret på den valgte disciplin:
   - `"FCFS"`: sorteer efter `arrival_time` (stigende).
   - `"LRTF"`: sorteer efter `predicted_throughput` (faldende).
   - `"NPS"`: sorteer efter $|\hat{\text{NPS}} - 7.5|$ (stigende).
3. Anvender SLA-override hvis aktiveret (deaktiveret i Study 3).

Derefter tildeler `case_assignment()` de højest-prioriterede sager til ledige agenter.

```python
# Forenklet oversigt over flow i hvert tidsstep:
ordered_queue = queue_management(queue, discipline, current_time, sla_hours)
case_assignment(ordered_queue, agents, case_lookup)
```

### Tidsstep

Simulationen kører i diskrete tidsstep på 15 minutter (`TIMESTEP_DAYS = 15 / (24 * 60)`). I hvert tidsstep:

1. Tjek om aktive sager er færdige.
2. Sorteer køen (kødisciplin).
3. Tildel ledige agenter til ventende sager.
4. Simuleer næste aktivitet for aktive sager.

---

## Opsummering

| Disciplin | Sorteringsnøgle | Retning | Information krævet |
|-----------|-----------------|---------|-------------------|
| FCFS | `arrival_time` | Stigende | Ingen |
| LRTF | `predicted_throughput` | Faldende | Throughput-estimat |
| NPS | $\lvert\hat{\text{NPS}} - 7.5\rvert$ | Stigende | Throughput-estimat + NPS-model |

Study 3's kernespørgsmål: betaler den ekstra modelkompleksitet i NPS-prioritering sig, når prædiktionerne bliver bedre ($\rho \uparrow$)?

**Næste kapitel**: [04-markov-kæde.md](04-markov-kæde.md) --- Hvordan genereres aktivitetssekvenser for en sag?
