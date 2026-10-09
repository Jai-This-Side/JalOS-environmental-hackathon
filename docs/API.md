# API notes

FastAPI's interactive schema is available at `/docs` while the service is running.

| Method | Route | Behavior |
|---|---|---|
| GET | `/health` | Backend process health |
| GET | `/api/v1/health/components` | Backend, PostgreSQL, trained forecaster, simulator and WebSocket status |
| POST | `/api/v1/auth/login` | Exchange JSON email/password for a short-lived bearer token |
| GET | `/api/v1/auth/me` | Current user's ID, role, and optional flat ID |
| PATCH | `/api/v1/auth/password` | Change the authenticated user's password after current-password verification |
| GET | `/api/v1/water/status` | Current synthetic tank state, reserve runway, risk and recommendations |
| GET | `/api/v1/water/runway` | Deterministic reserve and empty time estimates |
| GET | `/api/v1/tanks` | Seeded tanks and latest persisted reading |
| GET | `/api/v1/tanks/{id}/history?limit=100` | Tank history, with limit capped at 1,000 |
| GET | `/api/v1/consumption/society` | Synthetic virtual-meter society rollup for 24 hours |
| GET | `/api/v1/towers` | Admin tower list with flat counts |
| GET | `/api/v1/consumption/tower/{id}` | Admin tower usage rollup with per-flat usage, budget guidance, and possible anomaly score |
| GET | `/api/v1/consumption/flat/{id}` | Admin household usage, budget guidance, and possible anomaly score |
| GET | `/api/v1/consumption/me` | Authenticated resident's own meter history, averages, anomaly check and suggested range |
| GET | `/api/v1/forecasts` | Trained synthetic seasonal-ridge forecast for 1, 6, 24 and 48 hours, with chronological holdout metrics, previous-day naive baseline, and split metadata |
| GET | `/api/v1/anomalies` | Admin peer-relative household anomaly scores from recent synthetic readings, with baseline ratio and explanation |
| PATCH | `/api/v1/anomalies/{flat_number}/review` | Admin persists `REVIEWED`, `FALSE_POSITIVE`, or `RESOLVED` feedback for a flat's anomaly signal |
| GET | `/api/v1/anomalies/reviews` | Admin lists persisted anomaly review decisions |
| POST | `/api/v1/demo/scenarios/{scenario}` | Apply a synthetic demo event |
| POST | `/api/v1/simulations` | Run and persist an isolated what-if result, returning its ID |
| GET | `/api/v1/simulations/{id}` | Admin retrieves a saved what-if result |
| GET | `/api/v1/tankers` | Admin tanker delivery schedule and arrival outcomes |
| POST | `/api/v1/tankers` | Admin replaces the current upcoming schedule; runway uses the new ETA/quantity |
| PATCH | `/api/v1/tankers/{id}` | Admin updates ETA, quantity, note, status, or cancels an upcoming delivery |
| GET | `/api/v1/alerts` | Persisted society alerts with per-account read state |
| PATCH | `/api/v1/alerts/{id}/read` | Mark a society alert read for the authenticated account |
| POST | `/api/v1/complaints` | Submit a complaint as an authenticated resident |
| POST | `/api/v1/complaints/{id}/photo` | Attach one JPEG, PNG, or WebP image up to 5 MB to the resident's complaint |
| GET | `/api/v1/complaints/{id}/photo` | Read the attachment; only its resident and society administrators may access it |
| GET | `/api/v1/complaints` | Resident's own complaints or admin society queue |
| PATCH | `/api/v1/complaints/{id}` | Admin status change and comment; creates a resident alert |
| GET | `/api/v1/complaint-clusters` | Admin sees 15-minute tower complaint spikes with current supply context |
| GET | `/api/v1/maintenance` | Maintenance schedule, tower-scoped for residents |
| POST | `/api/v1/maintenance` | Admin schedules cleaning, pump, pipeline or shutdown work and creates an alert |
| PATCH | `/api/v1/maintenance/{id}` | Admin cancels or marks maintenance complete |
| WS | `/ws/societies/{society_id}` | Two-second status updates; clients should reconnect after disconnect |

Login JSON body: `{"email":"admin@example.local","password":"..."}`. Tank management, forecasts, anomaly detail, scenario triggers, and simulations require `ADMIN` or `SUPER_ADMIN`. Alerts require a bearer token. WebSocket clients send `{"token":"<access token>"}` as their first JSON frame; the server closes connections that do not authenticate within five seconds. Residents receive only their own flat's detailed meter history; society meter history is aggregated and does not expose flat identities.

Complaint photo files are stored outside the database under `.local/uploads` for the local runner and in the persistent `uploads_data` Docker volume for Compose. The complaint response includes a private `photo_url` only when an attachment exists.

Tanker schedule creation accepts an ETA in hours from the current simulation time, a quantity in litres, and an optional note. Admin APIs support creating, editing, and canceling the next scheduled delivery.

Scenario enum values include `NORMAL_DAY`, `HIGH_USAGE`, `HEATWAVE`, `LEAK_EVENT`, `TANKER_DELAY`, `TANKER_SHORTAGE`, `PUMP_FAILURE`, `SHORTAGE_EVENT`, and `SUPPLY_RESTORED`.

Simulation body example (`tanker_delay_hours` is added to the currently scheduled ETA):

```json
{
  "tanker_delay_hours": 8,
  "tanker_quantity_litres": 12000,
  "consumption_multiplier": 1.2,
  "pump_available": true,
  "conservation_percent": 0
}
```

The simulation response explicitly includes `changes_real_telemetry: false`.
