# JalOS Flutter resident app

This cross-platform Flutter app is for residents. Society administrators use the separate React operations portal in `admin-web/`.

## Setup

Start the backend and simulator at the repository root:

```powershell
.\scripts\run_local.ps1
```

Then prepare and run the Flutter app:

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 --dart-define=WEBSOCKET_URL=ws://10.0.2.2:8000/ws/societies/demo
```

For Android emulators, use `10.0.2.2` for the host. iOS Simulator uses `localhost`. Physical devices need the development computer's LAN address and the backend bound to `0.0.0.0`.

Open the local API docs at `http://127.0.0.1:8000/docs`. The backend prints the local demo account credentials at startup. Admins sign in to the separate portal; the Flutter app is resident-only.

## Resident screens

- Home: current society water, animated tank, runway, risk, and next supply.
- Usage: household readings, averages, recommended range, and possible anomaly notice.
- Water: society status, reserve, supply, and conservation state.
- Complaints: submit and track water-related issues.
- Alerts: society alerts and maintenance notices.
- Profile: household identity and password change.

All demo telemetry and household data are synthetic. Forecast metrics are from a chronological synthetic holdout, not sensor field data. Anomaly scores are decision support and do not confirm leaks. Complaint photo attachments are supported. Residents can change passwords; editable contact details are not yet available.
