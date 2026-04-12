# Weibull-fordelingen og aktivitetsvarigheder

Dette kapitel giver en grundig gennemgang af Weibull-fordelingen og dens rolle i Study 3, hvor den bruges til at modellere varigheden af individuelle aktiviteter i en kundeservicesag.

---

## 1. Hvad er en Weibull-fordeling?

Weibull-fordelingen er en fleksibel fordelingsfamilie til **positive værdier** --- typisk varigheder, levetider eller "tid til hændelse". Den er opkaldt efter den svenske ingenioor Waloddi Weibull og bruges bredt i pålideligheds-analyse, overlevelsesanalyse og køteori.

### Tæthedsfunktion (PDF)

$$f(x; \text{shape}, \text{scale}) = \frac{\text{shape}}{\text{scale}} \left(\frac{x}{\text{scale}}\right)^{\text{shape}-1} \exp\!\left(-\left(\frac{x}{\text{scale}}\right)^{\text{shape}}\right), \quad x > 0$$

### Fordelingsfunktion (CDF)

$$F(x; \text{shape}, \text{scale}) = 1 - \exp\!\left(-\left(\frac{x}{\text{scale}}\right)^{\text{shape}}\right)$$

### Specialtilfælde

Når $\text{shape} = 1$ reduceres Weibull-fordelingen til **eksponentialfordelingen** med rate $1/\text{scale}$. Eksponentialfordelingen er altså et specialtilfælde af Weibull --- men i praksis er shape sjeldent præcis 1.

### Grafisk intuition

- **shape < 1**: Fordelingen har en tung hængsel mod højre (mange korte varigheder, få meget lange).
- **shape = 1**: Eksponentiel --- "hukommelsesløs" fordeling.
- **shape > 1**: Fordelingen er unimodal med en tydelig top. Jo højere shape, jo mere koncentreret er fordelingen omkring middelværdien.

---

## 2. Hvorfor Weibull til aktivitetsvarigheder?

Weibull-fordelingen er velegnet til modellering af aktivitetsvarigheder fordi den har en **fleksibel hazard rate**.

### Hazard rate

Hazard rate (også kaldet "failure rate") er den ojeblikkelige sandsynlighed for at en aktivitet afsluttes, givet at den stadig er i gang:

$$h(x) = \frac{f(x)}{1 - F(x)} = \frac{\text{shape}}{\text{scale}} \left(\frac{x}{\text{scale}}\right)^{\text{shape}-1}$$

- **shape > 1**: Stigende hazard. Jo længere en aktivitet har varet, desto mere sandsynligt er det at den snart slutter. Dette giver intuitiv mening for kundeserviceaktiviteter: de fleste aktiviteter har en naturlig afslutning, og sandsynligheden for afslutning stiger over tid.
- **shape < 1**: Faldende hazard. En aktivitet der allerede har varet længe, vil sandsynligvis vare endnu længere.
- **shape = 1**: Konstant hazard (eksponentiel). Aktiviteten har ingen "hukommelse".

### I Study 3

I Study 3 er:

$$\text{shape} = \frac{1}{\theta} = \frac{1}{0.3908} \approx 2.56$$

Da shape > 1 har vi **stigende hazard** --- hvilket passer godt med kundeserviceaktiviteter. En email der allerede er blevet skrevet på i 30 minutter, er mere sandsynlig at blive afsluttet inden for de næste 5 minutter end en email der lige er påbegendt.

---

## 3. AFT-parameterisering (Accelerated Failure Time)

I Study 3 bruges Weibull-fordelingen ikke med faste shape/scale-parametre. I stedet bruger modellen en **AFT-parameterisering** (Accelerated Failure Time), hvor covariater multiplicerer tidsskalaen.

### Lineær prædiktor

Scale-parameteren beregnes som:

$$\text{scale} = \exp\!\left(\alpha + \sum_i X_i \beta_i\right)$$

hvor:

- $\alpha = 1.6645$ er intercept.
- $X_i$ er covariater (case topic, activity type, activity number, resource effect).
- $\beta_i$ er de tilhørende koefficienter.

### Fortolkning

AFT-parameteriseringen betyder at covariater **multiplicerer** tidsskalaen frem for at forskyde den. Konkret:

- Hvis en covariatkoefficient $\beta_i > 0$, så **forlænger** covariaten varigheden (scale bliver større).
- Hvis $\beta_i < 0$, så **forkorter** den varigheden.

Fordi vi arbejder på log-skala, svarer en koefficient $\beta_i$ til en multiplikativ faktor $\exp(\beta_i)$ på medianen (og alle andre percentiler).

**Eksempel**: Activity type "Interaction" har koefficient $\beta = 0.1057$. Det betyder at interaktioner i gennemsnit tager $\exp(0.1057) \approx 1.11$ gange så lang tid som referencetypen (Email).

### Covariater i Study 3

Den fulde lineære prædiktor i `simulation.py` er:

$$\text{linear\_pred} = \alpha + \beta_{\text{topic}} + \beta_{\text{activity\_type}} + \beta_{\text{activity\_number}} \cdot n + \beta_{\text{resource}} \cdot r + \beta_Z \cdot Z_{\text{actual}}$$

hvor det sidste led ($\beta_Z \cdot Z_{\text{actual}}$) kun er aktivt i "soft" sampling mode (se kapitel 3 om den latente variabel-model).

---

## 4. Inverse CDF-sampling

Dette er **det centrale afsnit** for at forstå hvordan Study 3 bruger Weibull-fordelingen. Inverse CDF-sampling (også kaldet "quantile transform") er metoden til at generere tilfældige varigheder fra fordelingen.

### Grundideen

CDF'en $F(x)$ angiver sandsynligheden for at en varighed er højst $x$. Hvis vi sætter $F(x) = u$ og løser for $x$, får vi den inverse CDF --- også kaldet **quantile-funktionen**:

$$F(x) = 1 - \exp\!\left(-\left(\frac{x}{\text{scale}}\right)^{\text{shape}}\right) = u$$

Løs for $x$:

$$\left(\frac{x}{\text{scale}}\right)^{\text{shape}} = -\ln(1 - u)$$

$$\frac{x}{\text{scale}} = \left(-\ln(1 - u)\right)^{1/\text{shape}}$$

$$\boxed{x = \text{scale} \cdot \left(-\ln(1 - u)\right)^{1/\text{shape}}}$$

Da $\theta = 1/\text{shape}$ i Study 3's parameterisering, kan vi skrive:

$$x = \text{scale} \cdot \left(-\ln(1 - u)\right)^{\theta}$$

### Metoden

1. **Vælg** en værdi $u \in (0, 1)$.
2. **Beregn** $x = \text{scale} \cdot (-\ln(1 - u))^{\theta}$.
3. Resultatet $x$ er en Weibull-fordelt varighed.

Spoergsmålet er: *hvor kommer $u$ fra?*

### Normal random sampling (standard)

I almindelig Monte Carlo-simulation trækker man $u \sim \text{Uniform}(0, 1)$ --- et tilfældigt tal mellem 0 og 1. Hvert kald giver en ny, uafhængig Weibull-variate. Dette svarer til `rng.weibull(shape)` i NumPy (som internt bruger netop denne metode, multipliceret med scale bagefter).

### Hard Z mode: deterministisk fra $Z_{\text{actual}}$

I Study 3's "hard Z" mode bruges en **fast percentil** i stedet for en tilfældig:

$$u = \Phi(Z_{\text{actual}})$$

hvor $\Phi$ er standard normalfordelingens CDF. Da $Z_{\text{actual}} \sim N(0,1)$, er $u = \Phi(Z_{\text{actual}}) \sim \text{Uniform}(0,1)$ (probability integral transform). Så den marginale fordeling er stadig Weibull.

Men der er en afgørenede forskel: i hard Z mode bruger **alle aktiviteter i samme sag den samme $u$**. Det betyder at:

- En sag med høj $Z_{\text{actual}}$ (fx $Z_{\text{actual}} = 1.5$, så $u = \Phi(1.5) \approx 0.93$) får konsistent **lange** varigheder på alle aktiviteter.
- En sag med lav $Z_{\text{actual}}$ (fx $Z_{\text{actual}} = -1.0$, så $u = \Phi(-1.0) \approx 0.16$) får konsistent **korte** varigheder.

Dette skaber en meningsfuld **latent sagskompleksitet**: $Z_{\text{actual}}$ bliver en "master-variabel" der styrer hele sagens karakter.

### Soft Z mode: tilfældig sampling med covariatjustering

I "soft Z" mode bruges tilfældig sampling ($u \sim \text{Uniform}(0,1)$), men $Z_{\text{actual}}$ tilføjes som covaritat i den lineære prædiktor (via koefficienten $\beta_Z$). Det giver en mere moderat sammenhæng --- varigheden påvirkes af $Z_{\text{actual}}$, men der er stadig tilfældig variation mellem aktiviteter i samme sag.

### Sammenligning

| Aspekt | Normal sampling | Hard Z mode | Soft Z mode |
|--------|----------------|-------------|-------------|
| $u$-kilde | $\text{Uniform}(0,1)$ | $\Phi(Z_{\text{actual}})$, fast | $\text{Uniform}(0,1)$ |
| Marginal fordeling | Weibull | Weibull | Weibull (modificeret scale) |
| Korrelation inden for sag | Ingen | Perfekt (alle aktiviteter får samme $u$) | Moderat (via covariat) |
| Effekt af $Z_{\text{actual}}$ | Ingen | Deterministisk: høj $Z$ $\to$ lang varighed | Stokastisk: høj $Z$ $\to$ længere i gennemsnit |

### Nøgleindsigt

**Uanset om $u$ trækkes tilfældigt eller er fast, er den marginale fordeling den samme** (Weibull med givne parametre). Forskellen ligger i den *betingede* struktur:

- I hard Z mode er aktivitetsvarigheder **perfekt korrelerede** inden for en sag.
- I normal sampling er de **uafhængige**.
- Soft Z mode ligger midt imellem.

Denne distinktion er vigtig fordi den afgorer om throughput-tid (summen af alle aktivitetsvarigheder) er prædikterbar fra $Z_{\text{actual}}$, og dermed om $Z_{\text{pred}}$ (som er korreleret med $Z_{\text{actual}}$ via $\rho$) kan bruges til kø-prioritering.

---

## 5. Parametre fra Study 3

### Hovedparametre

| Parameter | Værdi | Beskrivelse |
|-----------|--------|-------------|
| `DURATION_INTERCEPT` ($\alpha$) | 1.6645 | Intercept i lineær prædiktor (log-scale) |
| `DURATION_THETA` ($\theta$) | 0.3908 | Weibull form-parameter ($= 1/\text{shape}$) |
| `RESOURCE_EFFECT_MEAN` | 0.2171 | Middelværdi for agent-effekt |
| `RESOURCE_EFFECT_STD` | 0.52 | Standardafvigelse for agent-effekt |
| `DURATION_ACTIVITY_NUMBER_COEF` | 0.0420 | Koefficient for aktivitetsnummer |

### Topic-koefficienter

| Case topic | Koefficient ($\beta_{\text{topic}}$) |
|------------|--------------------------------------|
| `d_2-z_4` | 0.0200 |
| `g_1-z_4` | -0.0538 |
| `j_1-z_4` | -0.0557 |
| `q_3-z_4` | 0.1712 |
| `r_2-z_4` | 0.0836 |
| `w_1-z_4` | -0.0609 |
| `w_2-z_4` | 0.0119 |
| `z_2-z_4` | -0.0420 |
| `z_3-z_4` | 0.1637 |
| `z_4` (reference) | 0.0 |

### Activity type-koefficienter

| Activity type | Koefficient ($\beta_{\text{type}}$) |
|---------------|-------------------------------------|
| Task-Reminder | 0.0180 |
| Interaction | 0.1057 |
| Email (reference) | 0.0 |

---

## 6. Beregningseksempel

Lad os beregne varigheden af en konkret aktivitet:

**Givet**:
- Case topic: `q_3-z_4` ($\beta_{\text{topic}} = 0.1712$)
- Activity type: Interaction ($\beta_{\text{type}} = 0.1057$)
- Activity number: $n = 3$ ($\beta_n = 0.0420$)
- Resource effect: $r = 0.15$
- Hard Z mode med $Z_{\text{actual}} = 0.8$

**Trin 1: Lineær prædiktor**

$$\text{linear\_pred} = 1.6645 + 0.1712 + 0.1057 + 0.0420 \cdot 3 + 0.15 = 2.2174$$

**Trin 2: Scale**

$$\text{scale} = \exp(2.2174) \approx 9.18 \text{ timer}$$

**Trin 3: Percentil fra $Z_{\text{actual}}$**

$$u = \Phi(0.8) \approx 0.7881$$

**Trin 4: Varighed via inverse CDF**

$$\text{duration} = 9.18 \cdot (-\ln(1 - 0.7881))^{0.3908}$$

$$= 9.18 \cdot (-\ln(0.2119))^{0.3908}$$

$$= 9.18 \cdot (1.5515)^{0.3908}$$

$$= 9.18 \cdot 1.1879$$

$$\approx 10.9 \text{ timer}$$

Til sammenligning, hvis $Z_{\text{actual}} = -0.8$ (lav kompleksitet):

$$u = \Phi(-0.8) \approx 0.2119$$

$$\text{duration} = 9.18 \cdot (-\ln(1 - 0.2119))^{0.3908} = 9.18 \cdot (0.2380)^{0.3908} \approx 9.18 \cdot 0.5343 \approx 4.9 \text{ timer}$$

Samme aktivitet, men med lav kompleksitet ($Z = -0.8$) tager den knap halvdelen af tiden sammenlignet med høj kompleksitet ($Z = 0.8$). Det er denne mekanisme der gør throughput-tid prædikterbar fra $Z$.

---

## Opsummering

- Weibull-fordelingen modellerer aktivitetsvarigheder med **stigende hazard rate** (shape $\approx 2.56$).
- **AFT-parameterisering** lader covariater (topic, activity type, osv.) multiplicere tidsskalaen.
- **Inverse CDF-sampling** er nøglen til Study 3: ved at erstatte tilfældige $u$-værdier med $u = \Phi(Z_{\text{actual}})$ skabes en latent sagskompleksitet der gør throughput-tider prædikterbare.
- Jo højere $Z_{\text{actual}}$, desto længere varigheder --- konsistent på tværs af alle aktiviteter i sagen.

**Næste kapitel**: [03-latent-variabel-model.md](03-latent-variabel-model.md) --- Hvordan styrer $Z_{\text{actual}}$ og $Z_{\text{pred}}$ forholdet mellem prædiktion og virkelighed?
