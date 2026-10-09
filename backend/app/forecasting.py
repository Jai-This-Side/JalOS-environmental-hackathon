"""Inference for the versioned JalOS synthetic seasonal-ridge model."""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

MODEL_ARTIFACT = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "water-demand-ridge-v1.json"


@lru_cache(maxsize=1)
def load_model() -> dict:
    """Load the trained artifact once; a missing model should fail visibly."""
    with MODEL_ARTIFACT.open(encoding="utf-8") as artifact_file:
        artifact = json.load(artifact_file)
    required_metadata = {"model_name", "version", "training_date", "dataset_version", "features", "artifact_path", "metrics"}
    missing_metadata = required_metadata - artifact.keys()
    if missing_metadata:
        raise ValueError(f"Forecast model metadata is missing: {', '.join(sorted(missing_metadata))}")
    if len(artifact.get("coefficients", [])) != artifact.get("feature_count"):
        raise ValueError(f"Invalid forecast model artifact: {MODEL_ARTIFACT}")
    return artifact


def _features(at: datetime) -> list[float]:
    hour = at.hour + at.minute / 60
    morning = max(0.0, math.sin((hour - 5) * math.pi / 4))
    evening = max(0.0, math.sin((hour - 17) * math.pi / 6))
    daily_profile = 0.35 + 1.8 * morning + 1.7 * evening
    season = float(at.month in (4, 5, 6))
    work_period = float(at.weekday() < 5 and 8 <= at.hour < 17)
    return [
        1.0,
        daily_profile,
        daily_profile * work_period,
        daily_profile * season,
        daily_profile * work_period * season,
    ]


def _predict(coefficients: list[float], at: datetime) -> float:
    return sum(weight * value for weight, value in zip(coefficients, _features(at)))


def forecast_hourly(start: datetime, hours: int, event: str = "NORMAL_DAY") -> list[dict]:
    """Predict society demand from the trained model and apply named demo events."""
    model = load_model()
    coefficients = model["coefficients"]
    multiplier = 1.3 if event == "HIGH_USAGE" else 1.22 if event == "HEATWAVE" else 1.0
    leak_increment = 216.0 if event == "LEAK_EVENT" else 0.0
    points = []
    for offset in range(hours):
        hour = start + timedelta(hours=offset)
        demand = max(0.0, _predict(coefficients, hour) * multiplier + leak_increment)
        points.append(
            {
                "time": hour.isoformat(),
                "demand_litres": round(demand),
                "method": "trained_seasonal_ridge",
            }
        )
    return points


def forecast_horizons(start: datetime, event: str = "NORMAL_DAY") -> dict:
    model = load_model()
    hourly = forecast_hourly(start, 48, event)

    def total(count: int) -> int:
        return sum(point["demand_litres"] for point in hourly[:count])

    return {
        "synthetic_prototype_data": True,
        "model": model["model_name"],
        "model_version": model["version"],
        "dataset_version": model["dataset_version"],
        "evaluation_scope": "held-out synthetic data; not validated against real meters",
        "metrics": model["metrics"],
        "baselines": model["baselines"],
        "split": model["chronological_split"],
        "horizons": {
            f"next_{count}h_litres": total(count) for count in (1, 6, 24, 48)
        },
        "hourly": hourly,
    }
