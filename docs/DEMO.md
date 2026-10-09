# Local JalOS demo

## Start the backend and simulator

From a Windows PowerShell terminal at the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_local.ps1 --reset
```

This starts FastAPI and the synthetic telemetry loop against `.local/jalos.sqlite3`. It prints local demo account credentials. Use `--reset` only when you want to delete the local database and recreate the seeded society. The health endpoints are `/health` and `/api/v1/health/components`; the interactive API docs are `/docs`.

With the API still running, verify the resident/admin, scenario, complaint photo upload, and WebSocket flow from another terminal:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_local.py
```

## Start the resident Flutter app

In another PowerShell terminal:

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 --dart-define=WEBSOCKET_URL=ws://10.0.2.2:8000/ws/societies/demo
```

Use `10.0.2.2` from an Android emulator and `localhost` from iOS Simulator. For a physical phone, start the API with `--host 0.0.0.0` and use the computer's LAN IP. Administrators use the separate React operations portal in `admin-web/`.

## Demo story

1. Log in to the admin portal and show tank status, forecast, runway, and upcoming supply.
2. Trigger `HIGH_USAGE` and show demand/runway updates.
3. Trigger `LEAK_EVENT` and review synthetic possible-abnormal-use flags.
4. Apply `TANKER_DELAY` or reschedule a delivery.
5. Run a shortage what-if; confirm that it does not mutate live telemetry.
6. Submit a resident complaint in Flutter, then update it in the admin portal.
7. Log in to Flutter as a resident and review household usage, alerts, and complaint status.

All readings and forecast labels are synthetic. Forecast metrics come from a held-out chronological split of synthetic data. A leak event means possible abnormal usage, not a confirmed leak. The optional PostgreSQL path uses `docker compose up --build` after creating `.env` from `.env.example`.
