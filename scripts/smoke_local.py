"""Exercise the running JalOS API, role checks, simulator, complaint flow, and WebSocket."""
from __future__ import annotations

import argparse
import json
import os
import struct
import time
import zlib
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from websockets.sync.client import connect


DEFAULT_ADMIN_EMAIL = "admin@jalos.local"
DEFAULT_ADMIN_PASSWORD = "AdminDemo-2026!Change"
DEFAULT_RESIDENT_EMAIL = "resident@jalos.local"
DEFAULT_RESIDENT_PASSWORD = "ResidentDemo-2026!Change"


def call(base: str, path: str, *, token: str | None = None, method: str = "GET", body=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base.rstrip('/')}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as error:
        raw = error.read()
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw.decode("utf-8", errors="replace")
        return error.code, body


def cors_preflight(base: str, origin: str) -> tuple[int, str | None]:
    request = Request(
        f"{base.rstrip('/')}/api/v1/alerts",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
        method="OPTIONS",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("Access-Control-Allow-Origin")
    except HTTPError as error:
        return error.code, error.headers.get("Access-Control-Allow-Origin")


def upload_photo(base: str, complaint_id: int, token: str, payload: bytes) -> tuple[int, dict | bytes | None]:
    boundary = "jalos-smoke-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="photo"; filename="smoke.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode("ascii") + payload + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = Request(
        f"{base.rstrip('/')}/api/v1/complaints/{complaint_id}/photo",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return error.code, raw


def download_photo(base: str, complaint_id: int, token: str) -> tuple[int, bytes]:
    request = Request(
        f"{base.rstrip('/')}/api/v1/complaints/{complaint_id}/photo",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def one_pixel_png() -> bytes:
    def chunk(name: bytes, value: bytes) -> bytes:
        return struct.pack(">I", len(value)) + name + value + struct.pack(">I", zlib.crc32(name + value))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixel = zlib.compress(b"\x00\x15\x9a\x7d\xff")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixel) + chunk(b"IEND", b"")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    api = f"{base}/api/v1"

    status, health = call(base, "/api/v1/health/components")
    require(status == 200 and health.get("backend") == "ok" and health.get("database") == "ok", "Backend or database health check failed")
    require(health.get("simulator") == "running", f"Simulator is not running: {health.get('simulator')}")
    status, allowed_origin = cors_preflight(base, "http://localhost:5173")
    require(status == 200 and allowed_origin == "http://localhost:5173", "Local admin origin is not allowed by CORS")
    status, denied_origin = cors_preflight(base, "https://untrusted.example")
    require(status == 400 and denied_origin is None, "CORS should reject unconfigured browser origins")

    status, resident_login = call(api, "/auth/login", method="POST", body={
        "email": os.getenv("DEMO_RESIDENT_EMAIL", DEFAULT_RESIDENT_EMAIL),
        "password": os.getenv("DEMO_RESIDENT_PASSWORD", DEFAULT_RESIDENT_PASSWORD),
    })
    require(status == 200, f"Resident login failed: {resident_login}")
    resident_token = resident_login["access_token"]
    require(resident_login["user"]["role"] == "RESIDENT", "Resident login returned the wrong role")

    status, admin_login = call(api, "/auth/login", method="POST", body={
        "email": os.getenv("DEMO_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL),
        "password": os.getenv("DEMO_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
    })
    require(status == 200, f"Admin login failed: {admin_login}")
    admin_token = admin_login["access_token"]
    require(admin_login["user"]["role"] == "ADMIN", "Admin login returned the wrong role")

    call(api, "/demo/scenarios/HIGH_USAGE", token=admin_token, method="POST")
    status, resident_alerts = call(api, "/alerts", token=resident_token)
    require(status == 200 and resident_alerts, "Resident could not read persisted alerts")
    unread_alert = next((item for item in resident_alerts if not item["read"]), None)
    require(unread_alert is not None, "New alerts should be unread for the resident")
    status, admin_alerts = call(api, "/alerts", token=admin_token)
    require(status == 200 and any(item["id"] == unread_alert["id"] and not item["read"] for item in admin_alerts), "Alert read state was incorrectly shared across accounts")
    status, marked = call(api, f"/alerts/{unread_alert['id']}/read", token=resident_token, method="PATCH")
    require(status == 200 and marked.get("read") is True, "Resident could not mark an alert as read")
    status, resident_alerts = call(api, "/alerts", token=resident_token)
    require(status == 200 and any(item["id"] == unread_alert["id"] and item["read"] for item in resident_alerts), "Resident alert read state was not persisted")
    status, admin_alerts = call(api, "/alerts", token=admin_token)
    require(status == 200 and any(item["id"] == unread_alert["id"] and not item["read"] for item in admin_alerts), "Marking a resident alert read should not affect the admin account")

    status, usage = call(api, "/consumption/me", token=resident_token)
    require(status == 200 and usage.get("flat_id"), "Resident could not read private household usage")
    status, _ = call(api, "/forecasts", token=resident_token)
    require(status == 403, f"Resident role should be forbidden from admin forecasts, got HTTP {status}")
    status, forecasts = call(api, "/forecasts", token=admin_token)
    require(status == 200 and forecasts.get("horizons"), "Admin forecast endpoint did not return horizon predictions")

    status, tower_list = call(api, "/towers", token=admin_token)
    require(status == 200 and tower_list, "Admin could not read the tower list")
    status, tower_usage = call(api, f"/consumption/tower/{tower_list[0]['id']}", token=admin_token)
    require(status == 200 and tower_usage.get("flats"), "Admin tower consumption did not include household rollups")
    status, flat_usage = call(api, f"/consumption/flat/{tower_usage['flats'][0]['flat_id']}", token=admin_token)
    require(status == 200 and flat_usage.get("recommended_range_litres_per_day"), "Admin flat consumption did not include household guidance")
    status, _ = call(api, f"/consumption/flat/{tower_usage['flats'][0]['flat_id']}", token=resident_token)
    require(status == 403, "Resident role should be forbidden from admin flat consumption")

    flat_number = resident_login["user"]["flat_number"]
    status, _ = call(api, "/anomalies/reviews", token=resident_token)
    require(status == 403, "Resident role should be forbidden from anomaly review decisions")
    status, review = call(api, f"/anomalies/{flat_number}/review", token=admin_token, method="PATCH", body={"status": "FALSE_POSITIVE", "comment": "Synthetic smoke verification."})
    require(status == 200 and review.get("status") == "FALSE_POSITIVE", f"Admin could not save anomaly review: {review}")
    status, reviews = call(api, "/anomalies/reviews", token=admin_token)
    require(status == 200 and any(item["flat_id"] == flat_number and item["status"] == "FALSE_POSITIVE" for item in reviews), "Anomaly review decision was not persisted")

    flat_number = resident_login["user"]["flat_number"]
    status, _ = call(api, "/anomalies/reviews", token=resident_token)
    require(status == 403, "Resident role should be forbidden from anomaly review decisions")
    status, review = call(api, f"/anomalies/{flat_number}/review", token=admin_token, method="PATCH", body={"status": "FALSE_POSITIVE", "comment": "Synthetic smoke verification."})
    require(status == 200 and review.get("status") == "FALSE_POSITIVE", f"Admin could not save anomaly review: {review}")
    status, reviews = call(api, "/anomalies/reviews", token=admin_token)
    require(status == 200 and any(item["flat_id"] == flat_number and item["status"] == "FALSE_POSITIVE" for item in reviews), "Anomaly review decision was not persisted")

    status, deliveries = call(api, "/tankers", token=admin_token)
    require(status == 200, "Admin could not read the tanker schedule")
    active_delivery = next((item for item in deliveries if item["status"] in {"SCHEDULED", "DELAYED"}), None)
    require(active_delivery is not None, "The seeded demo must have an upcoming tanker delivery")
    original_eta = call(api, "/water/status")[1]["tanker_eta_hours"]
    status, delayed = call(api, f"/tankers/{active_delivery['id']}", token=admin_token, method="PATCH", body={
        "status": "DELAYED",
        "scheduled_eta_hours": original_eta + 1,
    })
    require(status == 200 and delayed["status"] == "DELAYED", "Admin could not update the tanker ETA")
    status, restored_delivery = call(api, f"/tankers/{active_delivery['id']}", token=admin_token, method="PATCH", body={
        "status": "SCHEDULED",
        "scheduled_eta_hours": original_eta,
        "expected_quantity_litres": active_delivery["expected_quantity_litres"],
        "note": active_delivery["note"],
    })
    require(status == 200 and restored_delivery["status"] == "SCHEDULED", "Smoke check could not restore the seeded tanker schedule")

    before = call(api, "/water/status")[1]
    status, scenario = call(api, "/demo/scenarios/HIGH_USAGE", token=admin_token, method="POST")
    require(status == 200 and scenario.get("scenario") == "HIGH_USAGE", "Admin could not trigger the high-usage scenario")
    status, simulation = call(api, "/simulations", token=admin_token, method="POST", body={
        "tanker_delay_hours": 8,
        "tanker_quantity_litres": 10000,
        "consumption_multiplier": 1.2,
        "pump_available": True,
        "conservation_percent": 0,
    })
    require(status == 200 and simulation.get("changes_real_telemetry") is False, "What-if simulation failed or mutated live telemetry")
    status, saved_simulation = call(api, f"/simulations/{simulation['id']}", token=admin_token)
    require(status == 200 and saved_simulation.get("id") == simulation["id"], "Saved what-if simulation could not be retrieved")
    require(call(api, "/water/status")[1].get("scenario") == "HIGH_USAGE", "What-if simulation changed the active telemetry scenario")

    status, complaint = call(api, "/complaints", token=resident_token, method="POST", body={
        "title": f"Local smoke report {int(time.time())}",
        "description": "Synthetic end-to-end verification complaint.",
        "category": "LOW_PRESSURE",
    })
    require(status == 201, f"Resident complaint creation failed: {complaint}")
    complaint_id = complaint["id"]
    tiny_png = one_pixel_png()
    status, photo = upload_photo(base, complaint_id, resident_token, tiny_png)
    require(status == 201 and photo.get("photo_url"), f"Resident could not attach a complaint photo: {photo}")
    status, resident_photo = download_photo(base, complaint_id, resident_token)
    require(status == 200 and resident_photo == tiny_png, "Resident could not read their private complaint photo")
    status, admin_complaints = call(api, "/complaints", token=admin_token)
    require(status == 200 and any(item["id"] == complaint_id and item["photo_url"] for item in admin_complaints), "Admin could not see the submitted complaint and attachment")
    status, admin_photo = download_photo(base, complaint_id, admin_token)
    require(status == 200 and admin_photo == tiny_png, "Admin could not read the complaint photo")
    status, update = call(api, f"/complaints/{complaint_id}", token=admin_token, method="PATCH", body={
        "status": "ACKNOWLEDGED",
        "comment": "Smoke check acknowledged by admin.",
    })
    require(status == 200 and update.get("status") == "ACKNOWLEDGED", "Admin could not update complaint status")
    status, resident_complaints = call(api, "/complaints", token=resident_token)
    require(status == 200 and any(item["id"] == complaint_id and item["status"] == "ACKNOWLEDGED" for item in resident_complaints), "Resident did not receive the complaint update")
    call(api, f"/complaints/{complaint_id}", token=admin_token, method="PATCH", body={
        "status": "CLOSED",
        "comment": "Smoke check complete.",
    })

    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    status, event = call(api, "/maintenance", token=admin_token, method="POST", body={
        "event_type": "TANK_CLEANING",
        "title": f"Local smoke maintenance {int(time.time())}",
        "description": "Synthetic end-to-end verification notice.",
        "start_time": starts_at.isoformat(),
        "end_time": (starts_at + timedelta(hours=2)).isoformat(),
        "affected_towers": ["Tower A"],
        "severity": "INFO",
    })
    require(status == 201, f"Admin could not schedule maintenance: {event}")
    status, resident_maintenance = call(api, "/maintenance", token=resident_token)
    require(status == 200 and any(item["id"] == event["id"] for item in resident_maintenance), "Resident did not receive the tower-scoped maintenance notice")
    status, updated_event = call(api, f"/maintenance/{event['id']}", token=admin_token, method="PATCH", body={"status": "COMPLETED"})
    require(status == 200 and updated_event["status"] == "COMPLETED", "Admin could not complete maintenance")

    websocket_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/ws/societies/demo"
    with connect(websocket_url, open_timeout=5, close_timeout=2) as socket:
        socket.send(json.dumps({"token": resident_token}))
        message = json.loads(socket.recv(timeout=5))
    require(message.get("type") == "water_status" and message.get("data", {}).get("society") == "Jal Residency", "WebSocket did not publish live water status")

    call(api, "/demo/scenarios/NORMAL_DAY", token=admin_token, method="POST")
    print("PASS: backend, SQLite, and simulator health")
    print("PASS: CORS allows the local admin origin and rejects unrelated origins")
    print("PASS: resident/admin login and resident-only household data")
    print("PASS: role authorization and admin forecast")
    print("PASS: alert unread state persists independently per account")
    print("PASS: tower and flat consumption drilldown with role protection")
    print("PASS: admin anomaly review states persist and remain role protected")
    print("PASS: tanker schedule read, delay, and restoration")
    print("PASS: high-usage scenario and isolated shortage simulation")
    print("PASS: saved what-if simulation retrieval")
    print("PASS: private complaint photo upload and resident/admin access")
    print("PASS: resident complaint, admin update, resident tracking")
    print("PASS: admin maintenance scheduling and resident notice visibility")
    print("PASS: authenticated water-status WebSocket")
    print(f"Smoke check created and closed complaint #{complaint_id} in the local demo database.")


if __name__ == "__main__":
    main()
