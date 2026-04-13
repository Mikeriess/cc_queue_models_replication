# Fig. S3b.4 — Forklaring: Skarp transition + plateau-effekt

## Kontekst

I artiklens kø-system prioriteres ventende kundeservicesager efter en
**NPS-prædiktion**. For hver sag ved ankomst beregnes en forudsagt
Net Promoter Score:

```
NPS_hat = α + β × log(predicted_throughput + 1) - 1
```

hvor `α` er interceptet og `β ≈ -0.095` er den kalibrerede hældning.
Prioritetsscoren for en sag er

```
priority(i) = | NPS_hat_i − 7.5 |
```

Sager tættest på midtpunktet 7.5 (de "passive" kunder der lige så snildt
kan blive promoters eller detractors) får højest prioritet. Lav prioritetsscore
= tidlig betjening.

## Hvad er intercept α?

Interceptet er baseline-værdien af den forudsagte NPS når throughput er 0:

- **α = 10.22 (original):** Artiklens kalibrerede værdi. Med realistiske
  throughput-værdier ligger NPS_hat typisk mellem 8.0 og 9.5 — **altid over
  7.5-midtpunktet**. Prioritetsscoren `|NPS_hat − 7.5|` bliver dermed en
  monoton funktion af throughput (lavere = højere prioritet), præcis som LRTF.
- **α = 8.0 (counterfactual):** Prædiktionerne flyttes nedad så NPS_hat
  ligger omkring 5.8-7.3 for korte sager og 7.3-8.5 for lange. Nu **krydser
  fordelingen 7.5**, og prioriteten bliver V-formet i throughput — både korte
  og lange sager nedprioriteres, mens mellemlange får højest prioritet.

Study 3b varierer interceptet (12 niveauer fra 10.22 ned til 6.5) for at
måle hvornår og hvor meget NPS-prioritering divergerer fra LRTF
(longest-remaining-time-first).

## Hvad er ρ (rho)?

ρ er **latent korrelation** mellem prædiktionsmodellen og virkeligheden
(implementeret som korrelation mellem `z_pred` og `z_actual` i
simulationen). Ρ = 0 betyder pure støj i prædiktionen; ρ = 1 betyder perfekt
information. Vores reelle data har ρ ≈ 0.22.

## Sådan læses plottet

- **X-aksen** er vendt om: baseline-interceptet (10.22) er til venstre,
  faldende værdier til højre — læses som "hvad sker der når vi sænker α?"
- **Y-aksen** er forskellen i gennemsnitlig NPS-respons mellem en kø der
  prioriterer efter NPS vs. en kø der prioriterer efter LRTF. Positiv = NPS
  vinder. Nul-linjen markerer ingen forskel.
- **Hver farvet kurve** svarer til ét ρ-niveau. Højere ρ (gul) =
  mere præcise prædiktioner; lavere ρ (mørk) = mere støjede prædiktioner.
- **Fejlbarer** er 95% konfidensintervaller beregnet fra de 100
  replikationer pr. betingelse.
- **Rød zone** (α = 9.0–9.5): området hvor NPS_hat-fordelingen *begynder*
  at krydse 7.5-midtpunktet.
- **Grøn zone** (α ≤ 8.75): plateau-området hvor fordelingen er fuldt
  krydset, og resultatet ikke længere afhænger af hvor meget mere vi sænker α.

## To strukturelle pointer

### Pointe 1 — Skarp, næsten binær transition

Mellem α = 10.22 og α = 9.5 er NPS præcis lige så god som LRTF (forskellen
er 0.000 ± numerisk støj). Ved α = 9.0 begynder effekten at dukke op
partial, og ved α = 8.75 er effekten **fuldt aktiveret**.

Årsag: `|NPS_hat − 7.5|` kun producerer en *anden* rangorden end LRTF
når NPS_hat-værdierne ligger på *begge* sider af 7.5. Så længe hele
fordelingen er > 7.5, er `|NPS_hat − 7.5| = NPS_hat − 7.5`, som bevarer
rangordenen fra throughput-prædiktionen. Transitionen er skarp fordi den
strukturelle betingelse "fordelingen krydser 7.5" enten er opfyldt eller
ikke.

### Pointe 2 — Plateau: dybden af krydsning er ligegyldig

Alle kurver er helt flade fra α = 8.75 og ned til α = 6.5. Det betyder
at **intercepts 8.75, 8.5, 8.25, 8.0, 7.75, 7.5, 7.25, 7.0 og 6.5
producerer identiske resultater** (op til 6 decimaler). Vores 100
replikationer × 8 intercept-niveauer viser nul variation.

Det er ikke en målefejl. Det er et **strukturelt fænomen**: når først
fordelingen krydser 7.5-midtpunktet, er den specifikke placering af
fordelingens centroid ligegyldig. V-formen omkring 7.5 sorterer sagerne
identisk uanset om midtpunktet ligger 0.5 eller 3 enheder under NPS_hat's
gennemsnit.

## Hvorfor betyder det noget

Artiklens kvalitative konklusion (Study 2) var at NPS-prioritering gør
kunder gladere end FCFS. Vores Study 3 fandt at NPS ≡ LRTF — ingen fordel
ud over den simplere LRTF-algoritme. Dette plot viser **hvordan denne
ækvivalens kan brydes** og **hvor skør betingelserne er for at bryde den**:

1. Ækvivalensen (NPS ≡ LRTF) er ikke en tilfældighed — det er en strukturel
   konsekvens af at artiklens kalibrerede α = 10.22 placerer hele NPS_hat-
   fordelingen over 7.5.
2. For at bryde ækvivalensen skal α sænkes tilstrækkeligt til at krydse
   7.5. I et virkeligt system svarer det til at ændre *hvilken NPS-værdi*
   der defineres som "passiv" (nuværende konvention: scores 7-8).
3. Det er en **binær beslutning** — enten krydser fordelingen eller ej.
   Der findes ikke en "lille justering" der giver en "lille forbedring".

Samtidig viser plottet at selv når effekten er fuldt aktiveret (plateau),
er fordelen over LRTF kun ca. +0.037 NPS-point for individer og +1.39
procentpoint for organisations-NPS ved ρ = 1.00 — og mindre ved lavere
prædiktionsnøjagtighed. Det er en reel men beskeden gevinst.
