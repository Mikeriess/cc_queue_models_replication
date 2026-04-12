# NPS-modellen --- simulation, prædiktion og monotonicitet

## Hvad er Net Promoter Score?

**Net Promoter Score (NPS)** er en udbredt kundetilfredshedsskala. Kunder svarer på spørgsmålet *"Hvor sandsynligt er det at du vil anbefale os?"* på en skala fra 0 til 10.

Svarene klassificeres i tre grupper:

| Gruppe | Score | Betydning |
|--------|-------|-----------|
| **Promoters** | 9--10 | Loyale, entusiastiske kunder |
| **Passives** | 7--8 | Tilfredse men ikke loyale |
| **Detractors** | 0--6 | Utilfredse kunder |

Organisationens samlede NPS beregnes som:

$$\text{NPS}_{\text{org}} = (\%\text{Promoters} - \%\text{Detractors}) \times 100$$

NPS spænder fra $-100$ (alle er Detractors) til $+100$ (alle er Promoters). En NPS på fx $+20$ betyder at der er 20 procentpoint flere Promoters end Detractors.

---

## NPS simulationsmodel (Eq. 8)

Den "sande" NPS-respons genereres *efter* en sag er lukket. Modellen er estimeret på rigtige kundedata og fanger sammenhængen mellem behandlingstid og tilfredshed.

### Lineær prædiktor

$$\text{linear\_pred} = 2.3006 - 0.0098 \times \log(\text{actual\_throughput} + 1) + \text{topic\_effects}$$

hvor `actual_throughput` er den faktiske throughput-tid i minutter, og `topic_effects` er sags-specifikke koefficienter.

### Gamma-sampling

NPS samples fra en **Gamma-fordeling**:

$$\text{shape} = \frac{\exp(\text{linear\_pred})}{\rho_{\text{sim}}}, \quad \text{scale} = \rho_{\text{sim}}$$

$$\text{NPS}_{\text{raw}} = \text{Gamma}(\text{shape}, \text{scale}) - 1$$

$$\text{NPS} = \text{clip}(\lceil \text{NPS}_{\text{raw}} \rceil, \; 0, \; 10)$$

Her er $\rho_{\text{sim}} = 1.3005$ en **dispersion parameter** --- *ikke* at forveksle med $\rho$ (korrelationen mellem prædikteret og faktisk kompleksitet). Dispersionen styrer spredningen i NPS-svarene.

### Nogleindsingt

Koefficienten $-0.0098$ er negativ: hurtigere behandling ($\downarrow$ throughput) $\to$ højere forventet NPS ($\uparrow$). Det afspejler den intuitive sammenhæng at kunder er mere tilfredse når deres sag behandles hurtigt.

---

## NPS prædiktionsmodel (Eq. 9)

Den *forudsagte* NPS beregnes ved sagsstarten --- før sagen er behandlet --- og bruges til at prioritere køen.

$$\text{NPS}_{\text{hat}} = 10.2211 - 0.0949 \times \log(\text{predicted\_throughput} + 1) - 1$$

Forenklet:

$$\text{NPS}_{\text{hat}} \approx 9.2211 - 0.0949 \times \log(\text{predicted\_throughput} + 1)$$

Bemærk: dette er en **simpel lineær funktion** af $\log(\text{predicted\_throughput})$. Den er **monotont aftagende** i predicted\_throughput --- højere forventet behandlingstid giver lavere forudsagt NPS.

---

## Prioritetsscoren: $|\text{NPS}_{\text{hat}} - 7.5|$

Ideen bag NPS-baseret prioritering er at identificere sager der kan "tippes" af god eller dårlig service.

Sager med $\text{NPS}_{\text{hat}}$ tæt på $7.5$ --- midtpunktet mellem Detractor (score $\leq 6$) og Promoter (score $\geq 9$) --- er dem hvor sagsbehandlingens kvalitet kan gøre forskellen mellem en utilfreds og en tilfreds kunde.

**Prioritetsscore:**

$$\text{priority} = |\text{NPS}_{\text{hat}} - 7.5|$$

**Lavest score** $\to$ **højest prioritet** (serveres først). En sag med $\text{NPS}_{\text{hat}} = 7.6$ får priority $= 0.1$ og serveres før en sag med $\text{NPS}_{\text{hat}} = 9.0$ (priority $= 1.5$).

---

## MONOTONITETS-ARGUMENTET --- det centrale resultat

Denne sektion forklarer Study 3's vigtigste fund: at NPS-prioritering producerer **identisk rangorden** som LRTF, uanset prædiktionsnøjagtigheden $\rho$.

### Trin 1: NPS_hat's værdiområde

Vi starter med den forenklede formel:

$$\text{NPS}_{\text{hat}} \approx 9.22 - 0.0949 \times \log(\text{pt} + 1)$$

hvor $\text{pt}$ er predicted throughput i minutter. For typiske throughput-tider:

| predicted throughput (min) | $\log(\text{pt} + 1)$ | $\text{NPS}_{\text{hat}}$ |
|----------------------------|-----------------------|---------------------------|
| 100 | 4.62 | 8.78 |
| 500 | 6.22 | 8.63 |
| 1000 | 6.91 | 8.56 |
| 2000 | 7.60 | 8.50 |

**Observation: $\text{NPS}_{\text{hat}}$ ligger ALTID over 7.5** for realistiske throughput-tider. Koefficienten $-0.0949$ er så lille at selv meget lange sager ikke trykker NPS\_hat under 7.5.

### Trin 2: Absolutværdien forsvinder

Når $\text{NPS}_{\text{hat}} > 7.5$ for *alle* sager, kan vi forenkle prioritetsscoren:

$$|\text{NPS}_{\text{hat}} - 7.5| = \text{NPS}_{\text{hat}} - 7.5$$

(Absolutværditegnet er redundant når alle værdier er på samme side af 7.5.)

### Trin 3: Prioritetsscore som funktion af throughput

$$|\text{NPS}_{\text{hat}} - 7.5| = (9.22 - 0.0949 \times \log(\text{pt} + 1)) - 7.5$$

$$= 1.72 - 0.0949 \times \log(\text{pt} + 1)$$

Dette er en **konstant minus en monotont stigende funktion** af $\text{pt}$.

### Trin 4: Sortering afslører ækvivalensen

- **Sortering efter $|\text{NPS}_{\text{hat}} - 7.5|$ ascending** (lavest prioritetsscore først)
- $= $ sortering efter $1.72 - 0.0949 \times \log(\text{pt} + 1)$ ascending
- $= $ sortering efter $\log(\text{pt} + 1)$ **descending** (størst først)
- $= $ sortering efter $\text{pt}$ **descending** (størst først)
- $= $ **LRTF!** (Longest Remaining Time First)

### Trin 5: Hvorfor $\rho$ er irrelevant

Bedre prædiktioner (højere $\rho$) giver mere præcise værdier af predicted throughput og dermed mere præcise $\text{NPS}_{\text{hat}}$-værdier. Men fordi den monotone transformation $\text{pt} \to |\text{NPS}_{\text{hat}} - 7.5|$ *bevarer rangordenen*, producerer de mere præcise værdier den **samme sortering**.

- Ved $\rho = 0$: prædiktionerne er tilfældige $\to$ NPS sorterer tilfældigt $\to$ LRTF sorterer også tilfældigt (samme tilfældige rangorden)
- Ved $\rho = 1$: prædiktionerne er perfekte $\to$ NPS sorterer korrekt efter kompleksitet $\to$ LRTF sorterer også korrekt efter kompleksitet (samme perfekte rangorden)
- For alle $\rho$ derimellem: **identisk rangorden**

### Konklusion

NPS-prioritering er **strukturelt ækvivalent** med LRTF. Forskellen $\text{NPS} - \text{LRTF} = 0.0000$ over alle 9.000 simulationskørsler.

### Hvad skal der til for at NPS $\neq$ LRTF?

For at NPS-prioritering skal give en *anderledes* rangorden end LRTF kræves mindst et af følgende:

**(a) En ikke-monoton NPS-model:** Hvis $\text{NPS}_{\text{hat}}$ afhænger af multiple prædiktorer (fx topic, agenthistorik, sagstype) på en måde der bryder den monotone sammenhæng med throughput.

**(b) At $\text{NPS}_{\text{hat}}$ krydser 7.5:** Hvis en betydelig andel sager har $\text{NPS}_{\text{hat}} < 7.5$ mens andre har $\text{NPS}_{\text{hat}} > 7.5$, så virker absolutværdien som en "fold" der skaber en ikke-monoton rangorden.

---

## Varianskontrol --- skaleringskoefficienten

### Problemet

Study 3 bruger en ny Weibull-baseret throughput-prædiktion (fra $Z_{\text{pred}}$) i stedet for Study 2's sæsonbaserede model. Fordi den nye prædiktionsmetode har en anden varians i predicted\_throughput, ændres variansen i $\text{NPS}_{\text{hat}}$ --- og det kan give en confounding effekt.

### Løsningen

Vi rescaler Eq. 9's koefficient så variansen i predicted\_nps matcher Study 2's baseline:

$$\text{NPS\_PRED\_COEF\_STUDY3} = -0.0949 \times \text{scaling\_factor}$$

hvor:

$$\text{scaling\_factor} = \sqrt{\frac{\text{baseline\_var}}{\text{new\_var}}}$$

Her er `baseline_var` variansen i $\log(\text{predicted\_throughput} + 1)$ fra Study 2's sæsonmodel, og `new_var` er variansen fra Study 3's Weibull-baserede prædiktioner.

Effekten er at spredningen i $\text{NPS}_{\text{hat}}$ forbliver den samme som i Study 2, så eventuelle forskelle alene skyldes prædiktionsnøjagtigheden $\rho$ --- ikke en artefakt af ændret varians.

---

## Inter-arrival processen (Eq. 6)

Sagerne ankommer til simulationen ifølge en **inhomogen Poisson-proces**. "Inhomogen" betyder at intensiteten varierer over tid --- der ankommer fx flere sager på hverdage end i weekenden.

### Model

Inter-arrival tiden (tid mellem to på hinanden følgende sager) er:

$$\text{inter\_arrival} = -\log(1 - U) \times \exp(\text{linear\_pred})$$

hvor $U \sim \text{Uniform}(0, 1)$ og:

$$\text{linear\_pred} = 726.2 + (-0.3589) \times \text{year} + (-0.0881) \times \text{month} + 0.0078 \times \text{day} + 0.2616 \times \text{weekday}$$

### Koefficienter

| Koefficient | Værdi | Fortolkning |
|-------------|--------|-------------|
| Intercept | 726.2 | Kalibreret basisværdi (i log-skala) |
| year | $-0.3589$ | Færre sager over tid (faldende trend år for år) |
| month | $-0.0881$ | Svag sæsoneffekt |
| day | $+0.0078$ | Minimal effekt af dag i måneden |
| weekday | $+0.2616$ | Flere sager på hverdage end i weekender |

Nøgleobservation: $-\log(1 - U)$ er en eksponentialfordelt variabel (inverse CDF-metoden), så inter-arrival tiderne er eksponentialfordelte med en tidsafhængig rate --- præcis definitionen på en inhomogen Poisson-proces.
