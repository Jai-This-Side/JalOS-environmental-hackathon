def recommended_range(baseline_litres_per_day: float, risk: str) -> list[int]:
    """Return soft household guidance, not a legal or metered cap."""
    factors = (0.9, 1.2) if risk in {"NORMAL", "LOW"} else (0.8, 1.1) if risk == "MODERATE" else (0.7, 0.95)
    return [round(baseline_litres_per_day * factors[0]), round(baseline_litres_per_day * factors[1])]
