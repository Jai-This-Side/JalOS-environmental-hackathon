"""Validation helpers for scheduled society maintenance events."""
from datetime import datetime

EVENT_TYPES = {
    "TANK_CLEANING",
    "PUMP_MAINTENANCE",
    "PIPELINE_MAINTENANCE",
    "WATER_SHUTDOWN",
}
SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
TOWERS = {f"Tower {letter}" for letter in "ABCDEFGH"}


def validate_maintenance_window(start_time: datetime, end_time: datetime) -> None:
    if start_time.tzinfo is None or start_time.utcoffset() is None:
        raise ValueError("start_time must include a timezone")
    if end_time.tzinfo is None or end_time.utcoffset() is None:
        raise ValueError("end_time must include a timezone")
    if end_time <= start_time:
        raise ValueError("end_time must be later than start_time")


def validate_affected_towers(towers: list[str]) -> None:
    unknown = sorted(set(towers) - TOWERS)
    if unknown:
        raise ValueError(f"Unknown affected towers: {', '.join(unknown)}")
