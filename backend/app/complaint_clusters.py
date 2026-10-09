"""Rule-based complaint clustering for operational decision support."""
from __future__ import annotations

from collections import Counter, defaultdict


def cluster_complaints(complaints: list[dict], *, minimum_count: int = 5) -> list[dict]:
    by_tower: dict[str, list[dict]] = defaultdict(list)
    for complaint in complaints:
        tower = str(complaint.get("tower", "")).strip()
        if tower:
            by_tower[tower].append(complaint)

    clusters = []
    for tower, rows in by_tower.items():
        if len(rows) < minimum_count:
            continue
        categories = Counter(row.get("category", "OTHER") for row in rows)
        pressure_reports = categories.get("LOW_PRESSURE", 0) + categories.get("WATER_NOT_AVAILABLE", 0)
        clusters.append({
            "tower": tower,
            "complaint_count": len(rows),
            "pressure_or_no_water_reports": pressure_reports,
            "categories": dict(categories),
            "first_report_at": min(row["created_at"] for row in rows),
            "last_report_at": max(row["created_at"] for row in rows),
        })
    return sorted(clusters, key=lambda item: item["complaint_count"], reverse=True)
