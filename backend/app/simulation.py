"""Deterministic household demand profiles for synthetic JalOS demo telemetry."""
from dataclasses import dataclass
from datetime import datetime
from math import sin, pi
from random import Random

@dataclass(frozen=True)
class Household:
    flat_id: str
    household_type: str
    occupants: int
    tower: str

TYPES = {"SINGLE_OCCUPANT": (1, 130), "WORKING_COUPLE": (2, 230), "SMALL_FAMILY": (4, 430), "LARGE_FAMILY": (6, 620), "WORK_FROM_HOME": (3, 390), "ELDERLY": (2, 240)}

def seeded_households(seed: int = 17) -> list[Household]:
    rng = Random(seed)
    result = []
    for tower_index, letter in enumerate("ABCDEFGH"):
        flat_count = 38 if tower_index < 4 else 37
        for number in range(101, 101 + flat_count):
            kind = rng.choice(tuple(TYPES))
            result.append(Household(f"{letter}-{number}", kind, TYPES[kind][0], letter))
    return result

def interval_consumption(household: Household, at: datetime, seed: int = 1, multiplier: float = 1.0) -> float:
    """Litres consumed during a 15-minute interval; repeatable for a given input."""
    rng = Random(f"{seed}:{household.flat_id}:{at.isoformat()}")
    hour = at.hour + at.minute / 60
    morning = 1.8 * max(0, sin((hour - 5) * pi / 4))
    evening = 1.7 * max(0, sin((hour - 17) * pi / 6))
    baseline = TYPES[household.household_type][1] / 96
    weekday_factor = 1.12 if at.weekday() < 5 and 8 <= hour < 17 else 0.94
    season_factor = 1.15 if at.month in (4, 5, 6) else 1.0
    return round(max(.1, baseline * (.35 + morning + evening) * weekday_factor * season_factor * multiplier * rng.uniform(.78, 1.22)), 2)

def generate_intervals(at: datetime, seed: int = 1, event: str = "NORMAL_DAY") -> list[dict]:
    households = seeded_households(seed)
    multiplier = 1.0
    if event == "HIGH_USAGE": multiplier = 1.3
    elif event == "HEATWAVE": multiplier = 1.22
    rows = []
    for household in households:
        value = interval_consumption(household, at, seed, multiplier)
        if event == "LEAK_EVENT" and household.flat_id in {"C-111", "C-119", "C-127"}:
            value += 18.0
        rows.append({"flat_id": household.flat_id, "tower": household.tower, "meter_type": "SYNTHETIC_VIRTUAL_METER", "consumed_litres": value, "flow_litres_per_minute": round(value / 15, 3), "timestamp": at.isoformat()})
    return rows

