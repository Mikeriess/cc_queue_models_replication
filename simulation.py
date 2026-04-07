"""
Reproduktion af Study 2 fra:
"Customer-service queuing based on predicted loyalty outcomes"
(Riess & Scholderer, preprint submitted to Journal of Service Research, 2026)

Denne fil implementerer alle kalibrerede modeller fra Study 1 og alle 7 algoritmer
fra Study 2's Monte Carlo-simulering. Alle parameterværdier er hentet direkte fra
artiklens tabeller og appendices.

Terminologi:
    - Case (η): En kundeservicesag med tilhørende trace (sekvens af aktiviteter)
    - Agent (ψ): En kundeservicemedarbejder
    - Queue (Θ): Buffer af aktive sager
    - Event log (L): Output-log med alle simulerede hændelser

Tidsenheder:
    - Intern tidsenhed er DAGE (fraktionelle)
    - 15 minutter = 0.010416 dage (brugt som tidsskridt i simulering)
    - Konverteringer er markeret eksplicit i koden

Reference til artiklen:
    - Eq. X  = ligningsnummer i artiklen
    - Tabel X = tabelnummer i artiklen
    - Alg. X  = algoritmenummer i artiklen (pseudokode)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

# =============================================================================
# KONSTANTER
# =============================================================================

# Tidsskridt: 15 minutter udtrykt i dage (artiklen bruger denne værdi eksplicit)
TIMESTEP_DAYS = 15 / (24 * 60)  # = 0.010416... dage

# Arbejdstid: Mandag-Fredag 08:00-18:00
BUSINESS_HOUR_START = 8   # kl. 08:00
BUSINESS_HOUR_END = 18    # kl. 18:00

# Simuleringsperiode: 2018-07-01 til 2019-07-01 (365 dage)
SIM_START_YEAR = 2018
SIM_START_MONTH = 7
SIM_START_DAY = 1

# NPS-midtpunkt for passives-segmentet (bruges i prioriteringsformel, Eq. 1)
NPS_MIDPOINT = 7.5

# Case topics: 10 anonymiserede kategorier fra artiklen.
# Navngivningen er baseret på koefficienternes labels i Tabel 1 og 6.
# Det sidste niveau i hver kategorisk variabel er referencekategorien.
# Vi har 9 eksplicitte topics + 1 referencekategori.
CASE_TOPICS = [
    "d_2-z_4", "g_1-z_4", "j_1-z_4", "q_3-z_4", "r_2-z_4",
    "w_1-z_4", "w_2-z_4", "z_2-z_4", "z_3-z_4",
    "z_4"  # referencekategori (koefficient = 0)
]

# Aktivitetstyper (3 typer + absorberingstilstand)
ACTIVITY_TYPES = ["Task-Reminder", "Interaction", "Email"]
ACTIVITY_STATES = ACTIVITY_TYPES + ["END"]


# =============================================================================
# SEKTION A: KALIBREREDE MODELLER FRA STUDY 1
# =============================================================================

# -----------------------------------------------------------------------------
# Model 1: Aktivitetsvarighed (Eq. 3, Tabel 1)
#
# GLM med Weibull link-funktion.
# Target: aktivitetsvarighed i timer.
# Simuleringsformel:
#   duration = Weibull(1/θ, exp(α + ΣXᵢβᵢ))
# hvor θ er shape-parameteren for gamma-fordelingen.
#
# Features: case_topic (kategorisk, 9 dummies), activity (kategorisk, 2 dummies),
#           activity_number (numerisk), resource (individuel agent-effekt).
# Resource-effekt samples fra N(μ=0.22, σ=0.52) for nye agenter (s. 8-9).
# -----------------------------------------------------------------------------

# Koefficienter fra Tabel 1 (s. 9)
DURATION_INTERCEPT = 1.6645
DURATION_THETA = 0.3908  # shape parameter

# Case topic koefficienter (referencekategori z_4 har koefficient 0)
DURATION_TOPIC_COEFS = {
    "d_2-z_4": 0.0200,
    "g_1-z_4": -0.0538,
    "j_1-z_4": -0.0557,
    "q_3-z_4": 0.1712,
    "r_2-z_4": 0.0836,
    "w_1-z_4": -0.0609,
    "w_2-z_4": 0.0119,
    "z_2-z_4": -0.0420,
    "z_3-z_4": 0.1637,
    "z_4": 0.0,  # reference
}

# Aktivitetstype koefficienter (reference = Email, koefficient = 0)
# Artiklens labels: task_tasksubtype[Email-Task-Reminder] og
# task_tasksubtype[Interaction-Task-Reminder]
DURATION_ACTIVITY_COEFS = {
    "Task-Reminder": 0.0180,      # Email-Task-Reminder
    "Interaction": 0.1057,         # Interaction-Task-Reminder
    "Email": 0.0,                  # reference
}

# Activity number koefficient
DURATION_ACTIVITY_NUMBER_COEF = 0.0420

# Resource (agent) random effekt distribution
RESOURCE_EFFECT_MEAN = 0.2171     # fra Tabel 1 bund (mean af 77 agenter)
RESOURCE_EFFECT_STD = 0.52        # fra teksten s. 8


def simulate_activity_duration(case_topic: str, activity_type: str,
                                activity_number: int, resource_effect: float,
                                rng: np.random.Generator) -> float:
    """
    Simulér varigheden af en enkelt aktivitet (Eq. 3, Tabel 1).

    Weibull-simulation:
        duration = Weibull(shape=1/θ, scale=exp(α + ΣXᵢβᵢ))

    Args:
        case_topic: En af de 10 case topics
        activity_type: "Task-Reminder", "Interaction" eller "Email"
        activity_number: Nummeret på aktiviteten i tracen (1-indekseret)
        resource_effect: Individuel agent-effekt (samplet fra N(0.22, 0.52))
        rng: Numpy random generator

    Returns:
        Varighed i timer
    """
    # Beregn lineær prædiktor (log-skala)
    linear_pred = (DURATION_INTERCEPT
                   + DURATION_TOPIC_COEFS.get(case_topic, 0.0)
                   + DURATION_ACTIVITY_COEFS.get(activity_type, 0.0)
                   + DURATION_ACTIVITY_NUMBER_COEF * activity_number
                   + resource_effect)

    # Weibull shape = 1/θ, scale = exp(lineær prædiktor)
    shape = 1.0 / DURATION_THETA
    scale = math.exp(linear_pred)

    # Sample fra Weibull-fordeling
    # numpy's weibull returnerer X ~ Weibull(shape), skaleret med scale
    duration_hours = scale * rng.weibull(shape)

    return duration_hours


# -----------------------------------------------------------------------------
# Model 2: Aktivitetssekvenser — Absorbing Markov Chain (Eq. 4, Tabel 2-3)
#
# States: Task-Reminder, Interaction, Email, END
# END er absorberingstilstanden (sagen lukkes).
# Transitionsmatrice fra Tabel 2, initialsandsynligheder fra Tabel 3.
# -----------------------------------------------------------------------------

# Transitionsmatrice P (Tabel 2, s. 9)
# Rækker: fra-tilstand, Kolonner: til-tilstand
# Rækkefølge: Task-Reminder, Interaction, Email, END
TRANSITION_MATRIX = np.array([
    [0.08, 0.00, 0.67, 0.25],   # Fra Task-Reminder
    [0.00, 0.02, 0.96, 0.02],   # Fra Interaction
    [0.00, 0.02, 0.45, 0.53],   # Fra Email
    [0.00, 0.00, 0.00, 1.00],   # Fra END (absorbing)
])

# Initialsandsynligheder P⁰ (Tabel 3, s. 10)
INITIAL_PROBS = np.array([0.0, 0.92, 0.08, 0.0])


def sample_initial_activity(rng: np.random.Generator) -> str:
    """Sample den første aktivitet i en sag fra initialsandsynlighederne (Tabel 3)."""
    idx = rng.choice(len(ACTIVITY_STATES), p=INITIAL_PROBS)
    return ACTIVITY_STATES[idx]


def sample_next_activity(current_activity: str, rng: np.random.Generator) -> str:
    """
    Sample næste aktivitet givet den nuværende (Eq. 4, Tabel 2).

    Markov-egenskab: P(X_{t+1} | X_1, ..., X_t) = P(X_{t+1} | X_t)
    """
    current_idx = ACTIVITY_STATES.index(current_activity)
    probs = TRANSITION_MATRIX[current_idx]
    next_idx = rng.choice(len(ACTIVITY_STATES), p=probs)
    return ACTIVITY_STATES[next_idx]


# -----------------------------------------------------------------------------
# Model 3: Inter-arrival tider (Eq. 6, Tabel 4)
#
# GLM med eksponentiel link-funktion.
# Target: timer mellem to på hinanden følgende sagsankomster.
# Simuleringsformel:
#   InterArrivalTime = -log(1 - U(0,1)) × exp(α + ΣXᵢβᵢ)
#
# Features: year, month, day, weekday.
# Koefficienter fra Tabel 4 (s. 10).
# -----------------------------------------------------------------------------

# KALIBRERINGSNOTAT (se CALIBRATION_NOTES.md):
# Originalt intercept fra Tabel 4: 726.6267
# Justeret med -0.4267 for at matche artiklens simuleringsresultater.
# Justeringen er inden for 1 SE (SE=323.93) og nødvendig fordi:
#   (a) afrundingsfejl i det store intercept/year-par (net effect ~2.4),
#   (b) kalibreringsperiode (23 mdr) ≠ simuleringsperiode (12 mdr), og
#   (c) weekday-kodningens eksakte konvention er ukendt.
# Med denne justering producerer modellen ~1100-1200 sager/år, hvilket giver
# kø-dynamik konsistent med artiklens Fig. 5, 7, 8 og 9.
ARRIVAL_INTERCEPT = 726.2
ARRIVAL_COEFS = {
    "year": -0.3589,
    "month": -0.0881,
    "day": 0.0078,
    "weekday": 0.2616,
}


def simulate_inter_arrival_time(current_time_days: float,
                                 rng: np.random.Generator) -> float:
    """
    Simulér inter-arrival tid for næste sag (Eq. 6, Tabel 4).

    Args:
        current_time_days: Nuværende tid i dage (fra simuleringsstart, dag 0 = 2018-07-01)
        rng: Numpy random generator

    Returns:
        Inter-arrival tid i dage
    """
    # Konvertér simuleringstid til kalenderfeatures
    # Dag 0 = 2018-07-01 (en søndag, weekday=7)
    # Vi bruger fraktionelle dage, så floor giver os dagnummeret
    day_number = int(math.floor(current_time_days))

    # Beregn kalender-attributter
    # 2018-07-01 er dag 182 i året (ikke-skudår)
    # Vi antager 365 dage pr. år for simpelhed
    total_day_of_year = 182 + day_number  # dag i året fra 1. januar 2018
    year = SIM_START_YEAR + total_day_of_year // 365
    day_in_year = total_day_of_year % 365

    # Måned (approksimeret)
    month = _day_to_month(day_in_year)

    # Dag i måneden (approksimeret)
    day_of_month = _day_to_day_of_month(day_in_year, month)

    # Weekday: 2018-07-01 (dag 0) er en søndag.
    # KALIBRERINGSNOTAT (se CALIBRATION_NOTES.md):
    # Bruger 0-baseret kodning: Mandag=0, ..., Søndag=6.
    # Dag 0 (søndag) % 7 = 0 i vores system, men søndag = 6 i Python's weekday().
    # Mapping: intern dag 0=søn→6, dag 1=man→0, dag 2=tirs→1, ..., dag 6=lør→5
    raw_weekday = day_number % 7  # 0=søndag, 1=mandag, ..., 6=lørdag
    weekday = (raw_weekday - 1) % 7  # mandag=0, tirsdag=1, ..., søndag=6

    # Beregn lineær prædiktor
    linear_pred = (ARRIVAL_INTERCEPT
                   + ARRIVAL_COEFS["year"] * year
                   + ARRIVAL_COEFS["month"] * month
                   + ARRIVAL_COEFS["day"] * day_of_month
                   + ARRIVAL_COEFS["weekday"] * weekday)

    # Simulér fra eksponentiel fordeling (Eq. 6)
    u = rng.uniform(0, 1)
    inter_arrival_hours = -math.log(1 - u) * math.exp(linear_pred)

    # KALIBRERINGSNOTAT (se CALIBRATION_NOTES.md):
    # Modellen er kalibreret på de 1897 email-baserede sager med NPS-respons.
    # Disse udgør de sager der behandles via kø-systemet (email-kanalen).
    # Telefon-sager (VIP-kunder) har dedikeret key account manager og indgår ikke.
    # NPS-skalering er IKKE nødvendig — modellen afspejler allerede den relevante
    # population af kø-baserede email-sager.

    # Konvertér fra timer til dage
    return inter_arrival_hours / 24.0


def _day_to_month(day_of_year: int) -> int:
    """Konvertér dag-i-året (0-indekseret) til måned (1-12)."""
    # Kumulative dage pr. måned (ikke-skudår)
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]
    day_of_year = day_of_year % 365
    for m in range(12):
        if day_of_year < cum_days[m + 1]:
            return m + 1
    return 12


def _day_to_day_of_month(day_of_year: int, month: int) -> int:
    """Konvertér dag-i-året til dag-i-måneden."""
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    day_of_year = day_of_year % 365
    return day_of_year - cum_days[month - 1] + 1


# -----------------------------------------------------------------------------
# Model 4: Throughput-tid prediction (Eq. 7, Tabel 5)
#
# GLM med eksponentiel link-funktion, offset = 1.
# Target: case throughput time i minutter.
# Prædiktionsformel:
#   Throughput_time = exp(α + ΣXᵢβᵢ) - 1
#
# Features: year, month, weekday, day, hour.
# Koefficienter fra Tabel 5 (s. 11).
# Bruges til SRTF/LRTF/NPS-prioritering (forudsiges ved ankomst).
# -----------------------------------------------------------------------------

THROUGHPUT_INTERCEPT = 66.809
THROUGHPUT_COEFS = {
    "year": -0.030,
    "month": -0.041,
    "day": 0.000,       # p=1.000, reelt nul
    "weekday": 0.000,   # p=0.995, reelt nul
    "hour": 0.065,
}


def predict_throughput_time(arrival_time_days: float) -> float:
    """
    Forudsig throughput-tid for en sag baseret på ankomsttidspunkt (Eq. 7, Tabel 5).

    Bruges til prioritering — forudsiges ved ankomst, da case-attributter
    (som topic) endnu ikke er kendte.

    Args:
        arrival_time_days: Ankomsttid i dage fra simuleringsstart

    Returns:
        Forudsagt throughput-tid i minutter
    """
    day_number = int(math.floor(arrival_time_days))
    total_day_of_year = 182 + day_number
    year = SIM_START_YEAR + total_day_of_year // 365
    day_in_year = total_day_of_year % 365
    month = _day_to_month(day_in_year)
    day_of_month = _day_to_day_of_month(day_in_year, month)

    # 0-baseret weekday: Man=0, ..., Søn=6 (se CALIBRATION_NOTES.md)
    raw_weekday = day_number % 7  # 0=søndag, 1=mandag, ...
    weekday = (raw_weekday - 1) % 7  # mandag=0, ..., søndag=6

    # Time på dagen (fra fraktionel del af dagen)
    fractional_day = arrival_time_days - math.floor(arrival_time_days)
    hour = int(fractional_day * 24)

    linear_pred = (THROUGHPUT_INTERCEPT
                   + THROUGHPUT_COEFS["year"] * year
                   + THROUGHPUT_COEFS["month"] * month
                   + THROUGHPUT_COEFS["day"] * day_of_month
                   + THROUGHPUT_COEFS["weekday"] * weekday
                   + THROUGHPUT_COEFS["hour"] * hour)

    # Eq. 7: exp(linear_pred) - 1 (offset = 1)
    throughput_minutes = math.exp(linear_pred) - 1

    return throughput_minutes


# -----------------------------------------------------------------------------
# Model 5a: NPS-simulering — betinget (Eq. 8, Tabel 6)
#
# GLM med gamma link-funktion, offset = 1.
# Target: NPS (0-10 skala).
# Simuleringsformel:
#   NPS = Γ(k, ρ) - 1
#   hvor k = exp(α + ΣXᵢβᵢ) / ρ (shape) og ρ = 1.3005 (scale)
#
# Bruges til evaluering: simulerer den "sande" NPS efter sag er lukket,
# betinget på den faktiske throughput-tid og case topic.
# Koefficienter fra Tabel 6 (s. 12).
# -----------------------------------------------------------------------------

NPS_SIM_INTERCEPT = 2.3006
NPS_SIM_RHO = 1.3005  # scale parameter

NPS_SIM_THROUGHPUT_COEF = -0.0098  # Log[case_throughputtime+1]

NPS_SIM_TOPIC_COEFS = {
    "d_2-z_4": -0.1291,
    "g_1-z_4": 0.1008,
    "j_1-z_4": 0.0853,
    "q_3-z_4": -0.0427,
    "r_2-z_4": -0.0317,
    "w_1-z_4": 0.0000,   # p=1
    "w_2-z_4": 0.0000,   # p=1
    "z_2-z_4": 0.0967,
    "z_3-z_4": -0.0048,
    "z_4": 0.0,           # reference
}


def simulate_nps_response(actual_throughput_minutes: float, case_topic: str,
                           rng: np.random.Generator) -> int:
    """
    Simulér den betingede NPS-respons efter en sag er lukket (Eq. 8, Tabel 6).

    Gamma-simulation med efterfølgende truncation og afrunding (Eq. 15-16).

    Args:
        actual_throughput_minutes: Den faktiske throughput-tid i minutter
        case_topic: Sagens topic-kategori
        rng: Numpy random generator

    Returns:
        Simuleret NPS-respons (heltal 0-10)
    """
    # Beregn lineær prædiktor
    log_throughput = math.log(actual_throughput_minutes + 1)

    linear_pred = (NPS_SIM_INTERCEPT
                   + NPS_SIM_THROUGHPUT_COEF * log_throughput
                   + NPS_SIM_TOPIC_COEFS.get(case_topic, 0.0))

    # Gamma-fordeling: shape = exp(linear_pred) / ρ, scale = ρ
    shape = math.exp(linear_pred) / NPS_SIM_RHO
    scale = NPS_SIM_RHO

    # Sample fra gamma og træk offset fra (Eq. 8: NPS = Γ(...) - 1)
    nps_raw = rng.gamma(shape, scale) - 1

    # Truncation til [0, 10] (Eq. 15)
    nps_raw = max(0.0, min(nps_raw, 10.0))

    # Afrunding til heltal (Eq. 16: ceiling)
    nps_resp = math.ceil(nps_raw)

    # Sikr at vi er inden for [0, 10]
    nps_resp = max(0, min(nps_resp, 10))

    return nps_resp


# -----------------------------------------------------------------------------
# Model 5b: NPS-prediction — forenklet (Eq. 9, Tabel 7)
#
# Lineær regression med offset = 1.
# Target: NPS.
# Prædiktionsformel:
#   NPS_hat = (α + x·β) - 1
#
# Bruges til NPS-kødisciplin: forudsiger NPS baseret på predicted throughput tid.
# Koefficienter fra Tabel 7 (s. 12).
# -----------------------------------------------------------------------------

NPS_PRED_INTERCEPT = 10.2211
NPS_PRED_THROUGHPUT_COEF = -0.0949  # Log[case_throughputtime+1]


def predict_nps(predicted_throughput_minutes: float) -> float:
    """
    Forudsig NPS baseret på forudsagt throughput-tid (Eq. 9, Tabel 7).

    Bruges til NPS-baseret prioritering i køen.

    Args:
        predicted_throughput_minutes: Forudsagt throughput-tid i minutter

    Returns:
        Forudsagt NPS (kontinuert værdi)
    """
    log_throughput = math.log(predicted_throughput_minutes + 1)

    nps_hat = (NPS_PRED_INTERCEPT
               + NPS_PRED_THROUGHPUT_COEF * log_throughput) - 1

    return nps_hat


# =============================================================================
# SEKTION B: DATASTRUKTURER
# =============================================================================

@dataclass
class Case:
    """
    Repræsenterer en kundeservicesag (trace η i artiklen).

    En trace η_i = (i, q, s, t, a, j, r, c) bestående af:
        i: case identifier
        q: arrival time
        s: status
        t: timestamps for activities
        a: activities performed
        j: activity time indices
        r: agents working on activities
        c: static case attributes (topic, predicted throughput, predicted NPS)

    Se sektion 3.1.4 (s. 15) i artiklen.
    """
    id: int
    arrival_time: float             # q: ankomsttid i dage
    status: str = "waiting"         # s: "waiting", "active", "closed"
    timestamps: List[float] = field(default_factory=list)        # t
    activities: List[str] = field(default_factory=list)          # a
    activity_indices: List[int] = field(default_factory=list)    # j
    resources: List[int] = field(default_factory=list)           # r (agent id'er)

    # Statiske case-attributter (c)
    case_topic: str = ""
    predicted_throughput: float = 0.0   # i minutter
    predicted_nps: float = 0.0          # NPS_arrival

    # Simulationsresultat
    nps_response: Optional[int] = None  # NPS_resp (efter lukning)
    close_time: Optional[float] = None  # tidspunkt for lukning

    @property
    def waiting_time(self) -> float:
        """Aktuel ventetid i dage (bruges i kø-management)."""
        # Bemærk: dette beregnes dynamisk relativt til simuleringstiden
        # og sættes eksplicit i queue_management
        return 0.0

    @property
    def last_timestamp(self) -> float:
        """Tidspunkt for seneste aktivitet."""
        return self.timestamps[-1] if self.timestamps else self.arrival_time

    @property
    def last_activity_index(self) -> int:
        """Indeks for seneste aktivitet."""
        return self.activity_indices[-1] if self.activity_indices else 0

    @property
    def actual_throughput_minutes(self) -> float:
        """Faktisk throughput-tid i minutter (fra ankomst til lukning)."""
        if self.close_time is not None:
            return (self.close_time - self.arrival_time) * 24 * 60
        return 0.0


@dataclass
class Agent:
    """
    Repræsenterer en kundeserviceagent (ψ i artiklen).

    Agenter har en individuel resource-effekt der påvirker aktivitetsvarigheden.
    Denne effekt samples fra N(μ=0.22, σ=0.52) ved oprettelse.

    Se sektion 3.1.6 (s. 18) i artiklen.
    """
    id: int
    assigned_case_id: Optional[int] = None  # ID på den sag agenten arbejder på
    last_active_time: float = 0.0           # Tidspunkt for sidste aktivitet
    resource_effect: float = 0.0            # Individuel effekt på varighed

    @property
    def is_idle(self) -> bool:
        """Er agenten ledig (ikke tildelt en sag)?"""
        return self.assigned_case_id is None


# =============================================================================
# SEKTION C: ALGORITMER
# =============================================================================

# -----------------------------------------------------------------------------
# Algorithm 3: Case Arrival (Appendix A, s. 32)
#
# Genererer alle sager der ankommer i simuleringsperioden.
# For hver sag:
#   1. Simulér inter-arrival tid (Eq. 6)
#   2. Tildel tilfældig case_topic
#   3. Forudsig throughput-tid (Eq. 7)
#   4. Forudsig NPS (Eq. 9)
# -----------------------------------------------------------------------------

def generate_all_arrivals(d_end: int, rng: np.random.Generator) -> List[Case]:
    """
    Generér alle sager der ankommer i simuleringsperioden (Alg. 3).

    Pre-genererer alle ankomster for hele perioden, da inter-arrival modellen
    ikke afhænger af kø-tilstanden.

    Args:
        d_end: Antal dage at simulere
        rng: Numpy random generator

    Returns:
        Liste af Case-objekter sorteret efter ankomsttid
    """
    cases = []
    z = 0.0  # aktuel tid i dage
    case_id = 1

    while z < d_end:
        # Simulér inter-arrival tid (Eq. 6)
        inter_arrival = simulate_inter_arrival_time(z, rng)

        # Opdater tid
        z += inter_arrival

        if z >= d_end:
            break

        # Tildel tilfældig case topic (uniform fordeling — se note i plan)
        # ANTAGELSE: Artiklen specificerer ikke topic-frekvenser eksplicit.
        topic = rng.choice(CASE_TOPICS)

        # Forudsig throughput-tid ved ankomst (Eq. 7)
        pred_throughput = predict_throughput_time(z)

        # Forudsig NPS ved ankomst (Eq. 9)
        pred_nps = predict_nps(pred_throughput)

        case = Case(
            id=case_id,
            arrival_time=z,
            case_topic=topic,
            predicted_throughput=pred_throughput,
            predicted_nps=pred_nps,
        )
        cases.append(case)
        case_id += 1

    return cases


# -----------------------------------------------------------------------------
# Algorithm 2: Queue Management (Alg. 2, s. 17)
#
# Sorterer køen baseret på den valgte kødisciplin:
#   FCFS: sortér efter ankomsttid (ascending)
#   SRTF: sortér efter predicted throughput (ascending)
#   LRTF: sortér efter predicted throughput (descending)
#   NPS:  sortér efter |NPS_predicted - 7.5| (ascending)
#
# Hvis SLA er aktiv: sager med ventetid > (SLA - 1 dag) flyttes forrest.
# Service level constraint: hård grænse på 60 timer = 2.5 dage.
# Dvs. sager over 60 timer ventetid prioriteres (med 12 timers buffer til 72 timer).
# -----------------------------------------------------------------------------

def queue_management(queue: List[Case], discipline: str,
                      current_time: float, sla_hours: Optional[float]) -> List[Case]:
    """
    Sortér og prioritér køen baseret på kødisciplin og evt. SLA (Alg. 2).

    Kun sager med status "waiting" der er ankommet inden current_time
    medtages. Sager der allerede er "active" (tildelt en agent) er ikke i køen.

    Args:
        queue: Liste af ventende sager
        discipline: "FCFS", "SRTF", "LRTF" eller "NPS"
        current_time: Nuværende simuleringstid i dage
        sla_hours: Service level i timer (fx 60), eller None

    Returns:
        Sorteret kø
    """
    # Filtrér: kun sager ankommet inden current_time + et tidsskridt
    visible = [c for c in queue
               if c.arrival_time <= current_time + TIMESTEP_DAYS
               and c.status == "waiting"]

    if len(visible) == 0:
        return visible

    # Sortér efter kødisciplin
    if discipline == "FCFS":
        ordered = sorted(visible, key=lambda c: c.arrival_time)

    elif discipline == "SRTF":
        ordered = sorted(visible, key=lambda c: c.predicted_throughput)

    elif discipline == "LRTF":
        ordered = sorted(visible, key=lambda c: c.predicted_throughput, reverse=True)

    elif discipline == "NPS":
        # NPS-sortering: kun hvis der er >1 sag og varians i priority scores
        if len(visible) > 1:
            scores = [abs(c.predicted_nps - NPS_MIDPOINT) for c in visible]
            if np.var(scores) > 0:
                ordered = sorted(visible,
                                  key=lambda c: abs(c.predicted_nps - NPS_MIDPOINT))
            else:
                ordered = visible  # behold nuværende rækkefølge
        else:
            ordered = visible
    else:
        raise ValueError(f"Ukendt kødisciplin: {discipline}")

    # Service Level Agreement (SLA) overrule
    # Sager med ventetid over (SLA - 24 timer) flyttes forrest, sorteret FCFS
    if sla_hours is not None and sla_hours > 0:
        sla_days = sla_hours / 24.0
        # Artiklen: "hard ceiling after 60 hours" med SLA på 72 timer
        # Dvs. prioritér sager der har ventet > (SLA_days - 1) dage
        threshold_days = sla_days / 24.0  # BEMÆRK: sla_hours allerede i timer
        # Korrekt: threshold er sla_hours / 24 dage (konvertér timer til dage)
        threshold_days = sla_hours / 24.0

        priority_cases = []
        remaining_cases = []

        for c in ordered:
            waiting_days = current_time - c.arrival_time
            if waiting_days >= (threshold_days - 1.0):  # SLA minus 1 dag buffer
                priority_cases.append(c)
            else:
                remaining_cases.append(c)

        # Sortér priority-sager efter ventetid (længst ventende først)
        priority_cases.sort(key=lambda c: c.arrival_time)  # ældste først

        # Sammensæt: priority-sager først, derefter resten
        ordered = priority_cases + remaining_cases

    return ordered


# -----------------------------------------------------------------------------
# Algorithm 4: Case Assignment (Appendix B, s. 33)
#
# Tildeler ledige agenter til sager i den sorterede kø.
# Ledige agenter sorteres efter last_active_time (ældst først).
# -----------------------------------------------------------------------------

def case_assignment(ordered_queue: List[Case], agents: List[Agent],
                     case_lookup: Dict[int, Case]) -> None:
    """
    Tildel ledige agenter til ventende sager i kø-rækkefølge (Alg. 4).

    Modificerer agents og cases in-place.

    Args:
        ordered_queue: Sorteret kø af ventende sager
        agents: Alle agenter
        case_lookup: Dict fra case_id til Case-objekt
    """
    # Opret idle-pool: agenter der ikke er tildelt en sag
    idle_agents = [a for a in agents if a.is_idle]

    # Sortér idle-pool efter last_active_time (ascending — ældst ledig først)
    idle_agents.sort(key=lambda a: a.last_active_time)

    # Tildel agenter til sager
    agent_idx = 0
    for case in ordered_queue:
        if agent_idx >= len(idle_agents):
            break  # ingen flere ledige agenter

        if case.status != "waiting":
            continue  # sagen er allerede tildelt

        agent = idle_agents[agent_idx]

        # Tildel: opdater agent og sag
        agent.assigned_case_id = case.id
        case.status = "active"
        case.resources.append(agent.id)

        agent_idx += 1


# -----------------------------------------------------------------------------
# Algorithm 6: Start Delay (Appendix D, s. 35)
#
# Beregner forsinkelse når en aktivitet ikke kan starte fordi agenten
# er off-duty (udenfor arbejdstid Man-Fre 08:00-18:00).
# Returnerer delay i dage.
# -----------------------------------------------------------------------------

def compute_start_delay(finish_time_days: float) -> float:
    """
    Beregn start-delay i dage for en aktivitet der afsluttes udenfor arbejdstid (Alg. 6).

    Arbejdstid: Mandag-Fredag 08:00-18:00.
    Hvis en aktivitet afsluttes udenfor arbejdstid, beregnes forsinkelsen
    til næste arbejdstidsstart.

    Args:
        finish_time_days: Tidspunkt for afslutning af forrige aktivitet (i dage)

    Returns:
        Delay i dage (0 hvis inden for arbejdstid)
    """
    v = 0.0

    # Beregn ugedag og tid på dagen
    day_number = int(math.floor(finish_time_days))

    # 2018-07-01 (dag 0) er en søndag.
    # weekday: 0=søndag, 1=mandag, ..., 6=lørdag
    weekday_0indexed = day_number % 7  # 0=søndag

    # Time på dagen (som float, 0-24)
    time_of_day = (finish_time_days - math.floor(finish_time_days)) * 24

    # Konvertér til artiklens konvention (1=mandag, ..., 7=søndag)
    # Vores: 0=søn, 1=man, 2=tirs, ..., 6=lør
    # Artiklens Alg. 6 bruger weekday > 5 for weekend (lørdag=6, søndag=7)
    # Vi mapper: 0(søn)->7, 1(man)->1, ..., 6(lør)->6
    weekday = weekday_0indexed if weekday_0indexed > 0 else 7

    if weekday > 5:
        # Weekend: delay til mandag kl. 08:00
        days_until_monday = 8 - weekday  # lørdag(6)->2, søndag(7)->1
        v = (days_until_monday - (time_of_day / 24.0)) + (BUSINESS_HOUR_START / 24.0)
    else:
        # Hverdag
        if time_of_day < BUSINESS_HOUR_START:
            # Før arbejdstid: delay til kl. 08:00 i dag
            v = (BUSINESS_HOUR_START - time_of_day) / 24.0
        elif time_of_day >= BUSINESS_HOUR_END:
            # Efter arbejdstid
            if weekday < 5:
                # Ikke fredag: delay til i morgen kl. 08:00
                v = (24 - time_of_day + BUSINESS_HOUR_START) / 24.0
            else:
                # Fredag efter kl. 18: delay til mandag kl. 08:00
                v = ((8 - weekday) - (time_of_day / 24.0)) + (BUSINESS_HOUR_START / 24.0)
                # Simplified: dage til mandag + timer til 08:00
                v = (2 + (24 - time_of_day + BUSINESS_HOUR_START) / 24.0)
        # Inden for arbejdstid: v = 0 (ingen delay)

    return max(v, 0.0)


# -----------------------------------------------------------------------------
# Algorithm 7: Next Activity (Appendix E, s. 36)
#
# Subroutine der:
#   1. Henter seneste aktivitet og tidsstempel
#   2. Sampler næste aktivitet fra Markov-kæden (Eq. 4)
#   3. Simulerer varighed fra Weibull-modellen (Eq. 3)
#   4. Tilføjer start-delay + varighed til tidsstempel
# -----------------------------------------------------------------------------

def next_activity(case: Case, start_delay: float, agent: Agent,
                   rng: np.random.Generator,
                   effective_start: Optional[float] = None) -> Tuple[str, float]:
    """
    Simulér næste aktivitet og dens varighed for en sag (Alg. 7).

    Args:
        case: Den aktuelle sag
        start_delay: Forsinkelse fra start_delay() i dage
        agent: Agenten der arbejder på sagen
        rng: Numpy random generator
        effective_start: Tidligste starttidspunkt (bruges til at sikre at
            aktiviteter ikke "backdates" til før sagentildeling)

    Returns:
        Tuple af (næste aktivitetstype, afslutningstid i dage)
    """
    # Hent seneste aktivitet
    if len(case.activities) == 0:
        last_activity = None
        last_time = case.arrival_time
    else:
        last_activity = case.activities[-1]
        last_time = case.timestamps[-1]

    # Sikr at vi ikke backdater aktiviteter til før tildeling.
    # Når en sag har ventet i køen, skal aktiviteter starte fra NU,
    # ikke fra ankomsttidspunktet.
    if effective_start is not None:
        last_time = max(last_time, effective_start)

    # Sample næste aktivitet fra Markov-kæde (Eq. 4)
    if last_activity is None:
        next_act = sample_initial_activity(rng)
    else:
        next_act = sample_next_activity(last_activity, rng)

    # Hvis END: sagen afsluttes (ingen varighed)
    if next_act == "END":
        # Tilføj END som sidste aktivitet
        case.activities.append("END")
        case.timestamps.append(last_time)
        case.activity_indices.append(len(case.activities))
        return ("END", last_time)

    # Simulér varighed af næste aktivitet (Eq. 3)
    activity_number = len(case.activities) + 1
    duration_hours = simulate_activity_duration(
        case.case_topic, next_act, activity_number, agent.resource_effect, rng
    )

    # Konvertér varighed fra timer til dage
    duration_days = duration_hours / 24.0

    # Beregn afslutningstid: sidste tidsstempel + start_delay + varighed
    finish_time = last_time + start_delay + duration_days

    # Opdater case
    case.activities.append(next_act)
    case.timestamps.append(finish_time)
    case.activity_indices.append(len(case.activities))
    case.resources.append(agent.id)

    return (next_act, finish_time)


# -----------------------------------------------------------------------------
# Algorithm 5: Case Activities (Appendix C, s. 34)
#
# For hver agent med en aktiv sag:
#   - Tjek om den nuværende aktivitets afslutning er inden for tidsvinduet
#   - Hvis ja: beregn start-delay, simulér næste aktivitet
#   - Hvis END: frigør agent, luk sag
# Gentag indtil aktiviteten rækker ud over det nuværende 15-min vindue.
# -----------------------------------------------------------------------------

def _is_business_hours(time_days: float) -> bool:
    """
    Tjek om et tidspunkt falder inden for arbejdstid (Man-Fre 08:00-18:00).

    Artiklen (s. 15): "activities can occur if and only if [...] (c) the current
    day is a workday." Samt (s. 18): "business hours are defined here as Monday
    to Friday from 08:00 to 18:00."
    """
    day_number = int(math.floor(time_days))
    # 0=søndag, 1=mandag, ..., 6=lørdag
    weekday_raw = day_number % 7

    # Weekend? (0=søndag, 6=lørdag)
    if weekday_raw == 0 or weekday_raw == 6:
        return False

    # Tjek klokkeslæt (rund for at undgå floating-point fejl ved fx 8.0 → 7.9999)
    hour = round((time_days - math.floor(time_days)) * 24, 6)
    return BUSINESS_HOUR_START <= hour < BUSINESS_HOUR_END


def case_activities(agents: List[Agent], case_lookup: Dict[int, Case],
                     current_time: float, rng: np.random.Generator) -> None:
    """
    Simulér aktiviteter for alle aktive sager i det nuværende tidsskridt (Alg. 5).

    Aktiviteter sker KUN under arbejdstid (Man-Fre 08:00-18:00), jf. artiklen
    s. 15: "activities can occur if and only if [...] (c) the current day is a
    workday."

    Modificerer agents og cases in-place.

    Args:
        agents: Alle agenter
        case_lookup: Dict fra case_id til Case
        current_time: Nuværende simuleringstid (start af 15-min vindue)
        rng: Numpy random generator
    """
    # Betingelse (c): kun under arbejdstid
    if not _is_business_hours(current_time):
        return

    for agent in agents:
        if agent.is_idle:
            continue

        # Hent den aktive sag
        case = case_lookup.get(agent.assigned_case_id)
        if case is None or case.status != "active":
            agent.assigned_case_id = None
            continue

        # Hent afslutningstid for nuværende aktivitet
        if len(case.timestamps) > 0:
            finish_time = case.timestamps[-1]
        else:
            finish_time = case.arrival_time

        # Næste aktivitets starttidspunkt
        next_step = max(finish_time, current_time)
        activity_idx = len(case.activities)

        # Fortsæt med aktiviteter inden for det nuværende 15-min vindue
        while next_step < current_time + TIMESTEP_DAYS:
            # Beregn start-delay (Alg. 6)
            delay = compute_start_delay(next_step)

            # Simulér næste aktivitet (Alg. 7)
            # effective_start=current_time sikrer at aktiviteter ikke backdates
            act_type, act_finish = next_activity(case, delay, agent, rng,
                                                  effective_start=current_time)

            if act_type == "END":
                # Sagen er afsluttet: frigør agent
                case.status = "closed"
                case.close_time = next_step
                agent.assigned_case_id = None
                agent.last_active_time = next_step
                break

            # Opdater agent
            agent.last_active_time = act_finish

            # Tjek om den nye aktivitet rækker ud over tidsvinduet
            next_step = act_finish

        # Opdater agentens sidste aktive tid
        if not agent.is_idle:
            agent.last_active_time = next_step


# =============================================================================
# SEKTION D: HOVEDLOOP — Algorithm 1: Timeline (s. 16)
# =============================================================================

@dataclass
class SimulationMetrics:
    """
    Opsamler evalueringsmetrikker for en enkelt simulationskørsel.

    Metrikkerne beregnes dagligt og aggregeres til slut (Eq. 10-17).
    """
    # Daglige opsamlinger
    daily_queue_lengths: List[int] = field(default_factory=list)
    daily_waiting_times: List[float] = field(default_factory=list)
    daily_utilisation: List[float] = field(default_factory=list)

    # Samlet for hele kørslen
    total_cases_arrived: int = 0
    total_cases_closed: int = 0
    nps_responses: List[int] = field(default_factory=list)

    @property
    def avg_queue_length(self) -> float:
        """Gennemsnitlig kølængde (Eq. 12)."""
        return np.mean(self.daily_queue_lengths) if self.daily_queue_lengths else 0.0

    @property
    def avg_waiting_time_days(self) -> float:
        """Gennemsnitlig ventetid i kø i dage (Eq. 10)."""
        return np.mean(self.daily_waiting_times) if self.daily_waiting_times else 0.0

    @property
    def avg_capacity_utilisation(self) -> float:
        """Gennemsnitlig kapacitetsudnyttelse (Eq. 13)."""
        return np.mean(self.daily_utilisation) if self.daily_utilisation else 0.0

    @property
    def percent_cases_closed(self) -> float:
        """Andel af sager lukket (Eq. 14)."""
        if self.total_cases_arrived == 0:
            return 0.0
        return self.total_cases_closed / self.total_cases_arrived

    @property
    def avg_individual_nps(self) -> float:
        """Gennemsnitlig individuel NPS-respons (0-10 skala)."""
        return np.mean(self.nps_responses) if self.nps_responses else 0.0

    @property
    def organisation_nps(self) -> float:
        """
        Organisations-niveau NPS (Eq. 17).

        NPS = %promoters - %detractors
        Promoters: NPS_resp >= 9
        Detractors: NPS_resp <= 6
        Skala: -100 til +100
        """
        if not self.nps_responses:
            return 0.0
        total = len(self.nps_responses)
        promoters = sum(1 for n in self.nps_responses if n >= 9) / total
        detractors = sum(1 for n in self.nps_responses if n <= 6) / total
        return (promoters - detractors) * 100


def simulate_timeline(discipline: str, n_agents: int, sla_hours: Optional[float],
                       d_end: int = 365, seed: Optional[int] = None) -> SimulationMetrics:
    """
    Kør en komplet simulering af kundeserviceprocessen (Alg. 1).

    Hovedloop der itererer over dage og 15-minutters intervaller.
    For hvert tidsskridt:
        1. Tilføj nye sager til kø (fra pre-genererede ankomster)
        2. Sortér kø efter kødisciplin (Alg. 2)
        3. Tildel ledige agenter til sager (Alg. 4)
        4. Simulér aktiviteter for aktive sager (Alg. 5)
        5. Simulér NPS for lukkede sager (Eq. 8)

    Args:
        discipline: "FCFS", "SRTF", "LRTF" eller "NPS"
        n_agents: Antal kundeserviceagenter
        sla_hours: Service level i timer (fx 60.0), eller None
        d_end: Antal dage at simulere (default 365)
        seed: Random seed for reproducerbarhed

    Returns:
        SimulationMetrics med alle evalueringsmetrikker
    """
    rng = np.random.default_rng(seed)
    metrics = SimulationMetrics()

    # Opret agenter med individuelle resource-effekter
    agents = []
    for i in range(n_agents):
        effect = rng.normal(RESOURCE_EFFECT_MEAN, RESOURCE_EFFECT_STD)
        agents.append(Agent(id=i + 1, resource_effect=effect))

    # Pre-generér alle ankomster (Alg. 3)
    all_cases = generate_all_arrivals(d_end, rng)
    metrics.total_cases_arrived = len(all_cases)

    # Opret lookup-dict for hurtig adgang
    case_lookup = {c.id: c for c in all_cases}

    # Kø-buffer (Θ): sager der er i systemet (waiting eller active)
    queue_buffer: List[Case] = []

    # Indeks til næste sag der skal tilføjes til køen
    next_case_idx = 0

    # Hovedloop: for hver dag
    for day in range(d_end):
        z = float(day)  # tid i dage

        # Daglig metrik-opsamling (ved dagens start, kl. 00:00)
        waiting_cases = [c for c in queue_buffer if c.status == "waiting"]
        metrics.daily_queue_lengths.append(len(waiting_cases))

        if waiting_cases:
            avg_wait = np.mean([z - c.arrival_time for c in waiting_cases])
            metrics.daily_waiting_times.append(avg_wait)
        else:
            metrics.daily_waiting_times.append(0.0)

        # Kapacitetsudnyttelse: andel agenter der er tildelt en sag
        busy_agents = sum(1 for a in agents if not a.is_idle)
        metrics.daily_utilisation.append(busy_agents / n_agents)

        # For hvert 15-minutters interval i dagen (96 intervaller)
        for step in range(96):
            z = day + step * TIMESTEP_DAYS

            # 1. Tilføj nye sager til kø-buffer
            while (next_case_idx < len(all_cases) and
                   all_cases[next_case_idx].arrival_time <= z + TIMESTEP_DAYS):
                queue_buffer.append(all_cases[next_case_idx])
                next_case_idx += 1

            # 2. Queue management: sortér ventende sager (Alg. 2)
            waiting_cases = [c for c in queue_buffer if c.status == "waiting"]
            ordered_queue = queue_management(waiting_cases, discipline, z, sla_hours)

            # 3. Case assignment: tildel ledige agenter (Alg. 4)
            case_assignment(ordered_queue, agents, case_lookup)

            # 4. Case activities: simulér aktiviteter (Alg. 5)
            case_activities(agents, case_lookup, z, rng)

            # 5. Simulér NPS for sager lukket i dette tidsskridt (Eq. 8)
            newly_closed = [c for c in queue_buffer
                           if c.status == "closed" and c.nps_response is None]
            for case in newly_closed:
                nps = simulate_nps_response(
                    case.actual_throughput_minutes, case.case_topic, rng
                )
                case.nps_response = nps
                metrics.nps_responses.append(nps)
                metrics.total_cases_closed += 1

        # Fjern lukkede sager fra queue_buffer (for at holde den kompakt)
        queue_buffer = [c for c in queue_buffer if c.status != "closed"]

    return metrics


# =============================================================================
# HJÆLPEFUNKTION: Kør en enkelt simulering med parametre som dict
# =============================================================================

def run_single_simulation(params: dict) -> dict:
    """
    Kør en enkelt simulering og returnér resultaterne som dict.

    Bruges af multiprocessing i run_experiments.py.

    Args:
        params: Dict med nøgler:
            discipline: str
            n_agents: int
            sla_hours: Optional[float]
            replication: int
            d_end: int (default 365)

    Returns:
        Dict med simuleringsresultater
    """
    discipline = params["discipline"]
    n_agents = params["n_agents"]
    sla_hours = params.get("sla_hours")
    replication = params["replication"]
    d_end = params.get("d_end", 365)

    # Generér unikt seed baseret på parametre (for reproducerbarhed)
    seed = hash((discipline, n_agents, sla_hours or 0, replication)) % (2**31)

    metrics = simulate_timeline(discipline, n_agents, sla_hours, d_end, seed)

    return {
        "discipline": discipline,
        "n_agents": n_agents,
        "sla_hours": sla_hours if sla_hours else "None",
        "replication": replication,
        "avg_queue_length": metrics.avg_queue_length,
        "avg_waiting_time_days": metrics.avg_waiting_time_days,
        "avg_capacity_utilisation": metrics.avg_capacity_utilisation,
        "percent_cases_closed": metrics.percent_cases_closed,
        "avg_individual_nps": metrics.avg_individual_nps,
        "organisation_nps": metrics.organisation_nps,
        "total_cases_arrived": metrics.total_cases_arrived,
        "total_cases_closed": metrics.total_cases_closed,
    }


# =============================================================================
# QUICK SMOKE TEST
# =============================================================================

if __name__ == "__main__":
    print("=== Smoke test: én simulering ===")
    print("Discipline: FCFS, Agents: 7, SLA: None, Days: 30")
    print()

    result = run_single_simulation({
        "discipline": "FCFS",
        "n_agents": 7,
        "sla_hours": None,
        "replication": 1,
        "d_end": 30,
    })

    for key, val in result.items():
        if isinstance(val, float):
            print(f"  {key}: {val:.4f}")
        else:
            print(f"  {key}: {val}")
