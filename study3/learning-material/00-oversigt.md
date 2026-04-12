# Study 3 --- Læringsmaterialer

## Introduktion

Study 3 undersøger om NPS-baseret kø-prioritering klarer sig bedre end simple heuristikker (LRTF) når prædiktionsnøjagtigheden forbedres. Vi simulerer "the value of information" ved at manipulere korrelationen ($\rho$) mellem prædikteret og faktisk throughput-tid. Hvis NPS-modellen er værdifuld, bør dens fordel vokse i takt med at prædiktionerne bliver mere præcise --- dvs. når $\rho \to 1$.

Studiet bygger på en detaljeret kø-simulation af et kundeservicecenter, hvor sager ankommer løbende, behandles af et begrænset antal agenter, og efterfølgende modtager en NPS-score. Ved at variere $\rho$ fra 0 (ingen information) til 1 (perfekt information) kan vi isolere værdien af prædiktiv information.

---

## Forudsætninger

For at få fuldt udbytte af materialerne bør du være fortrolig med:

- **Basal sandsynlighedsregning**: normalfordeling, betinget sandsynlighed, CDF og inverse CDF.
- **Grundlæggende statistik**: middelværdi, varians, konfidensintervaller, Monte Carlo-simulation.
- **Grundlæggende lineær regression**: lineær prædiktor, koefficienter, fortolkning af $\exp(\cdot)$ i log-lineære modeller.

---

## Anbefalet læserækkefølge

| # | Dokument | Interaktivt supplement |
|---|----------|----------------------|
| 1 | `00-oversigt.md` (denne fil) | --- |
| 2 | `01-køteori.md` | `interactive-01-kø-simulator.html` |
| 3 | `04-markov-kæde.md` | `interactive-04-markov-kæde.html` |
| 4 | `02-weibull-fordeling.md` | `interactive-02-weibull.html` |
| 5 | `03-latent-variabel-model.md` | `interactive-03-latent-z.html` |
| 6 | `05-nps-model.md` | `interactive-05-monotoni-bevis.html` |
| 7 | `06-eksperimentelt-design.md` | `interactive-06-eksperiment.html` |

Start med køteori (kapitel 1), som giver den overordnede ramme for simulationen. Markov-kæden (kapitel 4 i rækkefølgen) forklarer hvordan aktivitetssekvenser genereres. Weibull-fordelingen (kapitel 2) beskriver hvordan enkelte aktiviteters varighed samples. Den latente variabel-model (kapitel 3) er Study 3's kerneudvidelse. NPS-modellen (kapitel 5) forbinder throughput til kundetilfredshed. Til sidst samler det eksperimentelle design (kapitel 6) alle elementer.

---

## Symbolordbog / Notation

| Symbol | Navn | Betydning |
|--------|------|-----------|
| $\rho$ (rho) | Korrelation | Korrelation mellem prædikteret og faktisk kompleksitet. $\rho = 0$: ingen prædiktiv information; $\rho = 1$: perfekt prædiktion. |
| $Z_{\text{actual}} \sim N(0,1)$ | Latent sags-kompleksitet | En standard normalfordelt variabel der styrer hvor "kompleks" en sag er. Høj $Z_{\text{actual}}$ betyder længere aktivitetsvarigheder. |
| $Z_{\text{pred}}$ | Prædikteret kompleksitet | Korreleret med $Z_{\text{actual}}$ via $\rho$: $Z_{\text{pred}} = \rho \cdot Z_{\text{actual}} + \sqrt{1 - \rho^2} \cdot \varepsilon$, hvor $\varepsilon \sim N(0,1)$. |
| $\Phi(\cdot)$ | Standard normalfordelingens CDF | Transformerer $Z$-værdier til percentiler $u \in (0,1)$: $u = \Phi(Z)$. |
| $u_{\text{actual}} = \Phi(Z_{\text{actual}})$ | Faktisk percentil | Bruges til inverse CDF-sampling af aktivitetsvarigheder. |
| $\theta$ (theta) = 0.3908 | Weibull form-parameter | Svarer til $1/\text{shape}$, så shape $\approx 2.56$. Styrer hazard rate. |
| $\alpha$ (alpha) = 1.6645 | Weibull intercept | Intercept i den lineære prædiktor (log-scale). $\text{scale} = \exp(\alpha + \ldots)$. |
| NPS | Net Promoter Score | Kundetilfredshedsscore på 0--10 skalaen. Klassificeres som Detractor (0--6), Passive (7--8) eller Promoter (9--10). |
| FCFS | First Come First Served | Kødisciplin: først til mølle. |
| LRTF | Longest Remaining Time First | Kødisciplin: prioriter sager med længst forventet behandlingstid. |
| SLA | Service Level Agreement | Tidsgrænse for sagsbehandling (deaktiveret i Study 3: SLA = None). |
