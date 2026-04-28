"""
Study 3c — Multi-Predictor NPS Model.

Fork af study3b/simulation.py. Ændringer i forhold til Study 3b:
    8. predict_nps_study3 accepterer topic_aware (bool) og case_topic.
       Når topic_aware=True, lægges NPS_PRED_TOPIC_COEFS[topic] til den
       lineære prædiktor. Det bryder den monotone afhængighed af
       predicted_throughput og giver |NPS_hat − 7.5| en anden rangorden
       end LRTF allerede ved baseline-intercept (10.22).

Hypothese (H1, jf. study3c.md):
    Når NPS-prædiktionen er topic-bevidst, divergerer NPS-prioritering
    fra LRTF allerede ved nps_intercept = 10.22. Effekten vokser monotont
    med ρ.

Alle øvrige Study 3 / 3b-mekanikker (latent Z, hard/soft mode, paret
seeding, variabelt NPS-intercept) er bibeholdt uændret.
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

# =============================================================================
# KONSTANTER (arvet fra Study 2 — uændret)
# =============================================================================

TIMESTEP_DAYS = 15 / (24 * 60)
BUSINESS_HOUR_START = 8
BUSINESS_HOUR_END = 18
SIM_START_YEAR = 2018
SIM_START_MONTH = 7
SIM_START_DAY = 1
NPS_MIDPOINT = 7.5

CASE_TOPICS = [
    "d_2-z_4", "g_1-z_4", "j_1-z_4", "q_3-z_4", "r_2-z_4",
    "w_1-z_4", "w_2-z_4", "z_2-z_4", "z_3-z_4", "z_4"
]
ACTIVITY_TYPES = ["Task-Reminder", "Interaction", "Email"]
ACTIVITY_STATES = ACTIVITY_TYPES + ["END"]


# =============================================================================
# MODEL-KOEFFICIENTER (arvet fra Study 2 — uændret)
# =============================================================================

# Activity duration (Eq. 3, Tabel 1)
DURATION_INTERCEPT = 1.6645
DURATION_THETA = 0.3908

DURATION_TOPIC_COEFS = {
    "d_2-z_4": 0.0200, "g_1-z_4": -0.0538, "j_1-z_4": -0.0557,
    "q_3-z_4": 0.1712, "r_2-z_4": 0.0836, "w_1-z_4": -0.0609,
    "w_2-z_4": 0.0119, "z_2-z_4": -0.0420, "z_3-z_4": 0.1637,
    "z_4": 0.0,
}
DURATION_ACTIVITY_COEFS = {
    "Task-Reminder": 0.0180, "Interaction": 0.1057, "Email": 0.0,
}
DURATION_ACTIVITY_NUMBER_COEF = 0.0420
RESOURCE_EFFECT_MEAN = 0.2171
RESOURCE_EFFECT_STD = 0.52

# Absorbing Markov chain (Eq. 4, Tabel 2-3)
TRANSITION_MATRIX = np.array([
    [0.08, 0.00, 0.67, 0.25],
    [0.00, 0.02, 0.96, 0.02],
    [0.00, 0.02, 0.45, 0.53],
    [0.00, 0.00, 0.00, 1.00],
])
INITIAL_PROBS = np.array([0.0, 0.92, 0.08, 0.0])

# Inter-arrival model (Eq. 6, Tabel 4) — med kalibreret intercept fra Study 2
ARRIVAL_INTERCEPT = 726.2
ARRIVAL_COEFS = {
    "year": -0.3589,
    "month": -0.0881,
    "day": 0.0078,
    "weekday": 0.2616,
}

# NPS simulation model (Eq. 8, Tabel 6) — bruges til den "sande" NPS-respons
NPS_SIM_INTERCEPT = 2.3006
NPS_SIM_RHO = 1.3005
NPS_SIM_THROUGHPUT_COEF = -0.0098
NPS_SIM_TOPIC_COEFS = {
    "d_2-z_4": -0.1291, "g_1-z_4": 0.1008, "j_1-z_4": 0.0853,
    "q_3-z_4": -0.0427, "r_2-z_4": -0.0317, "w_1-z_4": 0.0000,
    "w_2-z_4": 0.0000, "z_2-z_4": 0.0967, "z_3-z_4": -0.0048,
    "z_4": 0.0,
}

# NPS prediction model (Eq. 9, Tabel 7) — original Study 2 koefficient
NPS_PRED_INTERCEPT = 10.2211
NPS_PRED_THROUGHPUT_COEF = -0.0949

# Study 3c: NPS-prædiktionsmodellen suppleres med topic-koefficienter
# når topic_aware=True. Vi bruger de "sande" topic-effekter fra Eq. 8 som
# baseline (perfekt topic-information).
NPS_PRED_TOPIC_COEFS = dict(NPS_SIM_TOPIC_COEFS)


# =============================================================================
# STUDY 3-SPECIFIKKE KONSTANTER
# =============================================================================

CALIBRATION_FILE = Path(__file__).parent / "results" / "calibration.json"


def _load_calibration() -> Dict[str, float]:
    """Indlæs kalibrerede parametre fra calibration.json, eller returnér defaults."""
    defaults = {
        "scaling_factor": 1.0,
        "beta_z": 0.0,
        "baseline_var": None,
        "new_var": None,
    }
    if CALIBRATION_FILE.exists():
        try:
            with open(CALIBRATION_FILE) as f:
                loaded = json.load(f)
            defaults.update(loaded)
        except Exception as e:
            print(f"Warning: kunne ikke indlæse {CALIBRATION_FILE}: {e}")
    return defaults


_calibration = _load_calibration()
CALIBRATED_SCALING_FACTOR: float = _calibration["scaling_factor"]
BETA_Z: float = _calibration["beta_z"]

NPS_PRED_COEF_STUDY3 = NPS_PRED_THROUGHPUT_COEF * CALIBRATED_SCALING_FACTOR

_U_CLIP = 1.0 - 1e-9


# =============================================================================
# MODEL-FUNKTIONER
# =============================================================================

def simulate_activity_duration(case_topic: str, activity_type: str,
                                activity_number: int, resource_effect: float,
                                rng: np.random.Generator,
                                u_fixed: Optional[float] = None,
                                z_feature: float = 0.0) -> float:
    """Identisk med Study 3b — uændret."""
    linear_pred = (DURATION_INTERCEPT
                   + DURATION_TOPIC_COEFS.get(case_topic, 0.0)
                   + DURATION_ACTIVITY_COEFS.get(activity_type, 0.0)
                   + DURATION_ACTIVITY_NUMBER_COEF * activity_number
                   + resource_effect
                   + BETA_Z * z_feature)

    scale = math.exp(linear_pred)
    shape = 1.0 / DURATION_THETA

    if u_fixed is not None:
        u = min(max(u_fixed, 1e-9), _U_CLIP)
        duration_hours = scale * (-math.log(1.0 - u)) ** DURATION_THETA
    else:
        duration_hours = scale * rng.weibull(shape)

    return duration_hours


def sample_initial_activity(rng: np.random.Generator) -> str:
    idx = rng.choice(len(ACTIVITY_STATES), p=INITIAL_PROBS)
    return ACTIVITY_STATES[idx]


def sample_next_activity(current_activity: str, rng: np.random.Generator) -> str:
    current_idx = ACTIVITY_STATES.index(current_activity)
    probs = TRANSITION_MATRIX[current_idx]
    next_idx = rng.choice(len(ACTIVITY_STATES), p=probs)
    return ACTIVITY_STATES[next_idx]


def simulate_inter_arrival_time(current_time_days: float,
                                 rng: np.random.Generator) -> float:
    day_number = int(math.floor(current_time_days))
    total_day_of_year = 182 + day_number
    year = SIM_START_YEAR + total_day_of_year // 365
    day_in_year = total_day_of_year % 365
    month = _day_to_month(day_in_year)
    day_of_month = _day_to_day_of_month(day_in_year, month)

    raw_weekday = day_number % 7
    weekday = (raw_weekday - 1) % 7

    linear_pred = (ARRIVAL_INTERCEPT
                   + ARRIVAL_COEFS["year"] * year
                   + ARRIVAL_COEFS["month"] * month
                   + ARRIVAL_COEFS["day"] * day_of_month
                   + ARRIVAL_COEFS["weekday"] * weekday)

    u = rng.uniform(0, 1)
    inter_arrival_hours = -math.log(1 - u) * math.exp(linear_pred)
    return inter_arrival_hours / 24.0


def _day_to_month(day_of_year: int) -> int:
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]
    day_of_year = day_of_year % 365
    for m in range(12):
        if day_of_year < cum_days[m + 1]:
            return m + 1
    return 12


def _day_to_day_of_month(day_of_year: int, month: int) -> int:
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    day_of_year = day_of_year % 365
    return day_of_year - cum_days[month - 1] + 1


def predict_throughput_from_z(z_pred: float) -> float:
    u_pred = norm.cdf(z_pred)
    u_pred = min(max(u_pred, 1e-9), _U_CLIP)

    scale_hours = math.exp(DURATION_INTERCEPT)
    predicted_hours = scale_hours * (-math.log(1.0 - u_pred)) ** DURATION_THETA

    return predicted_hours * 60.0


def predict_nps_study3(predicted_throughput_minutes: float,
                       nps_intercept: float = NPS_PRED_INTERCEPT,
                       case_topic: str = "",
                       topic_aware: bool = False) -> float:
    """
    Study 3c: forudsig NPS fra predicted throughput, valgfrit med topic-effekt.

    Når topic_aware=True, suppleres den lineære prædiktor med
    NPS_PRED_TOPIC_COEFS[case_topic]. Det bryder den monotone afhængighed
    af predicted_throughput, så |NPS_hat − 7.5| sortering ≠ LRTF sortering.

    Args:
        predicted_throughput_minutes: Forudsagt throughput i minutter
        nps_intercept: Intercept (Study 3b faktor)
        case_topic: Sagens topic (kun brugt når topic_aware=True)
        topic_aware: Om NPS-modellen tager hensyn til topic
    """
    log_throughput = math.log(predicted_throughput_minutes + 1)
    topic_term = NPS_PRED_TOPIC_COEFS.get(case_topic, 0.0) if topic_aware else 0.0
    return (nps_intercept
            + NPS_PRED_COEF_STUDY3 * log_throughput
            + topic_term) - 1


def simulate_nps_response(actual_throughput_minutes: float, case_topic: str,
                           rng: np.random.Generator) -> int:
    """Den "sande" NPS-respons (Eq. 8, Tabel 6) — uændret."""
    log_throughput = math.log(actual_throughput_minutes + 1)
    linear_pred = (NPS_SIM_INTERCEPT
                   + NPS_SIM_THROUGHPUT_COEF * log_throughput
                   + NPS_SIM_TOPIC_COEFS.get(case_topic, 0.0))
    shape = math.exp(linear_pred) / NPS_SIM_RHO
    scale = NPS_SIM_RHO
    nps_raw = rng.gamma(shape, scale) - 1
    nps_raw = max(0.0, min(nps_raw, 10.0))
    return max(0, min(math.ceil(nps_raw), 10))


# =============================================================================
# DATASTRUKTURER
# =============================================================================

@dataclass
class Case:
    id: int
    arrival_time: float
    status: str = "waiting"
    timestamps: List[float] = field(default_factory=list)
    activities: List[str] = field(default_factory=list)
    activity_indices: List[int] = field(default_factory=list)
    resources: List[int] = field(default_factory=list)

    case_topic: str = ""
    predicted_throughput: float = 0.0
    predicted_nps: float = 0.0

    z_actual: float = 0.0
    u_actual: float = 0.5
    z_pred: float = 0.0

    nps_response: Optional[int] = None
    close_time: Optional[float] = None

    @property
    def last_timestamp(self) -> float:
        return self.timestamps[-1] if self.timestamps else self.arrival_time

    @property
    def actual_throughput_minutes(self) -> float:
        if self.close_time is not None:
            return (self.close_time - self.arrival_time) * 24 * 60
        return 0.0


@dataclass
class Agent:
    id: int
    assigned_case_id: Optional[int] = None
    last_active_time: float = 0.0
    resource_effect: float = 0.0

    @property
    def is_idle(self) -> bool:
        return self.assigned_case_id is None


# =============================================================================
# ALGORITMER
# =============================================================================

def generate_all_arrivals(d_end: int,
                          rng_arrivals: np.random.Generator,
                          rng_actual: np.random.Generator,
                          rng_pred_noise: np.random.Generator,
                          rho: float,
                          nps_intercept: float = NPS_PRED_INTERCEPT,
                          topic_aware: bool = False) -> List[Case]:
    """
    Study 3c: Generér sager med latent Z, variabelt NPS-intercept og
    valgfri topic-bevidst NPS-prædiktion.

    Args:
        d_end: Simuleringsperiode i dage
        rng_arrivals: RNG for ankomsttider og case topics
        rng_actual: RNG for z_actual
        rng_pred_noise: RNG for ε i z_pred
        rho: Latent korrelation ∈ [0, 1]
        nps_intercept: Intercept i NPS-prædiktionsmodellen (Study 3b faktor)
        topic_aware: Hvis True bruger NPS-prædiktionen NPS_PRED_TOPIC_COEFS
            (Study 3c faktor)
    """
    cases: List[Case] = []
    z = 0.0
    case_id = 1
    sqrt_one_minus_rho_sq = math.sqrt(max(0.0, 1.0 - rho * rho))

    while z < d_end:
        inter_arrival = simulate_inter_arrival_time(z, rng_arrivals)
        z += inter_arrival
        if z >= d_end:
            break

        topic = rng_arrivals.choice(CASE_TOPICS)

        z_actual = float(rng_actual.normal(0.0, 1.0))
        u_actual = float(norm.cdf(z_actual))
        epsilon = float(rng_pred_noise.normal(0.0, 1.0))
        z_pred = rho * z_actual + sqrt_one_minus_rho_sq * epsilon

        pred_throughput = predict_throughput_from_z(z_pred)
        pred_nps = predict_nps_study3(
            pred_throughput,
            nps_intercept=nps_intercept,
            case_topic=topic,
            topic_aware=topic_aware,
        )

        case = Case(
            id=case_id,
            arrival_time=z,
            case_topic=topic,
            predicted_throughput=pred_throughput,
            predicted_nps=pred_nps,
            z_actual=z_actual,
            u_actual=u_actual,
            z_pred=z_pred,
        )
        cases.append(case)
        case_id += 1

    return cases


def queue_management(queue: List[Case], discipline: str,
                      current_time: float, sla_hours: Optional[float]) -> List[Case]:
    """Identisk med Study 3b."""
    visible = [c for c in queue
               if c.arrival_time <= current_time + TIMESTEP_DAYS
               and c.status == "waiting"]
    if not visible:
        return visible

    if discipline == "FCFS":
        ordered = sorted(visible, key=lambda c: c.arrival_time)
    elif discipline == "SRTF":
        ordered = sorted(visible, key=lambda c: c.predicted_throughput)
    elif discipline == "LRTF":
        ordered = sorted(visible, key=lambda c: c.predicted_throughput, reverse=True)
    elif discipline == "NPS":
        if len(visible) > 1:
            scores = [abs(c.predicted_nps - NPS_MIDPOINT) for c in visible]
            if np.var(scores) > 0:
                ordered = sorted(visible,
                                 key=lambda c: abs(c.predicted_nps - NPS_MIDPOINT))
            else:
                ordered = visible
        else:
            ordered = visible
    else:
        raise ValueError(f"Ukendt kødisciplin: {discipline}")

    if sla_hours is not None and sla_hours > 0:
        threshold_days = sla_hours / 24.0
        priority_cases = []
        remaining_cases = []
        for c in ordered:
            waiting_days = current_time - c.arrival_time
            if waiting_days >= (threshold_days - 1.0):
                priority_cases.append(c)
            else:
                remaining_cases.append(c)
        priority_cases.sort(key=lambda c: c.arrival_time)
        ordered = priority_cases + remaining_cases

    return ordered


def case_assignment(ordered_queue: List[Case], agents: List[Agent],
                     case_lookup: Dict[int, Case]) -> None:
    idle_agents = [a for a in agents if a.is_idle]
    idle_agents.sort(key=lambda a: a.last_active_time)

    agent_idx = 0
    for case in ordered_queue:
        if agent_idx >= len(idle_agents):
            break
        if case.status != "waiting":
            continue
        agent = idle_agents[agent_idx]
        agent.assigned_case_id = case.id
        case.status = "active"
        case.resources.append(agent.id)
        agent_idx += 1


def compute_start_delay(finish_time_days: float) -> float:
    v = 0.0
    day_number = int(math.floor(finish_time_days))
    weekday_0indexed = day_number % 7
    time_of_day = (finish_time_days - math.floor(finish_time_days)) * 24
    weekday = weekday_0indexed if weekday_0indexed > 0 else 7

    if weekday > 5:
        days_until_monday = 8 - weekday
        v = (days_until_monday - (time_of_day / 24.0)) + (BUSINESS_HOUR_START / 24.0)
    else:
        if time_of_day < BUSINESS_HOUR_START:
            v = (BUSINESS_HOUR_START - time_of_day) / 24.0
        elif time_of_day >= BUSINESS_HOUR_END:
            if weekday < 5:
                v = (24 - time_of_day + BUSINESS_HOUR_START) / 24.0
            else:
                v = (2 + (24 - time_of_day + BUSINESS_HOUR_START) / 24.0)
    return max(v, 0.0)


def _is_business_hours(time_days: float) -> bool:
    day_number = int(math.floor(time_days))
    weekday_raw = day_number % 7
    if weekday_raw == 0 or weekday_raw == 6:
        return False
    hour = round((time_days - math.floor(time_days)) * 24, 6)
    return BUSINESS_HOUR_START <= hour < BUSINESS_HOUR_END


def next_activity(case: Case, start_delay: float, agent: Agent,
                   rng: np.random.Generator,
                   effective_start: Optional[float] = None,
                   sampling_mode: str = "hard") -> Tuple[str, float]:
    if len(case.activities) == 0:
        last_activity = None
        last_time = case.arrival_time
    else:
        last_activity = case.activities[-1]
        last_time = case.timestamps[-1]

    if effective_start is not None:
        last_time = max(last_time, effective_start)

    if last_activity is None:
        next_act = sample_initial_activity(rng)
    else:
        next_act = sample_next_activity(last_activity, rng)

    if next_act == "END":
        case.activities.append("END")
        case.timestamps.append(last_time)
        case.activity_indices.append(len(case.activities))
        return ("END", last_time)

    activity_number = len(case.activities) + 1

    if sampling_mode == "hard":
        duration_hours = simulate_activity_duration(
            case.case_topic, next_act, activity_number, agent.resource_effect, rng,
            u_fixed=case.u_actual, z_feature=0.0
        )
    elif sampling_mode == "soft":
        duration_hours = simulate_activity_duration(
            case.case_topic, next_act, activity_number, agent.resource_effect, rng,
            u_fixed=None, z_feature=case.z_actual
        )
    else:
        raise ValueError(f"Ukendt sampling_mode: {sampling_mode}")

    duration_days = duration_hours / 24.0
    finish_time = last_time + start_delay + duration_days

    case.activities.append(next_act)
    case.timestamps.append(finish_time)
    case.activity_indices.append(len(case.activities))
    case.resources.append(agent.id)

    return (next_act, finish_time)


def case_activities(agents: List[Agent], case_lookup: Dict[int, Case],
                     current_time: float, rng: np.random.Generator,
                     sampling_mode: str = "hard") -> None:
    if not _is_business_hours(current_time):
        return

    for agent in agents:
        if agent.is_idle:
            continue

        case = case_lookup.get(agent.assigned_case_id)
        if case is None or case.status != "active":
            agent.assigned_case_id = None
            continue

        if len(case.timestamps) > 0:
            finish_time = case.timestamps[-1]
        else:
            finish_time = case.arrival_time

        next_step = max(finish_time, current_time)

        while next_step < current_time + TIMESTEP_DAYS:
            delay = compute_start_delay(next_step)
            act_type, act_finish = next_activity(
                case, delay, agent, rng,
                effective_start=current_time,
                sampling_mode=sampling_mode,
            )

            if act_type == "END":
                case.status = "closed"
                case.close_time = next_step
                agent.assigned_case_id = None
                agent.last_active_time = next_step
                break

            agent.last_active_time = act_finish
            next_step = act_finish

        if not agent.is_idle:
            agent.last_active_time = next_step


# =============================================================================
# HOVEDLOOP
# =============================================================================

@dataclass
class SimulationMetrics:
    daily_queue_lengths: List[int] = field(default_factory=list)
    daily_waiting_times: List[float] = field(default_factory=list)
    daily_utilisation: List[float] = field(default_factory=list)

    total_cases_arrived: int = 0
    total_cases_closed: int = 0
    nps_responses: List[int] = field(default_factory=list)

    closed_case_arrivals: List[float] = field(default_factory=list)
    closed_case_throughput_days: List[float] = field(default_factory=list)
    all_case_arrivals: List[float] = field(default_factory=list)

    # Study 3c diagnostik: variansen af predicted_nps
    predicted_nps_values: List[float] = field(default_factory=list)

    @property
    def avg_queue_length(self) -> float:
        return float(np.mean(self.daily_queue_lengths)) if self.daily_queue_lengths else 0.0

    @property
    def avg_waiting_time_days(self) -> float:
        return float(np.mean(self.daily_waiting_times)) if self.daily_waiting_times else 0.0

    @property
    def avg_capacity_utilisation(self) -> float:
        return float(np.mean(self.daily_utilisation)) if self.daily_utilisation else 0.0

    @property
    def percent_cases_closed(self) -> float:
        if self.total_cases_arrived == 0:
            return 0.0
        return self.total_cases_closed / self.total_cases_arrived

    @property
    def avg_individual_nps(self) -> float:
        return float(np.mean(self.nps_responses)) if self.nps_responses else 0.0

    @property
    def organisation_nps(self) -> float:
        if not self.nps_responses:
            return 0.0
        total = len(self.nps_responses)
        promoters = sum(1 for n in self.nps_responses if n >= 9) / total
        detractors = sum(1 for n in self.nps_responses if n <= 6) / total
        return (promoters - detractors) * 100

    @property
    def avg_case_resolution_time_days(self) -> float:
        return float(np.mean(self.closed_case_throughput_days)) if self.closed_case_throughput_days else 0.0

    @property
    def predicted_nps_variance(self) -> float:
        return float(np.var(self.predicted_nps_values)) if self.predicted_nps_values else 0.0

    def percent_closed_in_window(self, start_day: float) -> float:
        n_arrived = sum(1 for t in self.all_case_arrivals if t >= start_day)
        if n_arrived == 0:
            return 0.0
        n_closed = sum(1 for t in self.closed_case_arrivals if t >= start_day)
        return n_closed / n_arrived


def simulate_timeline(discipline: str, n_agents: int, sla_hours: Optional[float],
                       rho: float, sampling_mode: str,
                       d_end: int = 365,
                       seeds: Optional[Dict[str, int]] = None,
                       nps_intercept: float = NPS_PRED_INTERCEPT,
                       topic_aware: bool = False) -> SimulationMetrics:
    """
    Kør en komplet Study 3c-simulering.

    Args:
        discipline: FCFS, SRTF, LRTF eller NPS
        n_agents: Antal agenter
        sla_hours: SLA (None for ingen)
        rho: Latent korrelation mellem Z_pred og Z_actual ∈ [0, 1]
        sampling_mode: "hard" eller "soft"
        d_end: Antal dage
        seeds: Dict med keys arrivals, actual, pred_noise, simulation
        nps_intercept: NPS-prædiktionsintercept (Study 3b faktor)
        topic_aware: Om NPS-prædiktionen er topic-bevidst (Study 3c faktor)
    """
    if seeds is None:
        base = np.random.default_rng().integers(0, 2**31 - 1)
        seeds = {
            "arrivals": int(base) + 1_000_000,
            "actual": int(base) + 2_000_000,
            "pred_noise": int(base) + 3_000_000,
            "simulation": int(base) + 4_000_000,
        }

    rng_arrivals = np.random.default_rng(seeds["arrivals"])
    rng_actual = np.random.default_rng(seeds["actual"])
    rng_pred_noise = np.random.default_rng(seeds["pred_noise"])
    rng_sim = np.random.default_rng(seeds["simulation"])

    metrics = SimulationMetrics()

    agents = []
    for i in range(n_agents):
        effect = rng_sim.normal(RESOURCE_EFFECT_MEAN, RESOURCE_EFFECT_STD)
        agents.append(Agent(id=i + 1, resource_effect=effect))

    all_cases = generate_all_arrivals(
        d_end, rng_arrivals, rng_actual, rng_pred_noise, rho,
        nps_intercept=nps_intercept, topic_aware=topic_aware,
    )
    metrics.total_cases_arrived = len(all_cases)
    metrics.all_case_arrivals = [c.arrival_time for c in all_cases]
    metrics.predicted_nps_values = [c.predicted_nps for c in all_cases]

    case_lookup = {c.id: c for c in all_cases}
    queue_buffer: List[Case] = []
    next_case_idx = 0

    for day in range(d_end):
        z = float(day)

        waiting_cases = [c for c in queue_buffer if c.status == "waiting"]
        metrics.daily_queue_lengths.append(len(waiting_cases))

        if waiting_cases:
            metrics.daily_waiting_times.append(
                float(np.mean([z - c.arrival_time for c in waiting_cases]))
            )
        else:
            metrics.daily_waiting_times.append(0.0)

        busy_agents = sum(1 for a in agents if not a.is_idle)
        metrics.daily_utilisation.append(busy_agents / n_agents)

        for step in range(96):
            z = day + step * TIMESTEP_DAYS

            while (next_case_idx < len(all_cases) and
                   all_cases[next_case_idx].arrival_time <= z + TIMESTEP_DAYS):
                queue_buffer.append(all_cases[next_case_idx])
                next_case_idx += 1

            waiting_cases = [c for c in queue_buffer if c.status == "waiting"]
            ordered_queue = queue_management(waiting_cases, discipline, z, sla_hours)
            case_assignment(ordered_queue, agents, case_lookup)
            case_activities(agents, case_lookup, z, rng_sim, sampling_mode)

            newly_closed = [c for c in queue_buffer
                            if c.status == "closed" and c.nps_response is None]
            for case in newly_closed:
                nps = simulate_nps_response(
                    case.actual_throughput_minutes, case.case_topic, rng_sim
                )
                case.nps_response = nps
                metrics.nps_responses.append(nps)
                metrics.total_cases_closed += 1
                metrics.closed_case_arrivals.append(case.arrival_time)
                metrics.closed_case_throughput_days.append(
                    case.actual_throughput_minutes / (60.0 * 24.0)
                )

        queue_buffer = [c for c in queue_buffer if c.status != "closed"]

    return metrics


# =============================================================================
# HJÆLPEFUNKTION: kør en enkelt simulering med parametre som dict
# =============================================================================

def derive_seeds(replication: int, rho_idx: int) -> Dict[str, int]:
    """
    Paret seed-derivering (samme som Study 3 / 3b).

    arrivals, actual, simulation afhænger KUN af replication. pred_noise
    varierer med rho_idx. topic_aware og nps_intercept påvirker IKKE seeds —
    de er rent deterministiske transformationer af pred_throughput og topic.
    """
    base = hash(("study3", replication)) % (2**31)
    return {
        "arrivals": base + 1_000_000,
        "actual": base + 2_000_000,
        "pred_noise": base + 3_000_000 + rho_idx,
        "simulation": base + 4_000_000,
    }


def run_single_simulation(params: dict) -> dict:
    """Kør én simulering og returnér resultater som dict."""
    discipline = params["discipline"]
    n_agents = params["n_agents"]
    sla_hours = params.get("sla_hours")
    replication = params["replication"]
    rho = params["rho"]
    rho_idx = params["rho_idx"]
    sampling_mode = params["sampling_mode"]
    nps_intercept = params.get("nps_intercept", NPS_PRED_INTERCEPT)
    topic_aware = params.get("topic_aware", False)
    d_end = params.get("d_end", 365)

    seeds = derive_seeds(replication, rho_idx)
    metrics = simulate_timeline(
        discipline, n_agents, sla_hours, rho, sampling_mode, d_end, seeds,
        nps_intercept=nps_intercept,
        topic_aware=topic_aware,
    )

    return {
        "rho": rho,
        "rho_idx": rho_idx,
        "sampling_mode": sampling_mode,
        "nps_intercept": nps_intercept,
        "topic_aware": topic_aware,
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
        "avg_case_resolution_time_days": metrics.avg_case_resolution_time_days,
        "percent_cases_closed_last_335": metrics.percent_closed_in_window(30.0),
        "predicted_nps_variance": metrics.predicted_nps_variance,
        "_daily_queue_lengths": metrics.daily_queue_lengths,
    }


# =============================================================================
# SMOKE TEST
# =============================================================================

if __name__ == "__main__":
    print("=== Study 3c smoke test ===")
    print(f"CALIBRATED_SCALING_FACTOR: {CALIBRATED_SCALING_FACTOR:.4f}")
    print(f"BETA_Z: {BETA_Z:.4f}")
    print(f"NPS_PRED_COEF_STUDY3: {NPS_PRED_COEF_STUDY3:.6f}")
    print(f"NPS_PRED_TOPIC_COEFS: {NPS_PRED_TOPIC_COEFS}")
    print()

    for topic_aware in [False, True]:
        print(f"--- topic_aware={topic_aware}, NPS, 6 agenter, ρ=0.85, hard, 30 dage ---")
        result = run_single_simulation({
            "discipline": "NPS",
            "n_agents": 6,
            "sla_hours": None,
            "replication": 1,
            "rho": 0.85,
            "rho_idx": 3,
            "sampling_mode": "hard",
            "nps_intercept": NPS_PRED_INTERCEPT,
            "topic_aware": topic_aware,
            "d_end": 30,
        })
        result.pop("_daily_queue_lengths")
        print(f"  avg_individual_nps:    {result['avg_individual_nps']:.4f}")
        print(f"  organisation_nps:      {result['organisation_nps']:.2f}")
        print(f"  predicted_nps_variance: {result['predicted_nps_variance']:.6f}")
        print()
