# JalOS architecture (prototype)

```text
Synthetic household profiles --\
                                +--> FastAPI simulator --> PostgreSQL / local SQLite
Tank state + tanker schedule --/           |
                                            +--> WebSocket --> Flutter resident app
                                            +--> REST -------> Flutter resident app
                                            +--> REST -------> React admin portal
```

The tank readings and virtual flat-meter readings are different streams. Tank readings model aggregate society inventory, inflow, outflow, and pump state. The virtual meter simulator creates per-flat usage from household profiles; a tank sensor cannot identify a flat's usage.

The seeded Jal Residency configuration has eight towers, 300 synthetic flats, 300 virtual meters, and four tanks. Current telemetry, profiles, forecasts, scenario events, and anomalies are synthetic prototype data. The seasonal ridge-regression forecast is trained and evaluated chronologically against held-out outputs from the same synthetic generator; it has not been validated against real meters. Runway is deterministic and considers inventory, reserve, demand, tanker ETA/quantity, and pump availability. The anomaly endpoint combines household-profile ratios with a robust peer median/MAD score over recent readings and explains possible overnight or single-sample spikes. Complaint clusters count reports by tower within 15 minutes and pair pressure/no-water reports with society tank risk or pump state before suggesting a possible incident. Both are decision support over synthetic or user-reported data, not confirmed leak or pressure detection.

The local PowerShell runner starts FastAPI and the simulator against SQLite for a lightweight demo. Docker Compose runs PostgreSQL and FastAPI; Flutter and the React admin portal connect separately. PostgreSQL readings and simulation/alert records persist in the named `postgres_data` volume. Alembic creates and upgrades the schema at application startup, and legacy demo databases are stamped only when all current model tables exist. Simulator clock speed defaults to five simulated minutes per real second and can be changed with `JALOS_SIM_MINUTES_PER_TICK` and `JALOS_SIM_TICK_SECONDS`. Risk bands are deterministic prototype thresholds: critical at 6 hours or less to reserve, high at 12 hours or less, moderate at 24 hours or less, low at 48 hours or less, and normal above 48 hours.

## Boundaries

JWT login uses scrypt password hashes and short-lived HS256 tokens. Admin-only operations require an admin role, and alert/WebSocket endpoints require an authenticated user. Residents can view their own meter history, create and track their own complaints, attach private photos, and receive a guidance range. Admins can update complaint status, leave an update comment, and manage tankers and maintenance from the separate React portal. Editable resident contact details, TLS production hardening, live GitHub OIDC deployment, and full Flutter device verification remain outstanding.
