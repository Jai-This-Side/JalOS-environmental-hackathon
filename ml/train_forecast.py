"""Train and evaluate the JalOS synthetic demand forecaster."""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend"),
)

from app.simulation import TYPES, seeded_households

ROOT = Path(__file__).resolve().parents[1]

DATASET_VERSION = "synthetic-society-15m-v2"
MODEL_NAME = "jalos-seasonal-ridge"
MODEL_VERSION = "2.0.0"

START = datetime(2024, 1, 1, tzinfo=timezone.utc)

# 2024 is a leap year. This covers all of 2024 and 2025.
POINTS = 731 * 24 * 4
SEED = 31

# Narrow deterministic aggregate variation for 300 virtual meters.
AGGREGATE_JITTER_MIN = 0.9873
AGGREGATE_JITTER_MAX = 1.0127


def features(at: datetime) -> list[float]:
    """Return the model's time-of-day and seasonal features."""
    hour = at.hour + at.minute / 60

    morning = max(
        0.0,
        math.sin((hour - 5) * math.pi / 4),
    )
    evening = max(
        0.0,
        math.sin((hour - 17) * math.pi / 6),
    )

    daily_profile = (
        0.35 + 1.8 * morning + 1.7 * evening
    )

    season = float(at.month in (4, 5, 6))
    work_period = float(
        at.weekday() < 5 and 8 <= at.hour < 17
    )

    return [
        1.0,
        daily_profile,
        daily_profile * work_period,
        daily_profile * season,
        daily_profile * work_period * season,
    ]


def solve_ridge(
    gram: list[list[float]],
    cross: list[float],
    penalty: float,
) -> list[float]:
    """Solve the ridge-regression normal equations."""
    size = len(cross)

    matrix = [row.copy() for row in gram]
    target = cross.copy()

    # Do not penalize the intercept.
    for index in range(1, size):
        matrix[index][index] += penalty

    for pivot in range(size):
        best = max(
            range(pivot, size),
            key=lambda row: abs(matrix[row][pivot]),
        )

        if abs(matrix[best][pivot]) < 1e-12:
            raise ArithmeticError(
                "Forecast feature matrix is singular"
            )

        matrix[pivot], matrix[best] = (
            matrix[best],
            matrix[pivot],
        )
        target[pivot], target[best] = (
            target[best],
            target[pivot],
        )

        divisor = matrix[pivot][pivot]

        for column in range(pivot, size):
            matrix[pivot][column] /= divisor

        target[pivot] /= divisor

        for row in range(size):
            if row == pivot:
                continue

            factor = matrix[row][pivot]

            if factor == 0:
                continue

            for column in range(pivot, size):
                matrix[row][column] -= (
                    factor * matrix[pivot][column]
                )

            target[row] -= factor * target[pivot]

    return target


def predict(
    coefficients: list[float],
    row: list[float],
) -> float:
    return sum(
        weight * value
        for weight, value in zip(coefficients, row)
    )


def metrics(
    actual: list[float],
    predicted: list[float],
) -> dict[str, float]:
    """Compute error metrics on a held-out dataset split."""
    errors = [
        estimate - observed
        for observed, estimate in zip(actual, predicted)
    ]

    count = max(1, len(errors))

    return {
        "mae_litres_per_hour": round(
            sum(abs(error) for error in errors) / count,
            3,
        ),
        "rmse_litres_per_hour": round(
            math.sqrt(
                sum(error * error for error in errors) / count
            ),
            3,
        ),
        "mape_percent": round(
            sum(
                abs(error) / max(abs(observed), 1)
                for error, observed in zip(errors, actual)
            )
            / count
            * 100,
            3,
        ),
    }


def main() -> None:
    households = seeded_households()

    baseline_litres_per_day = sum(
        TYPES[home.household_type][1]
        for home in households
    )

    rng = Random(SEED)

    rows: list[
        tuple[datetime, list[float], float]
    ] = []

    dataset_path = (
        ROOT
        / "ml"
        / "datasets"
        / f"{DATASET_VERSION}.csv"
    )
    dataset_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Build a deterministic, two-year synthetic dataset.
    with dataset_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output:
        writer = csv.writer(output)

        writer.writerow(
            ("observed_at", "society_litres_per_hour")
        )

        for index in range(POINTS):
            at = START + timedelta(minutes=15 * index)
            hour = at.hour + at.minute / 60

            morning = max(
                0.0,
                math.sin((hour - 5) * math.pi / 4),
            )
            evening = max(
                0.0,
                math.sin((hour - 17) * math.pi / 6),
            )

            daily_profile = (
                0.35 + 1.8 * morning + 1.7 * evening
            )

            work_period_factor = (
                1.12
                if at.weekday() < 5 and 8 <= hour < 17
                else 0.94
            )

            season_factor = (
                1.15 if at.month in (4, 5, 6) else 1.0
            )

            # Aggregate the household profiles without running
            # millions of individual virtual-meter simulations.
            jitter = rng.uniform(
                AGGREGATE_JITTER_MIN,
                AGGREGATE_JITTER_MAX,
            )

            hourly_rate = (
                baseline_litres_per_day
                / 24
                * daily_profile
                * work_period_factor
                * season_factor
                * jitter
            )

            writer.writerow(
                (at.isoformat(), round(hourly_rate, 3))
            )

            rows.append(
                (at, features(at), hourly_rate)
            )

    # Keep chronological splits to avoid training on future data.
    train_end = int(POINTS * 0.70)
    validation_end = int(POINTS * 0.85)

    feature_count = len(rows[0][1])

    gram = [
        [0.0] * feature_count
        for _ in range(feature_count)
    ]
    cross = [0.0] * feature_count

    for _, vector, target in rows[:train_end]:
        for left, left_value in enumerate(vector):
            cross[left] += left_value * target

            for right, right_value in enumerate(vector):
                gram[left][right] += (
                    left_value * right_value
                )

    validation_actual = [
        item[2]
        for item in rows[train_end:validation_end]
    ]

    validation_naive = [
        rows[index - 96][2]
        for index in range(train_end, validation_end)
    ]

    best: tuple[
        float, float, list[float]
    ] | None = None

    validation_metrics_by_penalty: dict[
        str, dict[str, float]
    ] = {}

    for penalty in (0.001, 0.01, 0.1, 1.0):
        coefficients = solve_ridge(
            gram,
            cross,
            penalty,
        )

        validation_predictions = [
            predict(coefficients, item[1])
            for item in rows[train_end:validation_end]
        ]

        validation_result = metrics(
            validation_actual,
            validation_predictions,
        )

        score = validation_result[
            "rmse_litres_per_hour"
        ]

        validation_metrics_by_penalty[
            str(penalty)
        ] = validation_result

        if best is None or score < best[0]:
            best = (score, penalty, coefficients)

    assert best is not None

    _, selected_penalty, coefficients = best

    # The final 15% is reserved for test evaluation.
    test_rows = rows[validation_end:]

    test_actual = [
        item[2] for item in test_rows
    ]

    test_predictions = [
        predict(coefficients, item[1])
        for item in test_rows
    ]

    # 96 samples equals 24 hours of 15-minute observations.
    test_naive = [
        rows[index - 96][2]
        for index in range(validation_end, POINTS)
    ]

    model_path = (
        ROOT
        / "ml"
        / "artifacts"
        / "water-demand-ridge-v2.json"
    )

    artifact = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "artifact_path": (
            "ml/artifacts/water-demand-ridge-v2.json"
        ),
        "training_date": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_version": DATASET_VERSION,
        "dataset_rows": POINTS,
        "dataset_start": rows[0][0].isoformat(),
        "dataset_end": rows[-1][0].isoformat(),
        "target": (
            "society litres per hour aggregated from "
            "300 virtual household profiles at "
            "15-minute intervals"
        ),
        "generator_version": (
            "aggregate-household-profiles-v2"
        ),
        "aggregate_jitter_range": [
            AGGREGATE_JITTER_MIN,
            AGGREGATE_JITTER_MAX,
        ],
        "features": [
            "intercept",
            "synthetic household daily profile",
            "profile x weekday business-period",
            "profile x Apr-Jun season",
            "profile x business-period x season",
        ],
        "feature_count": feature_count,
        "ridge_penalty": selected_penalty,
        "chronological_split": {
            "method": (
                "first 70% train, next 15% validation, "
                "last 15% test"
            ),
            "train_rows": train_end,
            "validation_rows": (
                validation_end - train_end
            ),
            "test_rows": POINTS - validation_end,
            "validation_penalty_scores": (
                validation_metrics_by_penalty
            ),
        },
        "metrics": metrics(
            test_actual,
            test_predictions,
        ),
        "baselines": {
            "seasonal_naive_previous_day": {
                "definition": (
                    "Reuse the observed value from the "
                    "same 15-minute slot on the previous day"
                ),
                "validation_metrics": metrics(
                    validation_actual,
                    validation_naive,
                ),
                "test_metrics": metrics(
                    test_actual,
                    test_naive,
                ),
            }
        },
        "coefficients": coefficients,
    }

    model_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_path.write_text(
        json.dumps(artifact, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "dataset": str(
                    dataset_path.relative_to(ROOT)
                ),
                "artifact": str(
                    model_path.relative_to(ROOT)
                ),
                "metrics": artifact["metrics"],
                "baselines": artifact["baselines"],
                "split": artifact["chronological_split"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()