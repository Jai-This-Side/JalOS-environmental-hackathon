# JalOS

JalOS predicts water availability for housing societies using tank telemetry, simulated flat meters, forecasting, anomaly analysis, and a deterministic water-runway engine. The resident product is a Flutter mobile app. Society staff use a separate React and TypeScript operations portal, as specified for the admin experience.

The seeded society is Jal Residency: 8 towers, 300 flats, 4 tanks, and synthetic virtual-meter readings. Tank-sensor data and household-meter data are kept as separate sources. Synthetic demo data is not real resident or sensor data.

## Run the local demo on Windows

The API and simulator can run directly on Windows with SQLite; Docker and PostgreSQL are optional for this local path.

1. From PowerShell at the project root, start the backend and simulator:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\scripts\run_local.ps1 --reset
   ```

   The script creates the local virtual environment and installs backend requirements if needed. The demo database is stored in the ignored `.local` folder. Omit `--reset` on later starts to preserve it.

2. Prepare and launch the Flutter resident app in a second terminal:

   ```powershell
   cd mobile
   flutter pub get
   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 --dart-define=WEBSOCKET_URL=ws://10.0.2.2:8000/ws/societies/demo
   ```

   `10.0.2.2` is the Android emulator address for the development computer. For a physical device, start the API with `--host 0.0.0.0`, then use the computer's LAN IP and allow the port through the local firewall. iOS Simulator can use `localhost`.

3. Optional: run the separate admin portal in a third terminal:

   ```powershell
   cd admin-web
   npm ci
   npm run dev
   ```

4. Open the API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Local-only demo credentials are printed by the startup script.

The runner accepts `--port`, `--host`, and `--reload`. Use `--reset` only when you want to delete the local SQLite demo database and reseed it.

## Docker and PostgreSQL

For the PostgreSQL-backed local stack, copy `.env.example` to `.env`, replace the placeholders with development-only values, then run:

```powershell
docker compose up --build
```

PostgreSQL is only on the internal Compose network. Flutter and the admin portal run separately. The React portal is also available through the optional Compose `web-preview` profile.

## Features

- Flutter resident app: live society water status, tank animation, runway, personal household usage, recommended range, alerts, photo-supported complaints, and profile security controls.
- React admin portal: operations dashboard, forecasts, anomalies, tower analytics, shortage simulation, tanker schedule, complaint queue, maintenance, and alerts.
- FastAPI backend: JWT authentication, role-based authorization, PostgreSQL in Compose, SQLite for a lightweight Windows demo, WebSockets, telemetry simulator, and persisted alerts.
- ML: versioned synthetic training data, chronological holdout evaluation, and a trained demand model. Metrics describe synthetic data only.

See [docs/DEMO.md](docs/DEMO.md), [docs/API.md](docs/API.md), and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Data and model limits

Households, tanks, meter readings, forecasts, and alerts in the demo are synthetic. Forecast metrics are measured on a chronological synthetic holdout and are not field accuracy. Anomaly flags mean possible abnormal usage, not a confirmed leak.

## Project status

The backend, simulator, Flutter resident app, and React admin portal are implemented, with local SQLite and PostgreSQL Compose paths, Alembic migrations, private complaint photo attachments, and an AWS Terraform/GitHub OIDC deployment path. Remaining work includes configuring the actual GitHub repository and SSH CIDR, applying AWS infrastructure after cost review, adding a domain/TLS listener, and full Android/iOS device integration verification.

No AWS resources have been created. Review [AWS architecture](docs/AWS_ARCHITECTURE.md), [deployment notes](docs/AWS_DEPLOYMENT.md), and [cost guardrails](docs/AWS_COST_GUARDRAILS.md) before provisioning.
