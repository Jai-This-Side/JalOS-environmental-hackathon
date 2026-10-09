"""Robust peer-relative scoring for possible household usage anomalies."""
from __future__ import annotations

from statistics import median


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_usage_anomaly(
    actual_litres: float,
    expected_litres: float,
    peer_ratios: list[float],
    *,
    minimum_litres: float = 20.0,
    overnight_actual_litres: float = 0.0,
    overnight_expected_litres: float = 0.0,
    latest_actual_litres: float = 0.0,
    latest_expected_litres: float = 0.0,
) -> dict | None:
    """Score sustained usage against a household profile and peer median/MAD.

    This robust, unsupervised peer comparison is decision support over synthetic
    meter readings. It never confirms a leak.
    """
    if actual_litres < minimum_litres or expected_litres <= 0 or not peer_ratios:
        return None

    ratio = actual_litres / expected_litres
    peer_center = median(peer_ratios)
    deviations = [abs(value - peer_center) for value in peer_ratios]
    mad = median(deviations) if deviations else 0.0
    robust_z = 0.6745 * (ratio - peer_center) / max(mad, 0.05)
    household_component = _clamp((ratio - 1.5) / 2.5)
    peer_component = _clamp((robust_z - 2.5) / 4.0)
    overnight_ratio = overnight_actual_litres / max(overnight_expected_litres, 1.0)
    latest_ratio = latest_actual_litres / max(latest_expected_litres, 1.0)
    overnight_component = _clamp((overnight_ratio - 2.0) / 2.0)
    spike_component = _clamp((latest_ratio - 2.5) / 4.0)
    raw_score = (
        0.5 * household_component
        + 0.25 * peer_component
        + 0.15 * overnight_component
        + 0.1 * spike_component
    )
    if overnight_actual_litres >= 10 and overnight_ratio >= 3.0:
        raw_score = max(raw_score, 0.55)
    if latest_actual_litres >= 10 and latest_ratio >= 4.0:
        raw_score = max(raw_score, 0.55)
    score = round(raw_score, 3)
    if score < 0.45:
        return None

    severity = "HIGH" if score >= 0.75 else "MEDIUM" if score >= 0.55 else "LOW"
    return {
        "score": score,
        "ratio_to_household_baseline": round(ratio, 2),
        "peer_robust_z_score": round(robust_z, 2),
        "overnight_ratio": round(overnight_ratio, 2),
        "latest_sample_ratio": round(latest_ratio, 2),
        "severity": severity,
    }


def sustained_usage_anomaly(
    actual_litres: float,
    expected_litres: float,
    *,
    minimum_litres: float = 20.0,
    ratio: float = 3.0,
) -> bool:
    """Compatibility rule for callers that need a simple sustained threshold."""
    return actual_litres >= minimum_litres and actual_litres > max(1.0, expected_litres) * ratio
