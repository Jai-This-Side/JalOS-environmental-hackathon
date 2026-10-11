# JalOS — AI-Powered Predictive Water Management

> JalOS helps residential communities understand water availability, anticipate potential shortages, and coordinate residents and administrators through one connected platform.

**Team:** Jai Singh Bisht (Team Leader) and Tanishka Rawat (Team Member)

**Live demonstration:** http://13.206.102.148  
**API health check:** http://13.206.102.148/health  
**API base path:** `http://13.206.102.148/api/v1`

> **Security notice:** The current demo uses plain HTTP and unencrypted WebSockets. Treat it as a temporary hackathon demonstration only. Do not submit real resident information or reuse real passwords until HTTPS and WSS are configured.

---

## Table of Contents

1. [What Is JalOS?](#1-what-is-jalos)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Features](#3-goals-and-features)
4. [User Interfaces](#4-user-interfaces)
5. [How It Works](#5-how-it-works)
6. [Technology Stack](#6-technology-stack)
7. [Architecture](#7-architecture)
8. [Project Structure](#8-project-structure)
9. [Run Locally on Windows](#9-run-locally-on-windows)
10. [Docker Setup](#10-docker-setup)
11. [Using the Applications](#11-using-the-applications)
12. [Build the Android APK](#12-build-the-android-apk)
13. [API Documentation](#13-api-documentation)
14. [Forecasting and Synthetic Data](#14-forecasting-and-synthetic-data)
15. [Testing](#15-testing)
16. [AWS Deployment](#16-aws-deployment)
17. [GitHub Actions and OIDC](#17-github-actions-and-oidc)
18. [Credentials and Configuration](#18-credentials-and-configuration)
19. [AWS Services](#19-aws-services)
20. [Security](#20-security)
21. [Troubleshooting](#21-troubleshooting)
22. [AWS Cost Management](#22-aws-cost-management)
23. [Limitations and Future Work](#23-limitations-and-future-work)
24. [Team Contributions](#24-team-contributions)

---

## 1. What Is JalOS?

JalOS is a prototype water-management platform for apartment complexes and residential societies. It brings together water status, household usage guidance, demand forecasting, tanker planning, anomaly analysis, maintenance, and resident complaints.

The platform has two user-facing applications:

- **Administrator website:** A React and TypeScript operations portal for society staff.
- **Resident mobile application:** A Flutter application for residents to view water information, receive alerts, and submit complaints.

A FastAPI backend exposes the application APIs, manages authentication and role-based access, runs the simulation, and provides water-demand and water-runway calculations.

JalOS aims to move water management from reactive reporting toward informed planning. It is a decision-support prototype, not a replacement for certified physical sensors or professional water-system controls.

## 2. Problem Statement

Residential societies can face uncertainty around available water, consumption rates, tanker arrivals, and unusual usage. When this information is scattered across spreadsheets, messages, or separate systems, staff may struggle to identify potential shortages early.

JalOS brings these signals together and provides:

- An overall view of available water and reserve levels.
- Estimated time until critical reserve or depletion.
- Forecasted demand over several time horizons.
- Tanker scheduling and delivery information.
- Possible abnormal household usage for review.
- Complaint and maintenance workflows.
- Resident-facing water information and alerts.

## 3. Goals and Features

### Water Status and Runway

- Displays inventory, tank capacity, reserve level, pump state, and supply information.
- Estimates time to critical reserve and time to empty.
- Calculates runway using inventory, demand, reserve, tanker ETA and quantity, and pump availability.

### Forecasting

- Provides demand estimates over 1-, 6-, 24-, and 48-hour horizons.
- Uses a versioned seasonal ridge-regression forecasting artifact.
- Evaluates forecasts against synthetic data using chronological training, validation, and test splits.

### Tanker Planning

- Lists expected deliveries, arrival times, quantities, and status.
- Supports administrator changes to tanker schedules.
- Includes demo scenarios for tanker delay and shortage.

### Anomaly Analysis

- Scores usage that differs from household and peer-profile expectations.
- Identifies potentially unusual sustained or overnight usage.
- Provides signals for review; an anomaly does not confirm a leak.

### Resident Features

- Household usage history and guidance range.
- Water-related alerts.
- Complaint submission and tracking.
- Optional complaint photo attachments.
- Profile and account-security controls supported by the app.

### Administrator Features

- Society dashboard and tank readings.
- Forecasts and consumption analytics.
- Tower-level usage views.
- Anomaly review.
- Shortage what-if simulation.
- Tanker scheduling.
- Complaint review and status updates.
- Maintenance planning and alerts.

### Simulation

The example society, **Jal Residency**, contains eight towers, 300 flats/virtual households, and four tanks.

Scenarios include normal operation, high usage, heatwave, leak-event simulation, tanker delay, pump failure, tanker shortage, and supply restoration.

All demonstration telemetry is synthetic.

## 4. User Interfaces

### Administrator Web Portal

- Built with React, TypeScript, and Vite.
- Intended for society managers and operations staff.
- Vite normally serves the development portal at `http://localhost:5173`; it may choose another port if that one is occupied.

### Resident Mobile App

- Built with Flutter and Dart.
- Supports Android APK builds.
- API and WebSocket addresses are configured through `API_BASE_URL` and `WEBSOCKET_URL` Dart defines.

## 5. How It Works

1. The backend simulator advances the synthetic society's water state and household usage.
2. The backend calculates current water status, risk, and estimated runway.
3. The forecasting module loads a versioned model artifact to estimate future demand.
4. Anomaly and complaint-clustering logic generates review signals.
5. FastAPI supplies data to the admin portal and Flutter app through REST APIs and WebSockets.
6. SQLite is used by the lightweight local runner; PostgreSQL is used by the Docker deployment.
7. In the AWS deployment path, releases and model artifacts are stored in private S3 storage and deployed to EC2 through Systems Manager.

## 6. Technology Stack

| Layer | Technologies |
|---|---|
| Backend API | Python, FastAPI, Pydantic |
| Authentication | Password hashing, JWT bearer tokens, role-based access |
| Data layer | SQLAlchemy, Alembic, SQLite, PostgreSQL |
| Forecasting | Python, ridge regression, versioned JSON model artifact |
| Resident app | Flutter, Dart |
| Admin portal | React, TypeScript, Vite |
| Containers | Docker, Docker Compose, Nginx |
| Infrastructure as code | Terraform |
| CI/CD | GitHub Actions |
| AWS identity for CI/CD | IAM roles and GitHub OIDC |
| AWS hosting and operations | Amazon EC2, Amazon S3, Systems Manager, CloudWatch |
| Testing | Python unittest, Flutter tests, Flutter analyzer, frontend builds, Terraform validation |

## 7. Architecture

```text
                  ┌────────────────────────────┐
                  │       Resident app         │
                  │       Flutter / Dart       │
                  └──────────────┬─────────────┘
                                 │ REST / WebSocket
                                 ▼
┌────────────────────────┐  ┌──────────────────────────┐
│ Administrator website  │─▶│ FastAPI backend          │
│ React / TypeScript     │  │ Auth, water engine,       │
└────────────────────────┘  │ simulator, forecast,      │
                            │ anomalies and complaints  │
                            └─────────────┬────────────┘
                                          │
                           ┌──────────────┴─────────────┐
                           ▼                            ▼
                 ┌─────────────────┐          ┌─────────────────┐
                 │ SQLite (local)  │          │ PostgreSQL      │
                 │ demo runner     │          │ Docker / AWS    │
                 └─────────────────┘          └─────────────────┘

AWS deployment:
GitHub Actions → OIDC → AWS IAM role → private S3 release
                                    → Systems Manager
                                    → EC2 / Docker / Nginx
                                    → CloudWatch logs
```

## 8. Project Structure

```text
Hackathon Project/
├── .github/
│   └── workflows/
│       └── ci.yml
├── admin-web/                     # React + TypeScript admin portal
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI routes and simulator integration
│   │   ├── auth_api.py            # Authentication endpoints
│   │   ├── database.py            # Database setup and seeding
│   │   ├── models.py              # Database models
│   │   ├── engine.py              # Water-runway and risk logic
│   │   ├── forecasting.py         # Forecast artifact inference
│   │   ├── anomaly.py             # Usage anomaly scoring
│   │   ├── simulation.py          # Synthetic usage simulation
│   │   ├── maintenance.py         # Maintenance logic
│   │   ├── complaint_clusters.py  # Complaint clustering
│   │   └── test_engine.py         # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── deploy/                        # Nginx and deployment configuration
├── docs/                          # API, architecture, and AWS docs
├── ml/
│   ├── datasets/                  # Synthetic training datasets
│   ├── artifacts/                 # Versioned model artifacts
│   └── train_forecast.py          # Dataset generation and training
├── mobile/                        # Flutter resident application
├── scripts/
│   ├── run_local.ps1              # Windows local launcher
│   ├── run_local.py
│   └── smoke_local.py
├── terraform/                     # AWS infrastructure definitions
├── docker-compose.yml
├── docker-compose.production.yml
├── .env.example
└── README.md
```

## 9. Run Locally on Windows

### Prerequisites

Install the tools required for the components you intend to run:

- Git.
- A Python version compatible with `backend/requirements.txt`.
- Node.js and npm for the admin portal.
- Flutter SDK and Android tooling for the mobile app.
- Docker Desktop for the Docker/PostgreSQL workflow.
- AWS CLI and Terraform only for AWS provisioning.

### 9.1 Start the Backend

Open PowerShell in the project root:

```powershell
cd "C:\Hackathon Project"
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_local.ps1
```

The script prepares the local Python environment as needed and starts the backend and simulator using SQLite.

To reset the local demo database:

```powershell
.\scripts\run_local.ps1 --reset
```

**Warning:** `--reset` deletes local demo records. Do not use it if you need to preserve test data.

To see the available launcher options:

```powershell
.\.venv\Scripts\python.exe scripts\run_local.py --help
```

### 9.2 Verify the Backend

- Health check: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs
- Component health: http://127.0.0.1:8000/api/v1/health/components

The local startup script prints local demo credentials. These may differ from the AWS credentials.

### 9.3 Start the Admin Website

Open a second PowerShell terminal:

```powershell
cd "C:\Hackathon Project\admin-web"
npm ci
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
$env:VITE_WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/societies/demo"
npm run dev
```

Open the URL printed by Vite. If port 5173 is occupied, Vite may choose 5174.

### 9.4 Start the Flutter App

Open a third terminal:

```powershell
cd "C:\Hackathon Project\mobile"
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 --dart-define=WEBSOCKET_URL=ws://10.0.2.2:8000/ws/societies/demo
```

`10.0.2.2` is the Android emulator's special address for reaching the host computer.

For a physical phone, use the computer's LAN IP, bind the backend to a reachable interface, and ensure the Windows firewall allows the development connection. Do not use `10.0.2.2` on a physical phone.

## 10. Docker Setup

Install and start Docker Desktop.

Create a development environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace placeholders with development-only values. Use a strong database password and JWT secret. Never commit `.env`.

Start the stack:

```powershell
docker compose up --build
```

Verify the backend at http://127.0.0.1:8000/health.

Stop the stack with `Ctrl+C`. To stop detached services:

```powershell
docker compose down
```

The Docker setup uses PostgreSQL and a persistent named volume. Do not run `docker compose down -v` unless you intend to delete persistent database data.

## 11. Using the Applications

### Resident Flow

1. Open the Flutter app.
2. Sign in with a resident account for the current environment.
3. Review water status and household usage guidance.
4. Review water alerts.
5. Submit a complaint, optionally including a photo.
6. Track the complaint status.

### Administrator Flow

1. Open the React operations portal.
2. Sign in with an administrator account.
3. Review water status, tank readings, forecasts, and runway.
4. Review anomalies and tower usage.
5. Try a shortage what-if scenario.
6. Review or schedule tanker deliveries.
7. Review complaints and update their status.
8. Review maintenance and alerts.

### Suggested Hackathon Demo

1. Show the administrator dashboard and current water status.
2. Explain demand forecasting and water runway.
3. Trigger a `HIGH_USAGE` scenario and show the impact on runway.
4. Trigger a `TANKER_DELAY` scenario and explain the supply-planning impact.
5. Submit a resident complaint and show it in the administrator portal.
6. Explain that telemetry is synthetic and the model needs real-world validation.

## 12. Build the Android APK

From PowerShell:

```powershell
cd "C:\Hackathon Project\mobile"
flutter doctor
flutter pub get
```

### Build for the Current Demo

The current public demo uses HTTP and an unencrypted WebSocket. This build is for temporary synthetic hackathon demonstrations only:

```powershell
flutter build apk --release `
  --dart-define=API_BASE_URL=http://13.206.102.148/api/v1 `
  --dart-define=WEBSOCKET_URL=ws://13.206.102.148/ws/societies/demo
```

The APK should be generated at:

```text
mobile\build\app\outputs\flutter-apk\app-release.apk
```

Install the newly built APK on the Android device. Rebuilding the source does not update an already-installed app.

For production, configure a domain and TLS certificate, use HTTPS/WSS, update Android networking configuration if necessary, and rebuild with secure URLs.

## 13. API Documentation

FastAPI exposes interactive API documentation at `/docs`.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Basic health check |
| `GET` | `/api/v1/health/components` | Component health |
| `POST` | `/api/v1/auth/login` | Authenticate and receive a token |
| `GET` | `/api/v1/auth/me` | Current authenticated user |
| `GET` | `/api/v1/water/status` | Water status and runway |
| `GET` | `/api/v1/tanks` | Tank readings |
| `GET` | `/api/v1/forecasts` | Demand forecasts |
| `GET` | `/api/v1/consumption/society` | Society consumption history |
| `GET` | `/api/v1/anomalies` | Usage anomaly signals |
| `GET` | `/api/v1/towers` | Tower summaries |
| `GET` | `/api/v1/complaints` | Authorized complaints |
| `POST` | `/api/v1/complaints` | Create a complaint |
| `GET` | `/api/v1/alerts` | Authorized alerts |
| `GET` | `/api/v1/tankers` | Tanker deliveries |
| `GET` | `/api/v1/maintenance` | Maintenance records |

Use the live OpenAPI docs for exact request bodies, response schemas, and authorization requirements. Administrator operations require an administrator token where specified. Residents should only access data permitted for their account.

The demo WebSocket endpoint is `/ws/societies/demo`, using the authentication mechanism implemented by the application.

## 14. Forecasting and Synthetic Data

The training pipeline is implemented in `ml/train_forecast.py`, and inference is implemented in `backend/app/forecasting.py`.

To retrain the model from the project root:

```powershell
python ml/train_forecast.py
```

The pipeline generates synthetic observations, fits a seasonal ridge-regression model, evaluates a chronological holdout, and writes a JSON artifact under `ml/artifacts/`.

Keep the following consistent when changing the model:

- Dataset filename and version.
- Output artifact filename.
- Model version and dataset metadata.
- Artifact path in `backend/app/forecasting.py`.
- Tests that assert model metadata and split sizes.
- GitHub Actions artifact upload paths.
- Deployment scripts and S3 model keys.

Do not change only a test's expected row count if the implementation and deployment still use an older artifact.

### Data Boundaries

- Household usage, tank readings, and demo events are synthetic.
- Forecast metrics measure performance against synthetic data, not real field data.
- An anomaly is not proof of a leak.
- A simulated shortage is not evidence of a real supply interruption.
- Real deployments require sensor calibration, privacy controls, and field validation.

## 15. Testing

### Backend Unit Tests

From the repository root:

```powershell
python -m unittest discover -s backend/app -v
```

### Local Smoke Test

Start the backend first, then run:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_local.py
```

### Admin Portal

```powershell
cd admin-web
npm ci
npm run build
```

### Flutter

```powershell
cd mobile
flutter pub get
flutter analyze --no-pub
flutter test --no-pub
```

### Terraform

```powershell
cd terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

Run tests before pushing. If tests fail after changing the forecasting dataset or artifact, align the implementation, metadata, workflow, and tests.

## 16. AWS Deployment

The project includes Terraform and deployment configuration for a small EC2-based demo environment.

The intended deployment includes:

- Ubuntu EC2 instance.
- Docker Compose services behind Nginx.
- Private S3 storage for releases and model artifacts.
- EC2 IAM role for Systems Manager, S3, SSM parameter access, and CloudWatch logs.
- Systems Manager SecureString runtime configuration.
- CloudWatch log group.
- GitHub OIDC role restricted to the configured repository and branch.
- Deployment script and health-check step.

### Before Provisioning

1. Confirm the correct AWS account and region. The project configuration uses `ap-south-1`.
2. Review the AWS Billing dashboard and set a budget alert.
3. Review `terraform/terraform.tfvars.example`.
4. Create `terraform/terraform.tfvars` with a unique S3 bucket name, GitHub repository, branch, and restricted SSH CIDR if needed.
5. Never commit Terraform variable files, state files, plans containing secrets, or runtime configuration.
6. Review the plan before applying.

Example:

```powershell
cd "C:\Hackathon Project\terraform"
Copy-Item terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and replace all example values.
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

Only after reviewing the plan and expected charges:

```powershell
terraform apply
```

Terraform may store generated credentials in state and in an encrypted SSM parameter. Protect state and backups as secrets.

### Inspect Deployment Outputs

If the local Terraform state corresponds to the active deployment:

```powershell
terraform output
terraform output -raw health_url
terraform output -raw instance_id
terraform output -raw s3_bucket
terraform output -raw github_deploy_role_arn
```

Outputs depend on the actual state. Do not assume a local state file describes the active AWS account.

## 17. GitHub Actions and OIDC

The GitHub Actions workflow runs checks for the backend, admin portal, Flutter app, and Terraform. Deployment is conditional on configured repository variables and the branch condition in the workflow.

Configure these repository variables under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Meaning |
|---|---|
| `AWS_ROLE_ARN` | GitHub OIDC deployment role ARN |
| `AWS_REGION` | AWS region, usually `ap-south-1` |
| `JALOS_ENVIRONMENT` | Terraform environment name |
| `JALOS_S3_BUCKET` | Private S3 release bucket |
| `JALOS_INSTANCE_ID` | EC2 instance ID |
| `JALOS_HEALTH_URL` | Public health-check URL |

These are resource identifiers, not AWS access keys. The workflow should use OIDC to obtain short-lived credentials. Do not add long-lived AWS access keys to the repository.

After pushing to the configured branch:

1. Open GitHub → repository → **Actions**.
2. Open the latest workflow run.
3. Check each validation and build job.
4. If deployment runs, inspect S3 upload and Systems Manager steps.
5. Confirm the health-check step passes.
6. If deployment is skipped, check the branch condition and required variables.

A failed validation job blocks deployment.

## 18. Credentials and Configuration

### Local Development

- `.env.example` documents development settings.
- Copy it to `.env` for the Docker Compose workflow.
- Replace placeholders with development-only values.
- The local runner prints its own demo credentials.
- Do not assume every local script automatically loads `.env`.

### AWS Runtime Configuration

The Terraform template creates random database, JWT, administrator, and resident demo passwords. The intended SSM parameter path is:

```text
/jalos/<environment>/runtime-environment
```

For the `hackathon` environment:

```text
/jalos/hackathon/runtime-environment
```

The parameter is a `SecureString`. The EC2 role needs appropriate IAM permissions to retrieve it.

If Terraform state corresponds to the active deployment, outputs may include demo credentials:

```powershell
terraform output -raw demo_admin_email
terraform output -raw demo_admin_password
terraform output -raw demo_resident_email
terraform output -raw demo_resident_password
```

**Caution:** These commands can reveal secrets. Run them privately and never paste their output into public issues, screenshots, repositories, or chat. Terraform's original password may no longer match a password changed directly in the database. Password hashes cannot be reversed; reset the account through an authorized process if necessary.

Never hardcode production passwords in Flutter, source files, GitHub commits, or this README. Use separate credentials for local development and production.

## 19. AWS Services

| Service | Role |
|---|---|
| Amazon EC2 | Runs the application containers |
| Amazon S3 | Private release and model artifact storage |
| AWS Systems Manager Parameter Store | Encrypted runtime configuration |
| AWS Systems Manager Run Command | Remote deployment orchestration |
| AWS IAM | Least-privilege permissions |
| GitHub OIDC with AWS STS | Short-lived CI/CD credentials |
| Amazon CloudWatch Logs | Application/container logs |
| Terraform | Reproducible infrastructure definitions |

Verify the actual AWS console and Terraform state before claiming that every resource is deployed.

## 20. Security

- Use HTTPS/WSS for public or production traffic.
- Do not use real resident data while the public endpoint is HTTP-only.
- Never commit `.env`, Terraform state, variable files, private keys, keystores, passwords, JWT secrets, or decrypted SSM values.
- Keep database and development ports private.
- Restrict SSH access to a trusted IP `/32`; avoid `0.0.0.0/0` for SSH.
- Use separate local and production credentials.
- Use OIDC instead of long-lived AWS access keys.
- Avoid writing passwords, JWTs, or personal data to logs.
- Configure backups, recovery, monitoring, and access reviews before production use.
- A hackathon demo is not a security-reviewed production system.

## 21. Troubleshooting

### App Cannot Connect to the API

- Confirm `/health` works.
- Check the APK's `API_BASE_URL` and `WEBSOCKET_URL`; source changes do not update an existing APK.
- For a local Android emulator, use `10.0.2.2`.
- For a physical phone, use the computer's reachable LAN IP.
- Check network rules and firewall settings.
- Ensure HTTP/HTTPS and `ws://`/`wss://` are configured consistently.

### Admin Website Says "Waiting for JalOS API"

- Verify the backend health URL.
- Inspect browser developer tools for failed requests or CORS errors.
- Check `VITE_API_BASE_URL` and `VITE_WEBSOCKET_URL`.
- Inspect backend and Nginx logs.

### Forecast Endpoint Returns HTTP 500

- Confirm the model artifact exists in `ml/artifacts/`.
- Verify the artifact path in `backend/app/forecasting.py`.
- Check artifact metadata, tests, and workflow upload paths.
- Inspect the backend logs for the exception.

### GitHub Actions Deployment Is Skipped

- Verify the push targets the configured branch.
- Verify all six repository variables are set.
- Check the OIDC trust policy repository and branch.
- Confirm the EC2 instance is online and managed by Systems Manager.

### Systems Manager Cannot Reach EC2

- Confirm the SSM Agent is running.
- Confirm the EC2 instance has an IAM instance profile.
- Verify outbound connectivity to Systems Manager endpoints.
- Check IAM permissions and AWS region/account.

### Tank Totals Differ Between Endpoints

- Fetch the endpoints again and compare timestamps.
- The simulator clock advances faster than real time, so separate requests may observe different moments.
- If timestamps align but totals differ, investigate stale readings or inconsistent inventory snapshots.

### Demo Login Does Not Work

- Confirm the environment and account being used.
- Local credentials differ from generated AWS credentials.
- Terraform's generated password may be stale if the database password changed.
- Reset the password through an authorized administrative process.

## 22. AWS Cost Management

The demo architecture avoids larger services such as EKS, ECS/Fargate, NAT Gateway, load balancers, and RDS in its small setup. This does **not** guarantee a zero-cost deployment.

Potential charges include:

- EC2 runtime.
- EBS storage, including while an instance is stopped.
- Public IPv4 address.
- S3 storage, requests, and retained object versions.
- CloudWatch log ingestion and storage.
- Data transfer.

Review current regional prices, account Free Tier eligibility, and the AWS Billing dashboard before provisioning. Set a budget alert. Stop the instance when idle, but remember that some storage and address charges may continue.

Before destroying infrastructure, back up needed data, inspect S3 objects and versions, and review:

```powershell
terraform plan -destroy
```

Do not delete resources blindly.

## 23. Limitations and Future Work

- Replace synthetic telemetry with calibrated real tank sensors and privacy-protected meter data.
- Evaluate forecasts on real-world time-series data.
- Validate anomaly thresholds against known incidents.
- Configure HTTPS/WSS and a domain.
- Complete end-to-end Android and iOS testing.
- Improve password recovery and account provisioning.
- Add production-grade monitoring, backups, restore testing, and runbooks.
- Improve deployment rollback and release observability.
- Review data retention, access control, privacy, and applicable compliance requirements.
- Verify actual AWS resources and costs before wider distribution.

## 24. Team Contributions

### Jai Singh Bisht — Team Leader

- Backend architecture and water-management logic using Python and FastAPI.
- Water runway and supply-planning calculations.
- Terraform/AWS infrastructure work, including EC2, IAM, and runtime configuration.
- Technical integration and overall system coordination.

### Tanishka Rawat — Team Member

- Resident-facing and administrator-facing application work, according to the actual assigned responsibilities.
- Application integration and deployment workflow contributions, where applicable.
- Shared testing, demo preparation, and presentation.

Update these contribution statements to reflect the team's actual division of work before submission.

---

## Acknowledgement

JalOS is a hackathon prototype exploring predictive water management for residential communities. All current demonstration data is synthetic unless explicitly stated otherwise.