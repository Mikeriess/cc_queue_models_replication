# Den latente variabel-model --- at kontrollere prædiktionsnøjagtighed

## Motivation

Study 3 stiller spørgsmålet: *hvad sker der når prædiktioner af throughput-tid bliver bedre?* Kan NPS-baseret køprioritering udnytte bedre information til at overgå simple heuristikker som LRTF?

For at besvare dette har vi brug for en mekanisme der kontrollerer prædiktionsnøjagtigheden --- dvs. korrelationen mellem den prædikterede og den faktiske throughput-tid. Men vi kan ikke bare ændre den underliggende Weibull-fordeling, fordi så ville vi ændre *virkeligheden*, ikke kun *informationen*. Vi skal holde den sande varighed uændret og kun ændre hvor godt vi kan forudsige den.

Løsningen er en **latent variabel $Z$** der styrer Både virkeligheden og prædiktionen, med en kontrollerbar korrelation $\rho$. Når $\rho = 0$ er prædiktionen ren støj; når $\rho = 1$ er prædiktionen perfekt. Alt derimellem giver os et præcist kontrolpunkt.

---

## Bivariat normal-konstruktion

Dette er den matematiske kerne i Study 3. Vi konstruerer to korrelerede standard normalfordelte variable med en *eksakt* kontrollerbar korrelation $\rho$.

### Trin 1: Træk den latente "virkelighed"

$$Z_{\text{actual}} \sim N(0, 1)$$

$Z_{\text{actual}}$ repræsenterer den latente *sagskompleksitet*. En høj værdi betyder en kompleks sag (lang behandlingstid); en lav værdi betyder en simpel sag.

### Trin 2: Træk uafhængig støj

$$\varepsilon \sim N(0, 1), \quad \varepsilon \perp Z_{\text{actual}}$$

$\varepsilon$ er ren støj, fuldstændig uafhængig af $Z_{\text{actual}}$.

### Trin 3: Konstruer prædiktionen

$$Z_{\text{pred}} = \rho \cdot Z_{\text{actual}} + \sqrt{1 - \rho^2} \cdot \varepsilon$$

Denne formel er nøglen. Lad os bevise at den har de ønskede egenskaber.

### Bevis: $Z_{\text{pred}}$ er også $N(0, 1)$

**Forventning:**

$$E[Z_{\text{pred}}] = \rho \cdot E[Z_{\text{actual}}] + \sqrt{1 - \rho^2} \cdot E[\varepsilon] = \rho \cdot 0 + \sqrt{1 - \rho^2} \cdot 0 = 0$$

**Varians:**

$$\text{Var}(Z_{\text{pred}}) = \rho^2 \cdot \text{Var}(Z_{\text{actual}}) + (1 - \rho^2) \cdot \text{Var}(\varepsilon)$$

(Krydsleddet forsvinder fordi $\varepsilon \perp Z_{\text{actual}}$.)

$$= \rho^2 \cdot 1 + (1 - \rho^2) \cdot 1 = \rho^2 + 1 - \rho^2 = 1$$

Da $Z_{\text{pred}}$ er en lineær kombination af to uafhængige normalfordelte variable, er $Z_{\text{pred}}$ selv normalfordelt: $Z_{\text{pred}} \sim N(0, 1)$. $\square$

### Bevis: $\text{Cov}(Z_{\text{actual}}, Z_{\text{pred}}) = \rho$

$$\text{Cov}(Z_{\text{actual}}, Z_{\text{pred}}) = \text{Cov}(Z_{\text{actual}},\; \rho \cdot Z_{\text{actual}} + \sqrt{1 - \rho^2} \cdot \varepsilon)$$

$$= \rho \cdot \text{Cov}(Z_{\text{actual}}, Z_{\text{actual}}) + \sqrt{1 - \rho^2} \cdot \text{Cov}(Z_{\text{actual}}, \varepsilon)$$

$$= \rho \cdot \text{Var}(Z_{\text{actual}}) + \sqrt{1 - \rho^2} \cdot 0 = \rho \cdot 1 = \rho \quad \square$$

### Bevis: $\text{Corr}(Z_{\text{actual}}, Z_{\text{pred}}) = \rho$

$$\text{Corr}(Z_{\text{actual}}, Z_{\text{pred}}) = \frac{\text{Cov}(Z_{\text{actual}}, Z_{\text{pred}})}{\sqrt{\text{Var}(Z_{\text{actual}}) \cdot \text{Var}(Z_{\text{pred}})}} = \frac{\rho}{\sqrt{1 \cdot 1}} = \rho \quad \square$$

### Konklusion

Parameteren $\rho$ kontrollerer *præcis* korrelationen mellem $Z_{\text{actual}}$ og $Z_{\text{pred}}$, mens begge marginalt forbliver $N(0, 1)$. Vi ændrer altså kun *informationsindholdet* i prædiktionen --- ikke virkelighedens fordeling.

---

## Fra $Z$ til varigheder: $\Phi$-transformationen

De latente $Z$-værdier er abstrakte --- vi har brug for at oversætte dem til konkrete aktivitetsvarigheder og throughput-prædiktioner.

### Probability integral transform

For $Z_{\text{actual}} \sim N(0, 1)$ definerer vi:

$$u_{\text{actual}} = \Phi(Z_{\text{actual}})$$

hvor $\Phi$ er standard normalfordelingens CDF (cumulative distribution function). Da $Z_{\text{actual}}$ er standard normalfordelt, følger det af **probability integral transform** at:

$$u_{\text{actual}} \sim \text{Uniform}(0, 1)$$

Intuitivt: $\Phi$ mapper enhver standard normalfordelt værdi til en percentil mellem 0 og 1. En $Z_{\text{actual}} = 0$ giver $u_{\text{actual}} = 0.5$ (medianen). En høj $Z_{\text{actual}} = 2$ giver $u_{\text{actual}} \approx 0.977$ (97.7-percentilen).

### Brug i Weibull inverse CDF sampling

$u_{\text{actual}}$ bruges som en *fast percentil* i Weibull inverse CDF-sampling til at bestemme aktivitetsvarigheder:

$$\text{duration} = \text{scale} \cdot \big(-\ln(1 - u_{\text{actual}})\big)^{\theta}$$

hvor scale $= \exp(\alpha + \text{koefficienter} \cdot \text{features})$ og $\theta = 0.3908$.

### Analogt for prædiktionen

$$u_{\text{pred}} = \Phi(Z_{\text{pred}})$$

$u_{\text{pred}}$ bruges til at beregne en throughput-prediktion via Weibull inverse CDF, som derefter indgår i NPS-prædiktionsmodellen.

---

## Hard $Z$ vs Soft $Z$

Study 3 implementerer to "modes" for hvordan $Z_{\text{actual}}$ påvirker aktivitetsvarigheder. De repræsenterer to forskellige grader af latent struktur.

### Hard $Z$ mode

I hard mode bruger **alle aktiviteter** i en sag den *samme* percentil:

$$u_{\text{actual}} = \Phi(Z_{\text{actual}})$$

Konsekvens: en "kompleks" sag (høj $Z_{\text{actual}}$) får *konsistent* lange varigheder på tværs af alle sine aktiviteter. Der er ingen individuel tilfældig variation.

$$\text{corr}(Z_{\text{actual}},\; \text{throughput}) \approx 1$$

Hard mode er den *stærkeste* test af hypotesen, fordi $Z$ indeholder maksimalt signal om den sande throughput-tid.

### Soft $Z$ mode

I soft mode indgår $Z_{\text{actual}}$ som en *feature* i den lineære prædiktor for aktivitetsvarigheder:

$$\text{linear\_pred} = \alpha + \text{topic\_coef} + \text{activity\_coef} + \ldots + \beta_Z \cdot Z_{\text{actual}}$$

Aktiviteterne har stadig individuel tilfældig Weibull-sampling --- $Z_{\text{actual}}$ forskyder blot scale-parameteren.

$$\text{corr}(Z_{\text{actual}},\; \text{throughput}) \approx 0.5$$

Soft mode er et **robusthedscheck**: den repræsenterer en mere realistisk situation hvor sagskompleksitet kun forklarer en del af variationen.

### Hvorfor begge?

| Mode | Signal-styrke | Formål |
|------|--------------|---------|
| Hard $Z$ | Maksimal ($r \approx 1$) | Stærkest mulig test: hvis NPS ikke divergerer fra LRTF her, gør den det aldrig |
| Soft $Z$ | Moderat ($r \approx 0.5$) | Realismecheck: bekræfter at resultatet holder under mere realistiske betingelser |

---

## $\beta_Z$ kalibrering

I soft mode skal koefficienten $\beta_Z$ vælges så $Z_{\text{actual}}$ har en meningsfuld men ikke dominerende indflydelse på aktivitetsvarigheder.

### Målkorrelation

Vi ønsker:

$$\text{corr}(Z_{\text{actual}},\; \log(\text{duration})) = 0.5$$

### Analytisk tilnærmelse

I den lineære prædiktor er $\log(\text{duration}) \approx \alpha + \ldots + \beta_Z \cdot Z + \text{Weibull-støj}$. Korrelationen mellem $Z$ og $\log(\text{duration})$ er:

$$\text{corr} = \frac{\beta_Z}{\sqrt{\beta_Z^2 + \text{Var}(\log \text{Weibull})}}$$

### Numerisk metode

Da den analytiske formel kun er en tilnærmelse (Weibull-variansen afhænger af shape-parameteren og andre features), bruger vi **binær søgning** over $\beta_Z \in [0, 2]$:

1. Vælg en kandidatværdi for $\beta_Z$
2. Simuler et stort antal aktiviteter med tilfældige $Z$-værdier
3. Beregn den empiriske korrelation mellem $Z$ og $\log(\text{duration})$
4. Juster $\beta_Z$ op eller ned alt efter om korrelationen er for lav eller høj
5. Gentag indtil $|\text{corr} - 0.5| < \epsilon$

**Kalibreret værdi:** $\beta_Z \approx 0.285$

---

## $\rho$-niveauer i eksperimentet

Study 3 tester fem niveauer af prædiktionsnøjagtighed:

| $\rho$ | Fortolkning | Eksempel |
|--------|-------------|----------|
| $0.00$ | **Ren støj.** Prædiktionen indeholder ingen information om virkeligheden. $Z_{\text{pred}}$ er fuldstændig uafhængig af $Z_{\text{actual}}$. | Tilfældigt gået |
| $0.22$ | **Baseline.** Svarer cirka til Study 2's faktiske prædiktionsnøjagtighed baseret på sæsondummy-variabler. | Simpel regressionsmodel |
| $0.50$ | **Medium.** Moderat prædiktiv evne. | Fx basic NLP på sagsbeskrivelser eller emails |
| $0.85$ | **Høj.** Avanceret prædiktiv evne. | Fx sofistikeret machine learning eller human-in-the-loop |
| $1.00$ | **Perfekt information.** $Z_{\text{pred}} = Z_{\text{actual}}$. Teoretisk loft for prædiktionsnøjagtighed. | Orakel (urealistisk, men nyttigt som ovre grænse) |

Ved $\rho = 0$: $Z_{\text{pred}} = \varepsilon$ (ren støj), og prædiktionen er tilfældig.

Ved $\rho = 1$: $Z_{\text{pred}} = Z_{\text{actual}}$ (da $\sqrt{1 - 1^2} = 0$), og prædiktionen er perfekt.

Spredningen over disse fem niveauer giver os et komplet billede af, hvordan værdien af prædiktiv information påvirker kødisciplinens effektivitet.
