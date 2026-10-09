"""Pure water-runway and risk logic."""


def risk_for(hours: float) -> str:
    if hours <= 6:
        return "CRITICAL"
    if hours <= 12:
        return "HIGH"
    if hours <= 24:
        return "MODERATE"
    if hours <= 48:
        return "LOW"
    return "NORMAL"


def _time_to_threshold(
    inventory: float,
    rate_per_hour: float,
    threshold: float,
    tanker_eta: float,
    tanker_litres: float,
    capacity: float | None,
) -> float:
    """Project the time to one inventory threshold with one scheduled delivery."""
    if inventory <= threshold:
        return 0.0

    without_supply = (inventory - threshold) / rate_per_hour
    if tanker_litres <= 0 or tanker_eta < 0 or tanker_eta >= without_supply:
        return without_supply

    inventory_at_arrival = max(0.0, inventory - rate_per_hour * tanker_eta)
    room = max(0.0, capacity - inventory_at_arrival) if capacity is not None else tanker_litres
    delivered = min(tanker_litres, room)
    after_delivery = inventory_at_arrival + delivered
    return tanker_eta + max(0.0, (after_delivery - threshold) / rate_per_hour)


def runway(
    inventory: float,
    demand_per_day: float,
    reserve: float,
    tanker_eta: float = 1e9,
    tanker_litres: float = 0,
    capacity: float | None = None,
) -> dict:
    """Return threshold and depletion times, respecting delivery timing and tank capacity."""
    inventory = max(0.0, inventory)
    rate_per_hour = max(demand_per_day / 24, 1.0)
    tanker_eta = max(0.0, tanker_eta)

    to_critical = _time_to_threshold(
        inventory, rate_per_hour, max(0.0, reserve), tanker_eta, tanker_litres, capacity
    )
    to_empty = _time_to_threshold(
        inventory, rate_per_hour, 0.0, tanker_eta, tanker_litres, capacity
    )
    return {
        "hours_to_critical": round(to_critical, 1),
        "hours_to_empty": round(to_empty, 1),
        "risk": risk_for(to_critical),
    }
