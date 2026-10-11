# JalOS

JalOS is an intelligent water management platform designed for housing societies. It uses water telemetry, simulated household meter readings, demand forecasting, anomaly analysis, and water-runway calculations to help societies understand water availability and make proactive decisions.

## Current Project Focus

The current implementation focuses on the backend and data intelligence layer of JalOS.

The system uses a seeded housing society with synthetic telemetry and household consumption data for development and demonstration purposes.

All demonstration data is synthetic and does not represent real resident, household, or sensor data.

## Core Capabilities

- Water telemetry processing
- Household water-consumption analysis
- Water availability and runway calculations
- Demand forecasting
- Abnormal consumption detection
- Synthetic telemetry simulation
- Authentication and role-based authorization
- REST APIs for water-management operations
- Database persistence with SQLite and PostgreSQL support
- Database migrations using Alembic
- Local development and Docker-based development

## Architecture

The current backend is built with:

- **FastAPI** — REST API and application server
- **SQLAlchemy** — database access and models
- **Alembic** — database migrations
- **SQLite** — lightweight local development database
- **PostgreSQL** — containerized development database
- **JWT authentication** — authentication and authorization
- **Python** — backend and data-processing logic

The ML/data intelligence layer provides:

- Synthetic water-consumption data
- Demand forecasting
- Versioned model artifacts
- Forecast training utilities
- Chronological evaluation on synthetic data
- Consumption anomaly analysis

## Project Structure

```text
JalOS/
│
├── backend/
│   ├── app/
│   │   ├── anomaly.py
│   │   ├── attachments.py
│   │   ├── auth_api.py
│   │   ├── budgets.py
│   │   ├── complaint_clusters.py
│   │   ├── database.py
│   │   ├── engine.py
│   │   ├── forecasting.py
│   │   ├── main.py
│   │   ├── maintenance.py
│   │   ├── migrations.py
│   │   ├── models.py
│   │   ├── passwords.py
│   │   ├── security.py
│   │   └── simulation.py
│   │
│   ├── alembic/
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
│
├── ml/
│   ├── artifacts/
│   │   └── water-demand-ridge-v1.json
│   ├── datasets/
│   │   └── synthetic-society-15m-v1.csv
│   ├── train_forecast.py
│   └── README.md
│
├── scripts/
│   ├── run_local.ps1
│   ├── run_local.py
│   ├── smoke_legacy_migration.py
│   └── smoke_local.py
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

## Local Development on Windows

### Requirements

- Python 3.11+
- PowerShell
- Docker Desktop (optional)

### Run the Local Demo

From PowerShell at the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_local.ps1 --reset
```

The script creates the local Python virtual environment and installs the backend requirements if necessary.

The local SQLite database is stored in the ignored `.local` directory.

Use `--reset` when you want to remove the existing local demo database and reseed it.

For subsequent runs, start the application without `--reset` to preserve the existing local database.

### API Documentation

Once the backend is running, FastAPI's interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

The local startup script prints the development/demo credentials required for local testing.

## Docker and PostgreSQL

JalOS also supports a PostgreSQL-backed development environment using Docker Compose.

Create a local environment file from the provided example:

```powershell
Copy-Item .env.example .env
```

Replace the development placeholders in `.env` with appropriate local values.

Then start the stack:

```powershell
docker compose up --build
```

PostgreSQL runs inside the Docker Compose network and is intended for local development.

## Machine Learning

The ML component currently uses synthetic water-consumption data for demand forecasting.

The training data and model artifacts are versioned inside the repository:

```text
ml/
├── datasets/
│   └── synthetic-society-15m-v1.csv
├── artifacts/
│   └── water-demand-ridge-v1.json
└── train_forecast.py
```

The forecasting pipeline uses chronological holdout evaluation so that future observations are not used to train the model for earlier observations.

Model metrics describe performance on synthetic development data only and should not be interpreted as real-world field accuracy.

## Data and Model Limitations

The current demonstration environment uses synthetic data for:

- Households
- Water tanks
- Meter readings
- Water consumption
- Forecasting
- Alerts
- Telemetry

No real resident or household data is included.

An anomaly flag represents potentially abnormal consumption and does not by itself confirm a leak, meter failure, or other physical problem.

Forecast performance is based on synthetic development data and requires validation against real-world measurements before operational deployment.

## Database

The backend supports two development configurations:

### SQLite

Used by the lightweight Windows local-demo workflow.

The database is created under the ignored `.local` directory.

### PostgreSQL

Used by the Docker Compose development environment.

Database schema changes are managed through Alembic migrations located under:

```text
backend/alembic/versions/
```

## Testing and Local Checks

The repository includes local smoke-test utilities under:

```text
scripts/
```

Run the local smoke checks with the corresponding project scripts after starting the backend.

## Development Status

The current repository contains the core JalOS backend, database layer, telemetry processing, forecasting, anomaly analysis, water-runway logic, ML training utilities, synthetic development data, and local development configuration.

Additional application interfaces, deployment infrastructure, and cloud integrations will be integrated as development progresses.

## Environmental Hackathon

JalOS is being developed as an environmental technology solution focused on improving water availability awareness and enabling proactive water-management decisions for housing societies.

The project is designed around the principle of moving from raw water-consumption information to actionable decisions.

## License

This project is developed for educational, experimental, and hackathon purposes.