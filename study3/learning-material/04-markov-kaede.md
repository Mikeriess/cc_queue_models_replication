# Absorberende Markov-kæder --- aktivitetssekvenser

## Hvad er en Markov-kæde?

En **Markov-kæde** er en stokastisk proces der hopper mellem et endeligt antal tilstande, hvor næste tilstand *kun afhænger af den nuværende tilstand* --- ikke af historikken. Denne egenskab kaldes **memoryless property** (hukommelsesløshed).

### Dagligdags eksempel

Tænk på vejret som en simpel Markov-kæde med to tilstande: *sol* og *regn*. Hvis det er solskin i dag, er der fx 80% chance for sol i morgen og 20% chance for regn. Hvis det regner i dag, er der 60% chance for regn i morgen og 40% chance for sol. Det afgørende er at morgendagens vejr kun afhænger af *dagens* vejr --- ikke om det har regnet hele ugen eller kun i dag.

Formelt: for en Markov-kæde $(X_t)_{t \geq 0}$ gælder:

$$P(X_{t+1} = j \mid X_t = i, X_{t-1}, \ldots, X_0) = P(X_{t+1} = j \mid X_t = i)$$

---

## Tilstande i Study 3

I simulationen gennemgår hver sag en sekvens af *aktiviteter*. Hvilken aktivitetstype der kommer næst modelleres som en Markov-kæde med 4 tilstande:

| Tilstandsnummer | Navn | Type |
|-----------------|------|------|
| 1 | Task-Reminder | Transient (midlertidig) |
| 2 | Interaction | Transient |
| 3 | Email | Transient |
| 4 | END | Absorbing (permanent) |

De første tre tilstande er **transiente** ("transient states"): processen kan forlade dem igen. END er en **absorberende tilstand** ("absorbing state"): når processen når END, forbliver den der permanent. I praksis betyder det at sagen er *lukket*.

En typisk sag starter i en af de transiente tilstande (oftest Interaction), hopper rundt mellem aktivitetstyper, og ender til sidst i END.

---

## Transitionsmatricen

Sandsynlighederne for at hoppe fra en tilstand til en anden samles i en $4 \times 4$ **transitionsmatrix** $P$:

$$P = \begin{pmatrix} 0.08 & 0.00 & 0.67 & 0.25 \\ 0.00 & 0.02 & 0.96 & 0.02 \\ 0.00 & 0.02 & 0.45 & 0.53 \\ 0.00 & 0.00 & 0.00 & 1.00 \end{pmatrix}$$

Læst som tabel:

| From \ To | Task-Rem | Interaction | Email | END |
|-----------|----------|-------------|-------|-----|
| **Task-Rem** | 0.08 | 0.00 | 0.67 | 0.25 |
| **Interaction** | 0.00 | 0.02 | 0.96 | 0.02 |
| **Email** | 0.00 | 0.02 | 0.45 | 0.53 |
| **END** | 0.00 | 0.00 | 0.00 | 1.00 |

### Hvordan læser man matricen?

- **Hver række summer til 1.** Række $i$ angiver sandsynlighedsfordelingen over næste tilstand, givet at processen er i tilstand $i$.
- **Rækken for END er $[0, 0, 0, 1]$** --- når man er i END, forbliver man der med sandsynlighed 1. Det er præcis definitionen på en absorberende tilstand.
- **Interaction $\to$ Email**: sandsynlighed 0.96. Langt de fleste Interactions efterfølges af en Email.
- **Email $\to$ END**: sandsynlighed 0.53. Lidt over halvdelen af alle Emails afslutter sagen.
- **Interaction $\to$ END**: sandsynlighed 0.02. Det er sjældent at en sag lukkes direkte efter en Interaction.

---

## Initial sandsynligheder

Når en ny sag oprettes, bestemmes den første aktivitetstype af **initialsandsynlighederne**:

$$\boldsymbol{\pi}_0 = [0.00, \; 0.92, \; 0.08, \; 0.00]$$

| Tilstand | Sandsynlighed | Fortolkning |
|----------|---------------|-------------|
| Task-Reminder | 0.00 | Ingen sager starter med en Task-Reminder |
| Interaction | 0.92 | 92% af sager starter med en Interaction |
| Email | 0.08 | 8% af sager starter med en Email |
| END | 0.00 | Ingen sager starter som lukkede |

---

## Hvad er absorption?

END er en **absorberende tilstand**: når processen når END, stopper den. Men *når* alle sager til sidst END? Svaret er ja --- og det kan vi argumentere for:

1. Fra **Email** er der 53% sandsynlighed for at nå END direkte ($P_{\text{Email} \to \text{END}} = 0.53 > 0$).
2. Fra **Interaction** nåes Email med sandsynlighed 0.96, og derfra nåes END med sandsynlighed 0.53.
3. Fra **Task-Reminder** nåes Email med sandsynlighed 0.67, og derfra END.

Alle transiente tilstande har en sti til END med positiv sandsynlighed. Derfor vil processen med sandsynlighed 1 *til sidst* nå END --- uanset hvor den starter. Matematisk:

$$P(\text{absorption}) = 1$$

---

## Fundamental-matricen og forventet antal aktiviteter

En af de stærkeste egenskaber ved absorberende Markov-kæder er at vi kan beregne det *forventede antal besøg* i hver transient tilstand før absorption --- uden at simulere.

### Opsætning

Vi isolerer den $3 \times 3$ **transiente delmatrix** $Q$ (de øverste 3 rækker og kolonner af $P$):

$$Q = \begin{pmatrix} 0.08 & 0.00 & 0.67 \\ 0.00 & 0.02 & 0.96 \\ 0.00 & 0.02 & 0.45 \end{pmatrix}$$

### Fundamental-matricen $N$

Den **fundamentale matrix** er defineret som:

$$N = (I - Q)^{-1}$$

hvor $I$ er $3 \times 3$ identitetsmatricen. Elementet $N_{ij}$ angiver det *forventede antal gange* processen besøger tilstand $j$, givet at den startede i tilstand $i$.

### Beregning for Study 3

Først beregner vi $I - Q$:

$$I - Q = \begin{pmatrix} 1 - 0.08 & 0 - 0.00 & 0 - 0.67 \\ 0 - 0.00 & 1 - 0.02 & 0 - 0.96 \\ 0 - 0.00 & 0 - 0.02 & 1 - 0.45 \end{pmatrix} = \begin{pmatrix} 0.92 & 0.00 & -0.67 \\ 0.00 & 0.98 & -0.96 \\ 0.00 & -0.02 & 0.55 \end{pmatrix}$$

For at finde $N = (I - Q)^{-1}$ kan vi bruge standard matrixinversion. Resultatet er (afrundet):

$$N = (I - Q)^{-1} \approx \begin{pmatrix} 1.087 & 0.000 & 1.325 \\ 0.000 & 1.055 & 1.838 \\ 0.000 & 0.037 & 1.855 \end{pmatrix}$$

### Fortolkning

- $N_{11} = 1.087$: en sag der starter i Task-Reminder besøger Task-Reminder i gennemsnit 1.087 gange (inkl. startbesøg).
- $N_{13} = 1.325$: en sag der starter i Task-Reminder besøger Email i gennemsnit 1.325 gange.
- $N_{23} = 1.838$: en sag der starter i Interaction besøger Email i gennemsnit 1.838 gange.

### Forventet antal aktiviteter pr. sag

Summen af række $i$ i $N$ giver det forventede totale antal aktiviteter før absorption, givet start i tilstand $i$:

| Starttilstand | Forventet antal aktiviteter |
|---------------|-----------------------------|
| Task-Reminder | $1.087 + 0.000 + 1.325 \approx 2.4$ |
| Interaction | $0.000 + 1.055 + 1.838 \approx 2.9$ |
| Email | $0.000 + 0.037 + 1.855 \approx 1.9$ |

Da 92% af sagerne starter i Interaction og 8% i Email, er det *vægtet gennemsnit*:

$$E[\text{aktiviteter}] \approx 0.92 \times 2.9 + 0.08 \times 1.9 \approx 2.8$$

I praksis har sager altså typisk **2-4 aktiviteter** før de afsluttes.

### Vigtig pointe

Fundamental-matricen viser at vores Markov-kæde giver relativt *korte* aktivitetssekvenser. Det skyldes den høje absorptionssandsynlighed fra Email ($P_{\text{Email} \to \text{END}} = 0.53$). Sekvensen $\text{Interaction} \to \text{Email} \to \text{END}$ er langt den mest almindelige sti --- over halvdelen af sagerne følger netop denne sti.
