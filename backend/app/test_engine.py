"""Business logic checks, runnable with python -m unittest discover -s app."""
import unittest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import runway, risk_for
from simulation import seeded_households, generate_intervals
from passwords import hash_password, verify_password
from app.forecasting import forecast_horizons
from anomaly import score_usage_anomaly, sustained_usage_anomaly
from budgets import recommended_range
from app.maintenance import validate_affected_towers, validate_maintenance_window
from app.complaint_clusters import cluster_complaints

class WaterEngineTests(unittest.TestCase):
    def test_runway_reacts_to_demand_and_tanker(self):
        base = runway(180000, 120000, 45000)
        high = runway(180000, 180000, 45000)
        supplied = runway(180000, 120000, 45000, tanker_eta=5, tanker_litres=12000)
        self.assertLess(high["hours_to_critical"], base["hours_to_critical"])
        self.assertGreater(supplied["hours_to_critical"], base["hours_to_critical"])

    def test_risk_thresholds_are_ordered(self):
        self.assertEqual(risk_for(5), "CRITICAL")
        self.assertEqual(risk_for(10), "HIGH")
        self.assertEqual(risk_for(20), "MODERATE")

    def test_synthetic_population_and_events(self):
        self.assertEqual(len(seeded_households()), 300)
        now = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
        normal = generate_intervals(now)
        leak = generate_intervals(now, event="LEAK_EVENT")
        self.assertEqual(len(normal), 300)
        self.assertGreater(leak[86]["consumed_litres"], normal[86]["consumed_litres"])

    def test_trained_forecast_has_measured_synthetic_metrics_and_split(self):
        result = forecast_horizons(datetime(2026, 10, 7, tzinfo=timezone.utc))
        self.assertEqual(len(result["hourly"]), 48)
        self.assertEqual(set(result["horizons"]), {"next_1h_litres", "next_6h_litres", "next_24h_litres", "next_48h_litres"})
        self.assertEqual(result["model"], "jalos-seasonal-ridge")
        self.assertGreater(result["metrics"]["rmse_litres_per_hour"], 0)
        self.assertEqual(result["split"]["test_rows"], 2592)
        self.assertLess(
            result["metrics"]["rmse_litres_per_hour"],
            result["baselines"]["seasonal_naive_previous_day"]["test_metrics"]["rmse_litres_per_hour"],
        )
        self.assertIn("not validated against real meters", result["evaluation_scope"])
        self.assertEqual(result["hourly"][0]["method"], "trained_seasonal_ridge")

    def test_forecast_artifact_has_model_versioning_metadata(self):
        artifact_path = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "water-demand-ridge-v1.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["model_name"], "jalos-seasonal-ridge")
        self.assertEqual(artifact["version"], "1.0.0")
        self.assertEqual(artifact["dataset_version"], "synthetic-society-15m-v1")
        self.assertEqual(artifact["artifact_path"], "ml/artifacts/water-demand-ridge-v1.json")
        self.assertTrue(artifact["features"])
        self.assertIn("rmse_litres_per_hour", artifact["metrics"])

    def test_forecast_scenario_changes_predicted_demand(self):
        start = datetime(2026, 10, 7, tzinfo=timezone.utc)
        normal = forecast_horizons(start, "NORMAL_DAY")
        high_use = forecast_horizons(start, "HIGH_USAGE")
        self.assertGreater(high_use["horizons"]["next_24h_litres"], normal["horizons"]["next_24h_litres"])

    def test_password_hash_is_salted_and_verifiable(self):
        first = hash_password("resident secret")
        second = hash_password("resident secret")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("resident secret", first))
        self.assertFalse(verify_password("wrong password", first))
        self.assertFalse(verify_password("resident secret", "plaintext"))

    def test_tanker_only_extends_runway_if_it_arrives_before_reserve(self):
        no_supply = runway(100_000, 120_000, 45_000, tanker_eta=30, tanker_litres=12_000)
        on_time = runway(100_000, 120_000, 45_000, tanker_eta=5, tanker_litres=12_000)
        self.assertEqual(no_supply["hours_to_critical"], 11.0)
        self.assertGreater(on_time["hours_to_critical"], no_supply["hours_to_critical"])

    def test_tanker_after_reserve_extends_time_to_empty_only(self):
        result = runway(100_000, 120_000, 45_000, tanker_eta=15, tanker_litres=12_000)
        self.assertEqual(result["hours_to_critical"], 11.0)
        self.assertEqual(result["hours_to_empty"], 22.4)

    def test_delivery_is_capped_by_available_tank_capacity(self):
        result = runway(90_000, 24_000, 10_000, tanker_eta=0, tanker_litres=50_000, capacity=100_000)
        self.assertEqual(result["hours_to_critical"], 90.0)
        self.assertEqual(result["hours_to_empty"], 100.0)

    def test_rule_anomaly_requires_sustained_above_baseline_usage(self):
        self.assertFalse(sustained_usage_anomaly(10, 4))
        self.assertTrue(sustained_usage_anomaly(36, 8))

    def test_peer_profile_anomaly_scores_are_explainable_and_do_not_confirm_leaks(self):
        peers = [0.9, 1.0, 1.0, 1.05, 1.1]
        self.assertIsNone(score_usage_anomaly(30, 25, peers))
        high = score_usage_anomaly(120, 20, peers)
        self.assertIsNotNone(high)
        self.assertEqual(high["severity"], "HIGH")
        self.assertGreaterEqual(high["score"], 0.75)

    def test_sustained_overnight_usage_can_raise_a_possible_anomaly(self):
        result = score_usage_anomaly(
            24, 20, [1.0, 1.0, 1.0, 1.05],
            overnight_actual_litres=30,
            overnight_expected_litres=8,
        )
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["score"], 0.55)
        self.assertGreater(result["overnight_ratio"], 3)

    def test_water_budget_tightens_as_society_risk_rises(self):
        normal = recommended_range(500, "NORMAL")
        critical = recommended_range(500, "CRITICAL")
        self.assertEqual(normal, [450, 600])
        self.assertGreater(normal[1], critical[1])

    def test_maintenance_windows_require_ordered_timezone_aware_times(self):
        start = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
        validate_maintenance_window(start, end)
        with self.assertRaises(ValueError):
            validate_maintenance_window(end, start)
        with self.assertRaises(ValueError):
            validate_maintenance_window(start.replace(tzinfo=None), end)

    def test_maintenance_scope_rejects_unknown_towers(self):
        validate_affected_towers(["Tower C"])
        with self.assertRaises(ValueError):
            validate_affected_towers(["Tower Z"])

    def test_complaints_cluster_by_tower_and_minimum_count(self):
        reports = [
            {"tower": "Tower C", "category": "LOW_PRESSURE", "created_at": f"2026-10-07T09:{minute:02d}:00+00:00"}
            for minute in range(5)
        ] + [{"tower": "Tower D", "category": "OTHER", "created_at": "2026-10-07T09:00:00+00:00"}]
        result = cluster_complaints(reports)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tower"], "Tower C")
        self.assertEqual(result[0]["complaint_count"], 5)
        self.assertEqual(result[0]["pressure_or_no_water_reports"], 5)

if __name__ == "__main__": unittest.main()


