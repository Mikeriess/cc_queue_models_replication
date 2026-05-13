"""
Study 4b — Sinusoidal arrivals × topic-aware NPS predictor.

Fork of study4/simulation.py. Single mechanical change vs Study 4:

  * The NPS predictor (Eq. 9) may now include a topic term controlled by
    a topic-accuracy parameter `rho_topic` ∈ [0, 1]:

      - rho_topic = 0.0 → no topic term, identical to Study 4 / topic_aware=False
      - rho_topic > 0   → the predictor sees the true topic with prob
                          rho_topic, otherwise a uniform-random topic.
                          The topic term uses the *true* coefficient table
                          NPS_PRED_TOPIC_COEFS (= NPS_SIM_TOPIC_COEFS, the
                          Study 3c "perfect coef knowledge" convention).
      - rho_topic = 1.0 → topic-aware predictor with perfect topic info,
                          identical to Study 3c's topic_aware=True.

  * A dedicated rng_topic_pred RNG isolates the topic-prediction coin
    flips from the throughput-prediction noise stream, so the same case
    at the same (rep, ρ_throughput) gets the same predicted-topic draws
    across ρ_topic levels. At ρ_topic = 0 the RNG is never consumed, so
    those cells are bit-identical paired-seeded with Study 4.

Sinusoidal arrival modulation (amplitude / period / phase) is unchanged
from Study 4. All other model functions are unchanged from Study 4 /
Study 3e.
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

# =============================================================================
# CONSTANTS (inherited from Study 2 — unchanged)
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
# MODEL COEFFICIENTS (inherited from Study 2)
# =============================================================================

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

TRANSITION_MATRIX = np.array([
    [0.08, 0.00, 0.67, 0.25],
    [0.00, 0.02, 0.96, 0.02],
    [0.00, 0.02, 0.45, 0.53],
    [0.00, 0.00, 0.00, 1.00],
])
INITIAL_PROBS = np.array([0.0, 0.92, 0.08, 0.0])

ARRIVAL_INTERCEPT = 726.2
ARRIVAL_COEFS = {
    "year": -0.3589,
    "month": -0.0881,
    "day": 0.0078,
    "weekday": 0.2616,
}

NPS_SIM_INTERCEPT = 2.3006
NPS_SIM_RHO = 1.3005
NPS_SIM_THROUGHPUT_COEF = -0.0098
NPS_SIM_TOPIC_COEFS = {
    "d_2-z_4": -0.1291, "g_1-z_4": 0.1008, "j_1-z_4": 0.0853,
    "q_3-z_4": -0.0427, "r_2-z_4": -0.0317, "w_1-z_4": 0.0000,
    "w_2-z_4": 0.0000, "z_2-z_4": 0.0967, "z_3-z_4": -0.0048,
    "z_4": 0.0,
}

NPS_PRED_INTERCEPT = 10.2211
NPS_PRED_THROUGHPUT_COEF = -0.0949

# Study 4b: the predictor's topic coefficients. Study 3c convention —
# perfect coefficient knowledge (uses the same table as the simulation).
NPS_PRED_TOPIC_COEFS = dict(NPS_SIM_TOPIC_COEFS)


# =============================================================================
# CALIBRATION + EMPIRICAL MULTINOMIAL
# =============================================================================

CALIBRATION_FILE = Path(__file__).parent / "results" / "calibration.json"
EMPIRICAL_NPS_FILE = Path(__file__).parent / "results" / "empirical_nps_multinomial.json"


def _load_calibration() -> Dict[str, float]:
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
            print(f"Warning: could not load {CALIBRATION_FILE}: {e}")
    return defaults


def _load_empirical_multinomial() -> Optional[List[float]]:
    if EMPIRICAL_NPS_FILE.exists():
        try:
            with open(EMPIRICAL_NPS_FILE) as f:
                data = json.load(f)
            props = data["proportions"]
            assert len(props) == 11
            assert abs(sum(props) - 1.0) < 1e-3
            return list(props)
        except Exception as e:
            print(f"Warning: could not load {EMPIRICAL_NPS_FILE}: {e}")
    return None


_calibration = _load_calibration()
CALIBRATED_SCALING_FACTOR: float = _calibration["scaling_factor"]
BETA_Z: float = _calibration["beta_z"]

NPS_PRED_COEF_STUDY3 = NPS_PRED_THROUGHPUT_COEF * CALIBRATED_SCALING_FACTOR

EMPIRICAL_NPS_MULTINOMIAL: Optional[List[float]] = _load_empirical_multinomial()

_U_CLIP = 1.0 - 1e-9


# =============================================================================
# SINUSOIDAL ARRIVAL MODULATION (inherited from Study 4 — unchanged)
# =============================================================================

def sinusoidal_factor(t_days: float, amplitude: float,
                       period_days: float, phase: float = 0.0) -> float:
    if amplitude <= 0.0:
        return 1.0
    return 1.0 + amplitude * math.sin(2.0 * math.pi * t_days / period_days + phase)


# =============================================================================
# TARGET MULTINOMIAL FAMILY (Study 3e — unchanged)
# =============================================================================

def build_target(f: float) -> List[float]:
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"f must be in [0, 1], got {f}")
    p = [0.0] * 11
    p[7] = f / 2.0
    p[8] = f / 2.0
    rest = (1.0 - f) / 9.0
    for k in (0, 1, 2, 3, 4, 5, 6, 9, 10):
        p[k] = rest
    assert abs(sum(p) - 1.0) < 1e-12
    return p


# =============================================================================
# MODEL FUNCTIONS
# =============================================================================

def simulate_activity_duration(case_topic: str, activity_type: str,
                                activity_number: int, resource_effect: float,
                                rng: np.random.Generator,
                                u_fixed: Optional[float] = None,
                                z_feature: float = 0.0) -> float:
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


def _arrival_linear_pred(time_days: float) -> float:
    day_number = int(math.floor(time_days))
    total_day_of_year = 182 + day_number
    year = SIM_START_YEAR + total_day_of_year // 365
    day_in_year = total_day_of_year % 365
    month = _day_to_month(day_in_year)
    day_of_month = _day_to_day_of_month(day_in_year, month)

    raw_weekday = day_number % 7
    weekday = (raw_weekday - 1) % 7

    return (ARRIVAL_INTERCEPT
            + ARRIVAL_COEFS["year"] * year
            + ARRIVAL_COEFS["month"] * month
            + ARRIVAL_COEFS["day"] * day_of_month
            + ARRIVAL_COEFS["weekday"] * weekday)


def simulate_inter_arrival_time(current_time_days: float,
                                 rng: np.random.Generator,
                                 amplitude: float = 0.0,
                                 period_days: float = 14.0,
                                 phase: float = 0.0) -> float:
    """Sinusoidally-modulated inter-arrival sampler (unchanged from Study 4)."""
    linear_pred_now = _arrival_linear_pred(current_time_days)

    if amplitude <= 0.0:
        u = rng.uniform(0.0, 1.0)
        inter_arrival_hours = -math.log(1 - u) * math.exp(linear_pred_now)
        return inter_arrival_hours / 24.0

    t = current_time_days
    while True:
        day_number = int(math.floor(t))
        next_day_boundary = float(day_number + 1)

        linear_pred = _arrival_linear_pred(t)
        lambda_base_per_day = 24.0 / math.exp(linear_pred)
        lambda_max = lambda_base_per_day * (1.0 + amplitude)

        u = rng.uniform(0.0, 1.0)
        candidate_dt = -math.log(1.0 - u) / lambda_max
        t_candidate = t + candidate_dt

        if t_candidate >= next_day_boundary:
            t = next_day_boundary
            continue

        u_accept = rng.uniform(0.0, 1.0)
        sin_val = math.sin(2.0 * math.pi * t_candidate / period_days + phase)
        ratio = (1.0 + amplitude * sin_val) / (1.0 + amplitude)
        if u_accept <= ratio:
            return t_candidate - current_time_days
        t = t_candidate


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


def predict_nps_study4b(predicted_throughput_minutes: float,
                         predicted_topic: Optional[str],
                         nps_intercept: float = NPS_PRED_INTERCEPT) -> float:
    """
    Predicted NPS (Eq. 9 extended). When predicted_topic is None, the
    predictor reduces to Study 2/3/3e form (throughput-only). When
    predicted_topic is provided, the topic term NPS_PRED_TOPIC_COEFS[t]
    is added — the Study 3c "topic_aware" form.
    """
    log_throughput = math.log(predicted_throughput_minutes + 1)
    topic_term = (NPS_PRED_TOPIC_COEFS.get(predicted_topic, 0.0)
                  if predicted_topic is not None else 0.0)
    return (nps_intercept
            + NPS_PRED_COEF_STUDY3 * log_throughput
            + topic_term) - 1


def sample_predicted_topic(actual_topic: str, rho_topic: float,
                            rng_topic: np.random.Generator) -> Optional[str]:
    """
    Stochastic categorical topic predictor. Mirrors the mechanism used for
    throughput-ρ: with probability rho_topic the predictor sees the true
    topic; otherwise it sees a uniform-random topic.

    Returns None when rho_topic <= 0.0 (no topic term in the predictor —
    bit-identical to Study 4 behaviour). The RNG is never consumed in
    this branch, so ρ_topic=0 cells are paired-seeded with Study 4.
    """
    if rho_topic <= 0.0:
        return None
    u = rng_topic.uniform(0.0, 1.0)
    if u < rho_topic:
        return actual_topic
    return CASE_TOPICS[int(rng_topic.integers(0, len(CASE_TOPICS)))]


def simulate_nps_response(actual_throughput_minutes: float, case_topic: str,
                           rng: np.random.Generator) -> int:
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
# DATA STRUCTURES
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
    predicted_topic: Optional[str] = None
    predicted_throughput: float = 0.0
    predicted_nps: float = 0.0

    z_actual: float = 0.0
    u_actual: float = 0.5
    z_pred: float = 0.0

    predicted_nps_binned: int = 0
    tie_break_key: float = 0.0

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
# RANK-BINNING (unchanged from Study 3d/3e/4)
# =============================================================================

def apply_rank_binning(cases: List[Case],
                       target_multinomial: List[float]) -> None:
    if not cases:
        return
    n = len(cases)
    cum_target = np.cumsum(target_multinomial)
    cum_alloc = np.round(cum_target * n).astype(int)
    cum_alloc[-1] = n
    counts = np.diff(np.concatenate([[0], cum_alloc]))

    sorted_cases = sorted(cases, key=lambda c: c.predicted_nps)

    cursor = 0
    for bin_value, n_in_bin in enumerate(counts):
        for offset in range(n_in_bin):
            sorted_cases[cursor + offset].predicted_nps_binned = bin_value
        cursor += n_in_bin


# =============================================================================
# ARRIVAL GENERATION + QUEUE MANAGEMENT
# =============================================================================

def generate_all_arrivals(d_end: int,
                          rng_arrivals: np.random.Generator,
                          rng_actual: np.random.Generator,
                          rng_pred_noise: np.random.Generator,
                          rng_topic_pred: np.random.Generator,
                          rho: float,
                          rho_topic: float = 0.0,
                          nps_intercept: float = NPS_PRED_INTERCEPT,
                          amplitude: float = 0.0,
                          period_days: float = 14.0,
                          phase: float = 0.0) -> List[Case]:
    cases: List[Case] = []
    z = 0.0
    case_id = 1
    sqrt_one_minus_rho_sq = math.sqrt(max(0.0, 1.0 - rho * rho))

    while z < d_end:
        inter_arrival = simulate_inter_arrival_time(
            z, rng_arrivals,
            amplitude=amplitude, period_days=period_days, phase=phase,
        )
        z += inter_arrival
        if z >= d_end:
            break

        topic = CASE_TOPICS[int(rng_arrivals.integers(0, len(CASE_TOPICS)))]
        tie_break = float(rng_arrivals.uniform(0.0, 1.0))

        z_actual = float(rng_actual.normal(0.0, 1.0))
        u_actual = float(norm.cdf(z_actual))
        epsilon = float(rng_pred_noise.normal(0.0, 1.0))
        z_pred = rho * z_actual + sqrt_one_minus_rho_sq * epsilon

        pred_throughput = predict_throughput_from_z(z_pred)
        pred_topic = sample_predicted_topic(topic, rho_topic, rng_topic_pred)
        pred_nps = predict_nps_study4b(
            pred_throughput, pred_topic, nps_intercept=nps_intercept,
        )

        case = Case(
            id=case_id,
            arrival_time=z,
            case_topic=topic,
            predicted_topic=pred_topic,
            predicted_throughput=pred_throughput,
            predicted_nps=pred_nps,
            z_actual=z_actual,
            u_actual=u_actual,
            z_pred=z_pred,
            tie_break_key=tie_break,
        )
        cases.append(case)
        case_id += 1

    return cases


def queue_management(queue: List[Case], discipline: str,
                      current_time: float, sla_hours: Optional[float]) -> List[Case]:
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
    elif discipline == "NPS_BINNED":
        ordered = sorted(
            visible,
            key=lambda c: (abs(c.predicted_nps_binned - NPS_MIDPOINT),
                            c.tie_break_key),
        )
    else:
        raise ValueError(f"Unknown queue discipline: {discipline}")

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
        raise ValueError(f"Unknown sampling_mode: {sampling_mode}")

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
# MAIN LOOP
# =============================================================================

@dataclass
class SimulationMetrics:
    daily_queue_lengths: List[int] = field(default_factory=list)
    daily_waiting_times: List[float] = field(default_factory=list)
    daily_utilisation: List[float] = field(default_factory=list)
    daily_arrivals: List[int] = field(default_factory=list)

    total_cases_arrived: int = 0
    total_cases_closed: int = 0
    nps_responses: List[int] = field(default_factory=list)
    nps_response_arrivals: List[float] = field(default_factory=list)

    closed_case_arrivals: List[float] = field(default_factory=list)
    closed_case_throughput_days: List[float] = field(default_factory=list)
    all_case_arrivals: List[float] = field(default_factory=list)

    top_class_size: int = 0
    bulk_class_size: int = 0

    # Diagnostics for the topic-aware predictor
    predicted_nps_var: float = 0.0
    predicted_nps_range: float = 0.0
    topic_match_rate: float = 0.0
    pred_actual_corr: float = 0.0

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
    def percent_detractors(self) -> float:
        if not self.nps_responses:
            return 0.0
        return sum(1 for n in self.nps_responses if n <= 6) / len(self.nps_responses)

    @property
    def percent_passives(self) -> float:
        if not self.nps_responses:
            return 0.0
        return sum(1 for n in self.nps_responses if 7 <= n <= 8) / len(self.nps_responses)

    @property
    def percent_promoters(self) -> float:
        if not self.nps_responses:
            return 0.0
        return sum(1 for n in self.nps_responses if n >= 9) / len(self.nps_responses)

    @property
    def avg_case_resolution_time_days(self) -> float:
        return float(np.mean(self.closed_case_throughput_days)) if self.closed_case_throughput_days else 0.0

    @property
    def peak_queue_length(self) -> int:
        return int(max(self.daily_queue_lengths)) if self.daily_queue_lengths else 0

    def percent_closed_in_window(self, start_day: float) -> float:
        n_arrived = sum(1 for t in self.all_case_arrivals if t >= start_day)
        if n_arrived == 0:
            return 0.0
        n_closed = sum(1 for t in self.closed_case_arrivals if t >= start_day)
        return n_closed / n_arrived

    def organisation_nps_in_window(self, start_day: float, end_day: float) -> float:
        responses = [n for n, a in zip(self.nps_responses, self.nps_response_arrivals)
                     if start_day <= a < end_day]
        if not responses:
            return 0.0
        total = len(responses)
        promoters = sum(1 for n in responses if n >= 9) / total
        detractors = sum(1 for n in responses if n <= 6) / total
        return (promoters - detractors) * 100


def simulate_timeline(discipline: str, n_agents: int, sla_hours: Optional[float],
                       rho: float, sampling_mode: str,
                       d_end: int = 365,
                       seeds: Optional[Dict[str, int]] = None,
                       nps_intercept: float = NPS_PRED_INTERCEPT,
                       target_multinomial: Optional[List[float]] = None,
                       amplitude: float = 0.0,
                       period_days: float = 14.0,
                       phase: float = 0.0,
                       rho_topic: float = 0.0,
                       ) -> SimulationMetrics:
    if seeds is None:
        base = np.random.default_rng().integers(0, 2**31 - 1)
        seeds = {
            "arrivals": int(base) + 1_000_000,
            "actual": int(base) + 2_000_000,
            "pred_noise": int(base) + 3_000_000,
            "simulation": int(base) + 4_000_000,
            "topic_pred": int(base) + 5_000_000,
        }

    rng_arrivals = np.random.default_rng(seeds["arrivals"])
    rng_actual = np.random.default_rng(seeds["actual"])
    rng_pred_noise = np.random.default_rng(seeds["pred_noise"])
    rng_sim = np.random.default_rng(seeds["simulation"])
    rng_topic_pred = np.random.default_rng(seeds["topic_pred"])

    metrics = SimulationMetrics()

    agents = []
    for i in range(n_agents):
        effect = rng_sim.normal(RESOURCE_EFFECT_MEAN, RESOURCE_EFFECT_STD)
        agents.append(Agent(id=i + 1, resource_effect=effect))

    all_cases = generate_all_arrivals(
        d_end, rng_arrivals, rng_actual, rng_pred_noise, rng_topic_pred,
        rho, rho_topic=rho_topic,
        nps_intercept=nps_intercept,
        amplitude=amplitude, period_days=period_days, phase=phase,
    )

    if discipline == "NPS_BINNED":
        target = target_multinomial if target_multinomial is not None else EMPIRICAL_NPS_MULTINOMIAL
        if target is None:
            raise RuntimeError("NPS_BINNED requires target_multinomial.")
        apply_rank_binning(all_cases, target)

        binned_arr = np.array([c.predicted_nps_binned for c in all_cases], dtype=int)
        if len(binned_arr) > 0:
            top_count = int(((binned_arr == 7) | (binned_arr == 8)).sum())
            counts_per_bin = np.bincount(binned_arr, minlength=11)
            bulk_count = int(counts_per_bin.max())
        else:
            top_count = 0
            bulk_count = 0
        metrics.top_class_size = top_count
        metrics.bulk_class_size = bulk_count

    metrics.total_cases_arrived = len(all_cases)
    metrics.all_case_arrivals = [c.arrival_time for c in all_cases]

    # Topic-aware diagnostics
    pred_nps_arr = np.array([c.predicted_nps for c in all_cases])
    if len(pred_nps_arr) > 1:
        metrics.predicted_nps_var = float(np.var(pred_nps_arr))
        metrics.predicted_nps_range = float(pred_nps_arr.max() - pred_nps_arr.min())
    if rho_topic > 0:
        matches = sum(1 for c in all_cases if c.predicted_topic == c.case_topic)
        metrics.topic_match_rate = matches / max(1, len(all_cases))
    else:
        metrics.topic_match_rate = float("nan")

    case_lookup = {c.id: c for c in all_cases}
    queue_buffer: List[Case] = []
    next_case_idx = 0

    arrivals_by_day = np.zeros(d_end, dtype=int)
    for c in all_cases:
        d = int(math.floor(c.arrival_time))
        if 0 <= d < d_end:
            arrivals_by_day[d] += 1
    metrics.daily_arrivals = arrivals_by_day.tolist()

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
                metrics.nps_response_arrivals.append(case.arrival_time)
                metrics.total_cases_closed += 1
                metrics.closed_case_arrivals.append(case.arrival_time)
                metrics.closed_case_throughput_days.append(
                    case.actual_throughput_minutes / (60.0 * 24.0)
                )

        queue_buffer = [c for c in queue_buffer if c.status != "closed"]

    # Pred-vs-actual correlation (closed cases only)
    if metrics.nps_responses:
        closed_ids = {c.id for c in all_cases if c.nps_response is not None}
        pred_for_closed = [c.predicted_nps for c in all_cases if c.id in closed_ids]
        actual_for_closed = [c.nps_response for c in all_cases if c.id in closed_ids]
        if len(pred_for_closed) > 1 and np.std(pred_for_closed) > 0 and np.std(actual_for_closed) > 0:
            metrics.pred_actual_corr = float(np.corrcoef(pred_for_closed, actual_for_closed)[0, 1])

    return metrics


# =============================================================================
# HELPERS
# =============================================================================

def derive_seeds(replication: int, rho_idx: int) -> Dict[str, int]:
    """
    Paired seeding. Same as Study 4 with an added topic_pred stream that
    depends only on `replication`, so ρ_topic levels at the same (rep,
    ρ_throughput) share the same topic-prediction coin flips.
    """
    base = hash(("study3", replication)) % (2**31)
    return {
        "arrivals": base + 1_000_000,
        "actual": base + 2_000_000,
        "pred_noise": base + 3_000_000 + rho_idx,
        "simulation": base + 4_000_000,
        "topic_pred": base + 5_000_000,
    }


def run_single_simulation(params: dict) -> dict:
    discipline = params["discipline"]
    n_agents = params["n_agents"]
    sla_hours = params.get("sla_hours")
    replication = params["replication"]
    rho = params["rho"]
    rho_idx = params["rho_idx"]
    sampling_mode = params["sampling_mode"]
    nps_intercept = params.get("nps_intercept", NPS_PRED_INTERCEPT)
    d_end = params.get("d_end", 365)

    target_f = params.get("target_f", None)
    target_multinomial = None
    if discipline == "NPS_BINNED" and target_f is not None:
        target_multinomial = build_target(target_f)

    amplitude = float(params.get("amplitude", 0.0))
    period_days = float(params.get("period_days", 14.0))
    phase = float(params.get("phase", 0.0))
    rho_topic = float(params.get("rho_topic", 0.0))

    seeds = derive_seeds(replication, rho_idx)
    metrics = simulate_timeline(
        discipline, n_agents, sla_hours, rho, sampling_mode, d_end, seeds,
        nps_intercept=nps_intercept,
        target_multinomial=target_multinomial,
        amplitude=amplitude, period_days=period_days, phase=phase,
        rho_topic=rho_topic,
    )

    burn_in_day = 30.0
    half_split = burn_in_day + (d_end - burn_in_day) / 2.0
    org_nps_first_half = metrics.organisation_nps_in_window(burn_in_day, half_split)
    org_nps_second_half = metrics.organisation_nps_in_window(half_split, float(d_end))

    arrivals_in_window = sum(
        1 for t in metrics.all_case_arrivals if t >= burn_in_day
    )

    return {
        "rho": rho,
        "rho_idx": rho_idx,
        "rho_topic": rho_topic,
        "sampling_mode": sampling_mode,
        "nps_intercept": nps_intercept,
        "discipline": discipline,
        "n_agents": n_agents,
        "sla_hours": sla_hours if sla_hours else "None",
        "replication": replication,
        "target_f": target_f if target_f is not None else float("nan"),
        "amplitude": amplitude,
        "period_days": period_days,
        "phase": phase,
        "avg_queue_length": metrics.avg_queue_length,
        "peak_queue_length": metrics.peak_queue_length,
        "avg_waiting_time_days": metrics.avg_waiting_time_days,
        "avg_capacity_utilisation": metrics.avg_capacity_utilisation,
        "percent_cases_closed": metrics.percent_cases_closed,
        "avg_individual_nps": metrics.avg_individual_nps,
        "organisation_nps": metrics.organisation_nps,
        "organisation_nps_first_half": org_nps_first_half,
        "organisation_nps_second_half": org_nps_second_half,
        "percent_detractors": metrics.percent_detractors,
        "percent_passives": metrics.percent_passives,
        "percent_promoters": metrics.percent_promoters,
        "total_cases_arrived": metrics.total_cases_arrived,
        "total_cases_closed": metrics.total_cases_closed,
        "arrivals_after_burnin": arrivals_in_window,
        "avg_case_resolution_time_days": metrics.avg_case_resolution_time_days,
        "percent_cases_closed_last_335": metrics.percent_closed_in_window(30.0),
        "top_class_size": metrics.top_class_size,
        "bulk_class_size": metrics.bulk_class_size,
        "predicted_nps_var": metrics.predicted_nps_var,
        "predicted_nps_range": metrics.predicted_nps_range,
        "topic_match_rate": metrics.topic_match_rate,
        "pred_actual_corr": metrics.pred_actual_corr,
        "_daily_queue_lengths": metrics.daily_queue_lengths,
        "_daily_arrivals": metrics.daily_arrivals,
    }


# =============================================================================
# SMOKE TEST + PREDICTOR DIAGNOSTIC
# =============================================================================

if __name__ == "__main__":
    print("=== Study 4b smoke test ===")
    print(f"CALIBRATED_SCALING_FACTOR: {CALIBRATED_SCALING_FACTOR:.4f}")
    print(f"NPS_PRED_TOPIC_COEFS span: "
          f"{min(NPS_PRED_TOPIC_COEFS.values()):.4f} to "
          f"{max(NPS_PRED_TOPIC_COEFS.values()):.4f}")
    print()

    print("--- Predictor diagnostic: Var(pred_nps), topic_match_rate, "
          "corr(pred, actual) ---")
    print("  90-day, FCFS, 6 agents, A=0, rep=1")
    for rho in [0.5, 1.0]:
        for rho_topic in [0.0, 0.5, 1.0]:
            r = run_single_simulation({
                "discipline": "FCFS",
                "n_agents": 6,
                "sla_hours": None,
                "replication": 1,
                "rho": rho,
                "rho_idx": 2 if rho == 0.5 else 4,
                "sampling_mode": "hard",
                "d_end": 90,
                "amplitude": 0.0,
                "period_days": 14.0,
                "phase": 0.0,
                "rho_topic": rho_topic,
                "nps_intercept": 10.22,
            })
            print(f"  ρ_thr={rho:.1f}, ρ_topic={rho_topic:.1f}: "
                  f"Var(pred_nps)={r['predicted_nps_var']:.4f}, "
                  f"range={r['predicted_nps_range']:.3f}, "
                  f"topic_match={r['topic_match_rate']:.3f}, "
                  f"corr(pred,actual)={r['pred_actual_corr']:.3f}")
    print()

    print("--- Disciplines × ρ_topic at A=0.5, P=28, ρ_thr=1, 90-day ---")
    for disc in ["FCFS", "LRTF", "SRTF", "NPS", "NPS_BINNED"]:
        for rho_topic in [0.0, 0.5, 1.0]:
            params = {
                "discipline": disc,
                "n_agents": 6,
                "sla_hours": None,
                "replication": 1,
                "rho": 1.0,
                "rho_idx": 4,
                "sampling_mode": "hard",
                "d_end": 90,
                "amplitude": 0.5,
                "period_days": 28.0,
                "phase": 0.0,
                "rho_topic": rho_topic,
                "nps_intercept": 10.22,
            }
            if disc == "NPS_BINNED":
                params["target_f"] = 0.20
            r = run_single_simulation(params)
            print(f"  {disc:>11} ρ_topic={rho_topic:.1f}: "
                  f"orgNPS = {r['organisation_nps']:+.2f}, "
                  f"avg_q = {r['avg_queue_length']:.1f}, "
                  f"peak_q = {r['peak_queue_length']}")
