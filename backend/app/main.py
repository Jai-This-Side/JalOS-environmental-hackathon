from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
import asyncio
import os
import json
from fastapi import HTTPException, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from app.engine import runway, risk_for
from app.database import SessionLocal, initialize_database
from app.models import Alert, AlertRead, AnomalyReview, Flat, Tower, Meter, Tank, TankReading, MeterReading, SimulationRun, Society, Complaint, ComplaintUpdate, TankerDelivery, MaintenanceEvent
from app.simulation import TYPES, generate_intervals, seeded_households
from app.simulation import Household, interval_consumption
from app.anomaly import score_usage_anomaly, sustained_usage_anomaly
from app.budgets import recommended_range
from app.maintenance import EVENT_TYPES, SEVERITIES, validate_affected_towers, validate_maintenance_window
from app.complaint_clusters import cluster_complaints
from app.forecasting import forecast_horizons
from app.auth_api import router as auth_router
from app.security import current_user, require_admin, user_from_token
from app.models import User
from app.attachments import attachment_path, store_complaint_photo

app = FastAPI(title="JalOS Water Operations API", version="0.1.0", description="Synthetic prototype data")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"], allow_credentials=False)
app.include_router(auth_router)

class Scenario(str, Enum):
    NORMAL_DAY = "NORMAL_DAY"
    HIGH_USAGE = "HIGH_USAGE"
    HEATWAVE = "HEATWAVE"
    LEAK_EVENT = "LEAK_EVENT"
    TANKER_DELAY = "TANKER_DELAY"
    TANKER_SHORTAGE = "TANKER_SHORTAGE"
    PUMP_FAILURE = "PUMP_FAILURE"
    SHORTAGE_EVENT = "SHORTAGE_EVENT"
    SUPPLY_RESTORED = "SUPPLY_RESTORED"

class SimulationInput(BaseModel):
    tanker_delay_hours: float = Field(0, ge=0, le=168, description="Additional delay to add to the currently scheduled delivery ETA")
    tanker_quantity_litres: float = Field(12000, ge=0)
    consumption_multiplier: float = Field(1, ge=0.1, le=5)
    pump_available: bool = True
    conservation_percent: float = Field(0, ge=0, le=80)

class ComplaintInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    category: str = Field(pattern="^(WATER_NOT_AVAILABLE|LOW_PRESSURE|WATER_QUALITY|LEAKAGE|SUPPLY_DELAY|TANK_ISSUE|OTHER)$")

class ComplaintStatusUpdate(BaseModel):
    status: str = Field(pattern="^(OPEN|ACKNOWLEDGED|IN_PROGRESS|RESOLVED|CLOSED)$")
    comment: str = Field(min_length=2, max_length=2000)

EVENT_TYPE_PATTERN = "^(" + "|".join(sorted(EVENT_TYPES)) + ")$"
SEVERITY_PATTERN = "^(" + "|".join(sorted(SEVERITIES)) + ")$"

class MaintenanceInput(BaseModel):
    event_type: str = Field(pattern=EVENT_TYPE_PATTERN)
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=2000)
    start_time: datetime
    end_time: datetime
    affected_towers: list[str] = Field(default_factory=list, max_length=8)
    severity: str = Field(default="INFO", pattern=SEVERITY_PATTERN)

    @model_validator(mode="after")
    def validate_window_and_scope(self):
        validate_maintenance_window(self.start_time, self.end_time)
        validate_affected_towers(self.affected_towers)
        return self

class MaintenanceStatusInput(BaseModel):
    status: str = Field(pattern="^(CANCELLED|COMPLETED)$")

class AnomalyReviewInput(BaseModel):
    status: str = Field(pattern="^(REVIEWED|FALSE_POSITIVE|RESOLVED)$")
    comment: str = Field(default="", max_length=1000)

def _admin_flat_usage(flats: list[Flat], daily_rows: list[tuple[int, Any, float]]) -> list[dict[str, Any]]:
    today = state.simulated_at.date()
    daily_by_flat: dict[int, dict[str, float]] = {flat.id: {} for flat in flats}
    for flat_id, day, litres in daily_rows:
        daily_by_flat.setdefault(flat_id, {})[str(day)] = float(litres)
    baselines = {flat.id: float(TYPES[flat.household_type][1]) for flat in flats}
    peer_ratios = []
    for flat in flats:
        days = daily_by_flat.get(flat.id, {})
        seven_day = [value for day, value in days.items() if 0 <= (today - datetime.fromisoformat(day).date()).days < 7]
        if seven_day and baselines[flat.id] > 0:
            peer_ratios.append(sum(seven_day) / len(seven_day) / baselines[flat.id])

    risk = status()["runway"]["risk"]
    result = []
    for flat in flats:
        days = daily_by_flat.get(flat.id, {})
        seven_day = [value for day, value in days.items() if 0 <= (today - datetime.fromisoformat(day).date()).days < 7]
        thirty_day = [value for day, value in days.items() if 0 <= (today - datetime.fromisoformat(day).date()).days < 30]
        baseline = baselines[flat.id]
        seven_average = sum(seven_day) / len(seven_day) if seven_day else None
        thirty_average = sum(thirty_day) / len(thirty_day) if thirty_day else None
        anomaly = score_usage_anomaly(
            (seven_average or 0) * max(len(seven_day), 1),
            baseline * max(len(seven_day), 1),
            peer_ratios,
        ) if seven_average is not None and peer_ratios else None
        result.append({
            "flat_id": flat.id,
            "flat_number": flat.flat_number,
            "today_litres": round(days.get(today.isoformat(), 0)),
            "seven_day_average_litres": round(seven_average) if seven_average is not None else None,
            "thirty_day_average_litres": round(thirty_average) if thirty_average is not None else None,
            "household_baseline_litres_per_day": round(baseline),
            "recommended_range_litres_per_day": recommended_range(baseline, risk),
            "anomaly_score": anomaly["score"] if anomaly else None,
            "anomaly_status": anomaly["severity"] if anomaly else "NORMAL",
        })
    return result

class TankerInput(BaseModel):
    scheduled_eta_hours: float = Field(ge=0, le=720)
    expected_quantity_litres: float = Field(gt=0, le=1_000_000)
    note: str = Field(default="", max_length=500)

class TankerUpdateInput(BaseModel):
    status: str = Field(pattern="^(SCHEDULED|DELAYED|CANCELLED)$")
    scheduled_eta_hours: float | None = Field(default=None, ge=0, le=720)
    expected_quantity_litres: float | None = Field(default=None, gt=0, le=1_000_000)
    note: str | None = Field(default=None, max_length=500)

class DemoState:
    capacity = 300_000.0
    inventory = 187_400.0
    daily_demand = sum(TYPES[home.household_type][1] for home in seeded_households())
    reserve = 45_000.0
    scenario = Scenario.NORMAL_DAY
    tanker_eta_hours = 12.0
    tanker_quantity_litres = 12_000.0
    tanker_id: int | None = None
    pump_available = True
    inflow_litres_per_minute = 0.0
    outflow_litres_per_minute = 0.0
    simulated_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    alerts: list[dict[str, Any]] = []
    last_risk: str | None = None

state = DemoState()
simulator_task: asyncio.Task | None = None
SIM_MINUTES_PER_TICK = max(1, int(os.getenv("JALOS_SIM_MINUTES_PER_TICK", "5")))

def recommendations(risk: str) -> list[str]:
    return {
        "NORMAL": ["Continue normal monitoring."],
        "LOW": ["Confirm the upcoming tanker delivery."],
        "MODERATE": ["Notify residents about voluntary conservation.", "Confirm the upcoming tanker delivery.", "Review active consumption anomalies."],
        "HIGH": ["Notify residents.", "Suspend non-essential irrigation.", "Confirm tanker delivery and review anomalies."],
        "CRITICAL": ["Activate emergency conservation mode.", "Prioritize essential consumption.", "Confirm alternate supply immediately."],
    }[risk]

def status() -> dict[str, Any]:
    forecast_demand = state.daily_demand * (1.15 if state.scenario == Scenario.HIGH_USAGE else 1.22 if state.scenario == Scenario.HEATWAVE else 1.0)
    if state.scenario == Scenario.LEAK_EVENT: forecast_demand += 5_184
    delivery = state.tanker_quantity_litres if state.pump_available else 0
    run = runway(state.inventory, forecast_demand, state.reserve, state.tanker_eta_hours, delivery, capacity=state.capacity)
    return {"society": "Jal Residency", "synthetic_prototype_data": True, "observed_at": state.simulated_at.isoformat(), "inventory_litres": round(state.inventory), "capacity_litres": state.capacity, "critical_reserve_litres": state.reserve, "next_tanker_quantity_litres": state.tanker_quantity_litres, "level_percent": round(state.inventory / state.capacity * 100, 1), "inflow_litres_per_minute": round(state.inflow_litres_per_minute, 2), "outflow_litres_per_minute": round(state.outflow_litres_per_minute, 2), "pump_state": "ON" if state.pump_available else "OFF", "demand_litres_per_day": round(forecast_demand), "scenario": state.scenario.value, "tanker_eta_hours": None if state.tanker_eta_hours >= 1e8 else state.tanker_eta_hours, "runway": run, "recommendations": recommendations(run["risk"])}

def store_alert(kind: str, level: str, message: str):
    alert = {"type": kind, "level": level, "message": message, "created_at": datetime.now(timezone.utc).isoformat()}
    state.alerts.insert(0, alert)
    with SessionLocal.begin() as session:
        session.add(Alert(society_id=1, kind=kind, level=level, message=message))

async def simulator_loop():
    """Advance five simulated minutes per configured real-time tick."""
    tick_seconds = max(0.2, float(os.getenv("JALOS_SIM_TICK_SECONDS", "1")))
    while True:
        demand = state.daily_demand * (1.15 if state.scenario == Scenario.HIGH_USAGE else 1.22 if state.scenario == Scenario.HEATWAVE else 1.0)
        if state.scenario == Scenario.LEAK_EVENT: demand += 5_184
        step_demand = demand * SIM_MINUTES_PER_TICK / 1440
        state.outflow_litres_per_minute = step_demand / SIM_MINUTES_PER_TICK
        state.inflow_litres_per_minute = 0.0
        state.inventory = max(0.0, state.inventory - step_demand)
        state.tanker_eta_hours = max(0.0, state.tanker_eta_hours - SIM_MINUTES_PER_TICK / 60)
        if state.tanker_eta_hours == 0 and state.pump_available:
            delivered = min(state.tanker_quantity_litres, state.capacity - state.inventory)
            state.inventory += delivered
            with SessionLocal.begin() as session:
                current_delivery = session.get(TankerDelivery, state.tanker_id) if state.tanker_id else None
                if current_delivery is not None:
                    current_delivery.status = "COMPLETED"
                    current_delivery.actual_arrival = state.simulated_at
                    current_delivery.actual_quantity_litres = delivered
                next_delivery = TankerDelivery(society_id=1, scheduled_arrival=state.simulated_at + timedelta(hours=24), expected_quantity_litres=12_000.0, status="SCHEDULED", note="Synthetic recurring supply")
                session.add(next_delivery)
                session.flush()
                state.tanker_id = next_delivery.id
                state.tanker_quantity_litres = next_delivery.expected_quantity_litres
                state.tanker_eta_hours = 24.0
            store_alert("TANKER_ARRIVAL", "INFO", f"Synthetic tanker delivered {round(delivered)} L")
        new_risk = status()["runway"]["risk"]
        risk_order = {"NORMAL": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}
        if state.last_risk is not None and risk_order[new_risk] > risk_order[state.last_risk]:
            alert_level = {"LOW": "LOW", "MODERATE": "MEDIUM", "HIGH": "HIGH", "CRITICAL": "CRITICAL"}[new_risk]
            store_alert("SHORTAGE_WARNING", alert_level, f"Water reserve risk increased to {new_risk}; review runway and tanker schedule.")
        state.last_risk = new_risk
        persist_telemetry()
        state.simulated_at += timedelta(minutes=SIM_MINUTES_PER_TICK)
        await asyncio.sleep(tick_seconds)

def persist_telemetry():
    """Persist tank sensor records and virtual flat-meter records separately."""
    now = state.simulated_at
    event = "HIGH_USAGE" if state.scenario == Scenario.HIGH_USAGE else "HEATWAVE" if state.scenario == Scenario.HEATWAVE else "LEAK_EVENT" if state.scenario == Scenario.LEAK_EVENT else "NORMAL_DAY"
    meter_rows = generate_intervals(now, event=event)
    by_flat = {row["flat_id"]: row for row in meter_rows}
    with SessionLocal.begin() as session:
        tanks = session.scalars(select(Tank).order_by(Tank.id)).all()
        if tanks:
            for tank in tanks:
                share = tank.capacity_litres / state.capacity
                litres = state.inventory * share
                session.add(TankReading(tank_id=tank.id, observed_at=now, water_level_litres=litres, level_percent=litres / tank.capacity_litres * 100, inflow_litres_per_minute=state.inflow_litres_per_minute * share, outflow_litres_per_minute=state.outflow_litres_per_minute * share, pump_state=state.pump_available))
        meters = session.execute(select(Meter.id, Flat.flat_number).join(Flat, Meter.flat_id == Flat.id)).all()
        session.add_all([MeterReading(meter_id=meter_id, observed_at=now, consumed_litres=by_flat[flat_number]["consumed_litres"] * SIM_MINUTES_PER_TICK / 15, flow_litres_per_minute=by_flat[flat_number]["flow_litres_per_minute"]) for meter_id, flat_number in meters if flat_number in by_flat])

def restore_latest_inventory():
    """Resume the aggregate tank quantity from the latest stored reading per tank."""
    with SessionLocal() as session:
        society = session.get(Society, 1)
        if society is not None:
            config = json.loads(society.config_json)
            state.capacity = float(config.get("tank_capacity_litres", state.capacity))
            state.inventory = float(config.get("initial_inventory_litres", state.inventory))
            state.reserve = float(config.get("critical_reserve_litres", state.reserve))
            state.tanker_eta_hours = float(config.get("tanker_eta_hours", state.tanker_eta_hours))
            state.tanker_quantity_litres = float(config.get("tanker_quantity_litres", state.tanker_quantity_litres))
        readings = []
        for tank in session.scalars(select(Tank).order_by(Tank.id)):
            reading = session.scalar(select(TankReading).where(TankReading.tank_id == tank.id).order_by(TankReading.observed_at.desc()).limit(1))
            if reading is not None: readings.append(reading)
        if readings:
            state.inventory = sum(row.water_level_litres for row in readings)
            state.simulated_at = max(row.observed_at for row in readings)
            state.pump_available = all(row.pump_state for row in readings)
        delivery = session.scalar(select(TankerDelivery).where(TankerDelivery.society_id == 1, TankerDelivery.status.in_(("SCHEDULED", "DELAYED"))).order_by(TankerDelivery.scheduled_arrival).limit(1))
        if delivery is not None:
            state.tanker_id = delivery.id
            state.tanker_eta_hours = max(0.0, (delivery.scheduled_arrival - state.simulated_at).total_seconds() / 3600)
            state.tanker_quantity_litres = delivery.expected_quantity_litres
        else:
            state.tanker_id = None
            state.tanker_eta_hours = 1e9
            state.tanker_quantity_litres = 0.0

@app.on_event("startup")
async def start_simulator():
    global simulator_task
    initialize_database()
    restore_latest_inventory()
    state.last_risk = status()["runway"]["risk"]
    simulator_task = asyncio.create_task(simulator_loop())

@app.on_event("shutdown")
async def stop_simulator():
    if simulator_task:
        simulator_task.cancel()

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/api/v1/health/components")
def components():
    try:
        with SessionLocal() as session: session.execute(select(1))
        database = "ok"
    except Exception:
        database = "unavailable"
    sim_status = "starting" if simulator_task is None else "running" if not simulator_task.done() else "failed"
    return {"backend": "ok", "database": database, "ml": "trained_seasonal_ridge", "simulator": sim_status, "websocket": "available"}

@app.get("/api/v1/water/status")
def water_status(): return status()

@app.get("/api/v1/water/runway")
def water_runway(): return status()["runway"]

@app.get("/api/v1/tanks", dependencies=[Depends(require_admin)])
def tanks():
    with SessionLocal() as session:
        result = []
        for tank in session.scalars(select(Tank).order_by(Tank.id)):
            reading = session.scalar(select(TankReading).where(TankReading.tank_id == tank.id).order_by(TankReading.observed_at.desc()).limit(1))
            result.append({"id": tank.id, "name": tank.name, "capacity_litres": tank.capacity_litres, "critical_reserve_litres": tank.critical_reserve_litres, "reading": None if reading is None else {"observed_at": reading.observed_at.isoformat(), "water_level_litres": round(reading.water_level_litres), "level_percent": round(reading.level_percent, 1), "inflow_litres_per_minute": reading.inflow_litres_per_minute, "outflow_litres_per_minute": reading.outflow_litres_per_minute, "pump_state": reading.pump_state}})
        return result

@app.get("/api/v1/tanks/{tank_id}/history", dependencies=[Depends(require_admin)])
def tank_history(tank_id: int, limit: int = 100):
    limit = min(max(limit, 1), 1000)
    with SessionLocal() as session:
        if session.get(Tank, tank_id) is None: raise HTTPException(404, "Tank not found")
        readings = session.scalars(select(TankReading).where(TankReading.tank_id == tank_id).order_by(TankReading.observed_at.desc()).limit(limit)).all()
        return [{"observed_at": row.observed_at.isoformat(), "water_level_litres": row.water_level_litres, "level_percent": row.level_percent, "inflow_litres_per_minute": row.inflow_litres_per_minute, "outflow_litres_per_minute": row.outflow_litres_per_minute, "pump_state": row.pump_state} for row in reversed(readings)]

@app.get("/api/v1/consumption/society")
def society_consumption():
    """Hourly synthetic meter rollups over the previous day, in kL/hour."""
    now = state.simulated_at.replace(minute=0, second=0, microsecond=0)
    event = "HIGH_USAGE" if state.scenario == Scenario.HIGH_USAGE else "HEATWAVE" if state.scenario == Scenario.HEATWAVE else "LEAK_EVENT" if state.scenario == Scenario.LEAK_EVENT else "NORMAL_DAY"
    rows = []
    for offset in range(23, -1, -1):
        at = now - timedelta(hours=offset)
        readings = generate_intervals(at, event=event)
        total_litres = sum(row["consumed_litres"] for row in readings) * 4
        rows.append({"t": at.isoformat(), "demand": round(total_litres / 1000, 2)})
    return {"unit": "kL/hour", "synthetic_prototype_data": True, "series": rows}

@app.get("/api/v1/towers", dependencies=[Depends(require_admin)])
def towers():
    with SessionLocal() as session:
        rows = session.execute(
            select(Tower.id, Tower.name, func.count(Flat.id))
            .outerjoin(Flat, Flat.tower_id == Tower.id)
            .where(Tower.society_id == 1)
            .group_by(Tower.id, Tower.name)
            .order_by(Tower.name)
        ).all()
    return [{"id": tower_id, "name": name, "flat_count": flat_count} for tower_id, name, flat_count in rows]

@app.get("/api/v1/consumption/tower/{tower_id}", dependencies=[Depends(require_admin)])
def tower_consumption(tower_id: int):
    with SessionLocal() as session:
        tower = session.get(Tower, tower_id)
        if tower is None or tower.society_id != 1:
            raise HTTPException(404, "Tower not found")
        flats = session.scalars(select(Flat).where(Flat.tower_id == tower_id).order_by(Flat.flat_number)).all()
        day = func.date(MeterReading.observed_at)
        rows = session.execute(
            select(Meter.flat_id, day, func.sum(MeterReading.consumed_litres))
            .join(MeterReading, MeterReading.meter_id == Meter.id)
            .join(Flat, Flat.id == Meter.flat_id)
            .where(Flat.tower_id == tower_id, MeterReading.observed_at >= state.simulated_at - timedelta(days=30))
            .group_by(Meter.flat_id, day)
            .order_by(Meter.flat_id, day)
        ).all()
        tower_name = tower.name
    usage = _admin_flat_usage(flats, rows)
    return {
        "tower_id": tower_id,
        "tower": tower_name,
        "synthetic_prototype_data": True,
        "today_litres": sum(item["today_litres"] for item in usage),
        "flats": usage,
    }

@app.get("/api/v1/consumption/flat/{flat_id}", dependencies=[Depends(require_admin)])
def flat_consumption(flat_id: int):
    with SessionLocal() as session:
        flat = session.get(Flat, flat_id)
        if flat is None:
            raise HTTPException(404, "Flat not found")
        tower = session.get(Tower, flat.tower_id)
        if tower is None or tower.society_id != 1:
            raise HTTPException(404, "Flat not found")
        day = func.date(MeterReading.observed_at)
        rows = session.execute(
            select(Meter.flat_id, day, func.sum(MeterReading.consumed_litres))
            .join(MeterReading, MeterReading.meter_id == Meter.id)
            .where(Meter.flat_id == flat_id, MeterReading.observed_at >= state.simulated_at - timedelta(days=30))
            .group_by(Meter.flat_id, day)
            .order_by(day)
        ).all()
        tower_name = tower.name
    usage = _admin_flat_usage([flat], rows)[0]
    return {"tower": tower_name, "synthetic_prototype_data": True, **usage}

@app.get("/api/v1/consumption/me")
def my_consumption(user: User = Depends(current_user)):
    if user.role != "RESIDENT" or user.flat_id is None: raise HTTPException(403, "Resident account with an assigned flat required")
    start = state.simulated_at - timedelta(days=30)
    with SessionLocal() as session:
        flat = session.get(Flat, user.flat_id)
        if flat is None: raise HTTPException(404, "Resident flat not found")
        meter = session.scalar(select(Meter).where(Meter.flat_id == flat.id))
        if meter is None: raise HTTPException(404, "Virtual meter not found")
        readings = session.scalars(select(MeterReading).where(MeterReading.meter_id == meter.id, MeterReading.observed_at >= start).order_by(MeterReading.observed_at)).all()
        daily: dict[str, float] = {}
        for reading in readings:
            key = reading.observed_at.date().isoformat()
            daily[key] = daily.get(key, 0.0) + reading.consumed_litres
        today_date = state.simulated_at.date()
        yesterday_date = today_date - timedelta(days=1)
        today_key = today_date.isoformat()
        yesterday_key = yesterday_date.isoformat()

        hourly_today: dict[int, float] = {h: 0.0 for h in range(max(1, state.simulated_at.hour + 1))}
        hourly_yesterday: dict[int, float] = {h: 0.0 for h in range(24)}
        for reading in readings:
            r_date = reading.observed_at.date()
            if r_date == today_date:
                hourly_today[reading.observed_at.hour] = hourly_today.get(reading.observed_at.hour, 0.0) + reading.consumed_litres
            elif r_date == yesterday_date:
                hourly_yesterday[reading.observed_at.hour] = hourly_yesterday.get(reading.observed_at.hour, 0.0) + reading.consumed_litres

        last7 = [value for day, value in daily.items() if (state.simulated_at.date() - datetime.fromisoformat(day).date()).days < 7]
        last30 = list(daily.values())
        baseline = float(TYPES[flat.household_type][1])
        risk = status()["runway"]["risk"]
        latest_six = readings[-6:]
        possible_anomaly = False
        if len(latest_six) == 6:
            household = Household(flat.flat_number, flat.household_type, flat.occupant_count, "")
            expected = sum(interval_consumption(household, row.observed_at) * SIM_MINUTES_PER_TICK / 15 for row in latest_six)
            possible_anomaly = sustained_usage_anomaly(sum(row.consumed_litres for row in latest_six), expected)

        hourly_threshold = (baseline / 24.0) * 2.2
        return {
            "flat_id": flat.flat_number,
            "synthetic_prototype_data": True,
            "today_litres": round(daily.get(today_key, 0)),
            "yesterday_litres": round(daily.get(yesterday_key, 0)),
            "seven_day_average_litres": round(sum(last7) / len(last7)) if last7 else None,
            "thirty_day_average_litres": round(sum(last30) / len(last30)) if last30 else None,
            "household_baseline_litres_per_day": round(baseline),
            "recommended_range_litres_per_day": recommended_range(baseline, risk),
            "budget_is_guidance": True,
            "possible_anomaly": possible_anomaly,
            "daily_series": [{"date": day, "litres": round(value), "anomaly": value > baseline * 1.4} for day, value in sorted(daily.items())],
            "hourly_today": [{"hour": h, "label": f"{h:02d}:00", "litres": round(litres, 1), "anomaly": litres > hourly_threshold and litres >= 12.0} for h, litres in sorted(hourly_today.items())],
            "hourly_yesterday": [{"hour": h, "label": f"{h:02d}:00", "litres": round(litres, 1), "anomaly": litres > hourly_threshold and litres >= 12.0} for h, litres in sorted(hourly_yesterday.items())],
        }

@app.get("/api/v1/forecasts", dependencies=[Depends(require_admin)])
def forecasts():
    event = "HIGH_USAGE" if state.scenario == Scenario.HIGH_USAGE else "HEATWAVE" if state.scenario == Scenario.HEATWAVE else "LEAK_EVENT" if state.scenario == Scenario.LEAK_EVENT else "NORMAL_DAY"
    return forecast_horizons(state.simulated_at.replace(minute=0, second=0, microsecond=0), event)

@app.post("/api/v1/demo/scenarios/{scenario}", dependencies=[Depends(require_admin)])
def trigger_scenario(scenario: Scenario):
    state.scenario = scenario
    if scenario == Scenario.NORMAL_DAY:
        state.pump_available = True
        state.tanker_eta_hours = 12.0
        state.tanker_quantity_litres = 12_000.0
    elif scenario == Scenario.TANKER_DELAY: state.tanker_eta_hours += 8
    elif scenario == Scenario.PUMP_FAILURE:
        state.pump_available = False
        state.tanker_eta_hours = max(state.tanker_eta_hours, 24)
    elif scenario == Scenario.TANKER_SHORTAGE:
        state.tanker_quantity_litres = 6_000.0
    elif scenario == Scenario.SUPPLY_RESTORED:
        state.pump_available = True
        state.tanker_quantity_litres = 12_000.0
        state.inventory = min(state.capacity, state.inventory + 138_000)
        state.tanker_eta_hours = 24
    elif scenario == Scenario.SHORTAGE_EVENT: state.inventory = min(state.inventory, 90_000)
    if state.tanker_id is not None:
        with SessionLocal.begin() as session:
            delivery = session.get(TankerDelivery, state.tanker_id)
            if delivery is not None:
                delivery.expected_quantity_litres = state.tanker_quantity_litres
                delivery.scheduled_arrival = state.simulated_at + timedelta(hours=state.tanker_eta_hours)
                delivery.status = "DELAYED" if scenario == Scenario.TANKER_DELAY else "SCHEDULED"
    result = status()
    alert_level = {"NORMAL": "INFO", "LOW": "LOW", "MODERATE": "MEDIUM", "HIGH": "HIGH", "CRITICAL": "CRITICAL"}[result["runway"]["risk"]]
    store_alert("WATER_STATUS", alert_level, f"Demo scenario {scenario.value} applied; reserve risk is {result['runway']['risk']}.")
    return result

@app.get("/api/v1/tankers", dependencies=[Depends(require_admin)])
def tankers():
    with SessionLocal() as session:
        rows = session.scalars(select(TankerDelivery).where(TankerDelivery.society_id == 1).order_by(TankerDelivery.scheduled_arrival.desc()).limit(100)).all()
        return [{"id": row.id, "scheduled_arrival": row.scheduled_arrival.isoformat(), "actual_arrival": row.actual_arrival.isoformat() if row.actual_arrival else None, "expected_quantity_litres": row.expected_quantity_litres, "actual_quantity_litres": row.actual_quantity_litres, "status": row.status, "note": row.note} for row in rows]

@app.post("/api/v1/tankers", status_code=201, dependencies=[Depends(require_admin)])
def create_tanker(inputs: TankerInput):
    with SessionLocal.begin() as session:
        active = session.scalars(select(TankerDelivery).where(TankerDelivery.society_id == 1, TankerDelivery.status.in_(("SCHEDULED", "DELAYED")))).all()
        for delivery in active: delivery.status = "CANCELLED"
        delivery = TankerDelivery(society_id=1, scheduled_arrival=state.simulated_at + timedelta(hours=inputs.scheduled_eta_hours), expected_quantity_litres=inputs.expected_quantity_litres, status="SCHEDULED", note=inputs.note.strip())
        session.add(delivery)
        session.flush()
        state.tanker_id = delivery.id
        state.tanker_eta_hours = inputs.scheduled_eta_hours
        state.tanker_quantity_litres = inputs.expected_quantity_litres
    store_alert("WATER_STATUS", "INFO", "Upcoming synthetic tanker schedule was updated by an administrator.")
    return {"id": state.tanker_id, "scheduled_eta_hours": state.tanker_eta_hours, "expected_quantity_litres": state.tanker_quantity_litres, "status": "SCHEDULED"}

@app.patch("/api/v1/tankers/{tanker_id}", dependencies=[Depends(require_admin)])
def update_tanker(tanker_id: int, inputs: TankerUpdateInput):
    with SessionLocal.begin() as session:
        delivery = session.get(TankerDelivery, tanker_id)
        if delivery is None or delivery.society_id != 1: raise HTTPException(404, "Tanker delivery not found")
        if inputs.status in {"SCHEDULED", "DELAYED"} and tanker_id != state.tanker_id:
            others = session.scalars(select(TankerDelivery).where(TankerDelivery.society_id == 1, TankerDelivery.id != tanker_id, TankerDelivery.status.in_(("SCHEDULED", "DELAYED")))).all()
            for other in others: other.status = "CANCELLED"
            state.tanker_id = tanker_id
        delivery.status = inputs.status
        if inputs.note is not None: delivery.note = inputs.note.strip()
        if inputs.expected_quantity_litres is not None: delivery.expected_quantity_litres = inputs.expected_quantity_litres
        if inputs.scheduled_eta_hours is not None: delivery.scheduled_arrival = state.simulated_at + timedelta(hours=inputs.scheduled_eta_hours)
        if tanker_id == state.tanker_id:
            if inputs.status == "CANCELLED":
                state.tanker_id = None
                state.tanker_eta_hours = 1e9
                state.tanker_quantity_litres = 0
            else:
                state.tanker_eta_hours = max(0.0, (delivery.scheduled_arrival - state.simulated_at).total_seconds() / 3600)
                state.tanker_quantity_litres = delivery.expected_quantity_litres
    risk = status()["runway"]["risk"]
    alert_level = {"NORMAL": "INFO", "LOW": "LOW", "MODERATE": "MEDIUM", "HIGH": "HIGH", "CRITICAL": "CRITICAL"}[risk]
    store_alert("TANKER_DELAY" if inputs.status == "DELAYED" else "WATER_STATUS", alert_level, f"Tanker delivery #{tanker_id} updated to {inputs.status}; reserve risk is {risk}.")
    return {"id": tanker_id, "status": inputs.status, "scheduled_arrival": delivery.scheduled_arrival.isoformat(), "expected_quantity_litres": delivery.expected_quantity_litres}

@app.post("/api/v1/simulations", dependencies=[Depends(require_admin)])
def simulate(inputs: SimulationInput):
    current = status()
    adjusted_demand = current["demand_litres_per_day"] * inputs.consumption_multiplier * (1 - inputs.conservation_percent / 100)
    incoming = inputs.tanker_quantity_litres if inputs.pump_available else 0
    result = runway(state.inventory, adjusted_demand, state.reserve, state.tanker_eta_hours + inputs.tanker_delay_hours, incoming, capacity=state.capacity)
    response = {"baseline": current["runway"], "scenario": result, "inputs": inputs.model_dump(), "recommendations": recommendations(result["risk"]), "changes_real_telemetry": False}
    with SessionLocal.begin() as session:
        run = SimulationRun(society_id=1, inputs_json=json.dumps(inputs.model_dump()), results_json="{}")
        session.add(run)
        session.flush()
        response["id"] = run.id
        run.results_json = json.dumps(response)
    return response

@app.get("/api/v1/simulations/{simulation_id}", dependencies=[Depends(require_admin)])
def get_simulation(simulation_id: int):
    with SessionLocal() as session:
        run = session.get(SimulationRun, simulation_id)
        if run is None or run.society_id != 1:
            raise HTTPException(404, "Simulation not found")
        return json.loads(run.results_json)

@app.get("/api/v1/alerts")
def alerts(user: User = Depends(current_user)):
    with SessionLocal() as session:
        rows = session.scalars(select(Alert).where(Alert.society_id == 1).order_by(Alert.created_at.desc()).limit(100)).all()
        read_ids = set(session.scalars(select(AlertRead.alert_id).where(AlertRead.user_id == user.id, AlertRead.alert_id.in_([row.id for row in rows]))).all()) if rows else set()
        return [{"id": row.id, "type": row.kind, "level": row.level, "message": row.message, "created_at": row.created_at.isoformat(), "read": row.id in read_ids} for row in rows]

@app.patch("/api/v1/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, user: User = Depends(current_user)):
    with SessionLocal.begin() as session:
        alert = session.get(Alert, alert_id)
        if alert is None or alert.society_id != 1:
            raise HTTPException(404, "Alert not found")
        read = session.scalar(select(AlertRead).where(AlertRead.alert_id == alert_id, AlertRead.user_id == user.id))
        if read is None:
            session.add(AlertRead(alert_id=alert_id, user_id=user.id, read_at=datetime.now(timezone.utc)))
    return {"alert_id": alert_id, "read": True}

@app.post("/api/v1/complaints", status_code=201)
def create_complaint(inputs: ComplaintInput, user: User = Depends(current_user)):
    if user.role != "RESIDENT": raise HTTPException(403, "Resident role required")
    with SessionLocal.begin() as session:
        complaint = Complaint(society_id=1, resident_id=user.id, category=inputs.category, title=inputs.title.strip(), description=inputs.description.strip(), status="OPEN")
        session.add(complaint)
        session.flush()
        session.add(ComplaintUpdate(complaint_id=complaint.id, author_id=user.id, comment="Complaint submitted", status="OPEN"))
        if user.flat_id:
            flat = session.get(Flat, user.flat_id)
            tower = session.get(Tower, flat.tower_id) if flat else None
            if tower:
                maybe_create_complaint_cluster_alert(session, tower)
        return {"id": complaint.id, "category": complaint.category, "title": complaint.title, "description": complaint.description, "status": complaint.status, "created_at": complaint.created_at.isoformat() if complaint.created_at else None}

def maybe_create_complaint_cluster_alert(session, tower: Tower) -> None:
    since = datetime.now(timezone.utc) - timedelta(minutes=15)
    rows = session.execute(
        select(Complaint, Tower)
        .join(User, Complaint.resident_id == User.id)
        .join(Flat, User.flat_id == Flat.id)
        .join(Tower, Flat.tower_id == Tower.id)
        .where(Complaint.society_id == 1, Tower.id == tower.id, Complaint.created_at >= since)
    ).all()
    reports = [
        {"tower": row_tower.name, "category": complaint.category, "created_at": complaint.created_at.isoformat()}
        for complaint, row_tower in rows
    ]
    clusters = cluster_complaints(reports)
    if not clusters:
        return
    cluster = clusters[0]
    water = status()
    supply_signal = (
        not state.pump_available
        or water["runway"]["risk"] in {"HIGH", "CRITICAL"}
        or water["level_percent"] <= 15
    )
    possible_incident = cluster["pressure_or_no_water_reports"] >= 3 and supply_signal
    already_alerted = session.scalar(
        select(Alert.id)
        .where(
            Alert.society_id == 1,
            Alert.kind == "COMPLAINT_CLUSTER",
            Alert.created_at >= since,
            Alert.message.contains(tower.name),
        )
        .limit(1)
    )
    if already_alerted:
        return
    message = (
        f"Possible {tower.name} water-supply incident: {cluster['complaint_count']} complaints in 15 minutes."
        if possible_incident
        else f"{tower.name} complaint spike: {cluster['complaint_count']} reports in 15 minutes; review pressure and tank status."
    )
    session.add(Alert(
        society_id=1,
        kind="COMPLAINT_CLUSTER",
        level="HIGH" if possible_incident else "MEDIUM",
        message=message,
    ))

@app.get("/api/v1/complaints")
def complaints(user: User = Depends(current_user)):
    with SessionLocal() as session:
        query = select(Complaint).where(Complaint.society_id == 1).order_by(Complaint.created_at.desc()).limit(200)
        if user.role == "RESIDENT": query = query.where(Complaint.resident_id == user.id)
        rows = session.scalars(query).all()
        result = []
        for row in rows:
            resident = session.get(User, row.resident_id)
            flat = session.get(Flat, resident.flat_id) if resident and resident.flat_id else None
            tower = session.get(Tower, flat.tower_id) if flat else None
            updates = session.scalars(select(ComplaintUpdate).where(ComplaintUpdate.complaint_id == row.id).order_by(ComplaintUpdate.created_at)).all()
            result.append({"id": row.id, "category": row.category, "title": row.title, "description": row.description, "status": row.status, "location": f"{tower.name} · {flat.flat_number}" if tower and flat else None, "created_at": row.created_at.isoformat(), "photo_url": f"/api/v1/complaints/{row.id}/photo" if row.photo_path else None, "updates": [{"comment": update.comment, "status": update.status, "created_at": update.created_at.isoformat()} for update in updates]})
        return result

@app.post("/api/v1/complaints/{complaint_id}/photo", status_code=201)
async def attach_complaint_photo(complaint_id: int, photo: UploadFile = File(...), user: User = Depends(current_user)):
    if user.role != "RESIDENT":
        raise HTTPException(403, "Resident role required")
    with SessionLocal() as session:
        complaint = session.get(Complaint, complaint_id)
        if complaint is None or complaint.society_id != 1 or complaint.resident_id != user.id:
            raise HTTPException(404, "Complaint not found")
        old_photo = complaint.photo_path

    saved_name = await store_complaint_photo(photo)
    try:
        with SessionLocal.begin() as session:
            complaint = session.get(Complaint, complaint_id)
            if complaint is None or complaint.resident_id != user.id:
                raise HTTPException(404, "Complaint not found")
            complaint.photo_path = saved_name
    except Exception:
        attachment_path(saved_name).unlink(missing_ok=True)
        raise
    if old_photo:
        attachment_path(old_photo).unlink(missing_ok=True)
    return {"photo_url": f"/api/v1/complaints/{complaint_id}/photo"}

@app.get("/api/v1/complaints/{complaint_id}/photo")
def complaint_photo(complaint_id: int, user: User = Depends(current_user)):
    with SessionLocal() as session:
        complaint = session.get(Complaint, complaint_id)
        if complaint is None or complaint.society_id != 1:
            raise HTTPException(404, "Complaint not found")
        if user.role == "RESIDENT" and complaint.resident_id != user.id:
            raise HTTPException(404, "Complaint not found")
        if user.role not in {"RESIDENT", "ADMIN", "SUPER_ADMIN"}:
            raise HTTPException(403, "Not authorized to view complaint attachments")
        if not complaint.photo_path:
            raise HTTPException(404, "Complaint has no photo")
        path = attachment_path(complaint.photo_path)
    if not path.is_file():
        raise HTTPException(404, "Complaint photo is unavailable")
    return FileResponse(path, media_type="image/jpeg" if path.suffix == ".jpg" else "image/png" if path.suffix == ".png" else "image/webp", filename=path.name, content_disposition_type="inline")

@app.get("/api/v1/complaint-clusters", dependencies=[Depends(require_admin)])
def complaint_clusters():
    since = datetime.now(timezone.utc) - timedelta(minutes=15)
    with SessionLocal() as session:
        rows = session.execute(
            select(Complaint, Tower)
            .join(User, Complaint.resident_id == User.id)
            .join(Flat, User.flat_id == Flat.id)
            .join(Tower, Flat.tower_id == Tower.id)
            .where(Complaint.society_id == 1, Complaint.created_at >= since)
            .order_by(Complaint.created_at)
        ).all()
        recent = [
            {"tower": tower.name, "category": complaint.category, "created_at": complaint.created_at.isoformat()}
            for complaint, tower in rows
        ]
    water = status()
    supply_signal = (
        not state.pump_available
        or water["runway"]["risk"] in {"HIGH", "CRITICAL"}
        or water["level_percent"] <= 15
    )
    results = []
    for cluster in cluster_complaints(recent):
        has_pressure_reports = cluster["pressure_or_no_water_reports"] >= 3
        possible_incident = has_pressure_reports and supply_signal
        message = (
            f"Possible {cluster['tower']} water-supply incident."
            if possible_incident
            else f"{cluster['tower']} complaint spike detected; review reported pressure and current tank status."
        )
        results.append({
            **cluster,
            "window_minutes": 15,
            "possible_incident": possible_incident,
            "message": message,
            "telemetry_context": {
                "society_risk": water["runway"]["risk"],
                "pump_state": water["pump_state"],
                "tank_level_percent": water["level_percent"],
            },
        })
    return results

@app.patch("/api/v1/complaints/{complaint_id}")
def update_complaint(complaint_id: int, inputs: ComplaintStatusUpdate, user: User = Depends(require_admin)):
    with SessionLocal.begin() as session:
        complaint = session.get(Complaint, complaint_id)
        if complaint is None or complaint.society_id != 1: raise HTTPException(404, "Complaint not found")
        complaint.status = inputs.status
        session.add(ComplaintUpdate(complaint_id=complaint.id, author_id=user.id, comment=inputs.comment.strip(), status=inputs.status))
        session.add(Alert(society_id=1, kind="COMPLAINT_UPDATE", level="INFO", message=f"Complaint #{complaint.id} status updated to {inputs.status}"))
        return {"id": complaint.id, "status": complaint.status}

def maintenance_payload(event: MaintenanceEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "affected_towers": json.loads(event.affected_towers_json),
        "severity": event.severity,
        "status": event.status,
    }

@app.get("/api/v1/maintenance")
def maintenance_schedule(user: User = Depends(current_user)):
    with SessionLocal() as session:
        rows = session.scalars(
            select(MaintenanceEvent)
            .where(MaintenanceEvent.society_id == 1)
            .order_by(MaintenanceEvent.start_time)
            .limit(200)
        ).all()
        resident_tower = None
        if user.role == "RESIDENT" and user.flat_id:
            flat = session.get(Flat, user.flat_id)
            tower = session.get(Tower, flat.tower_id) if flat else None
            resident_tower = tower.name if tower else None
        result = []
        for event in rows:
            affected = json.loads(event.affected_towers_json)
            if user.role == "RESIDENT" and affected and resident_tower not in affected:
                continue
            result.append(maintenance_payload(event))
        return result

@app.post("/api/v1/maintenance", status_code=201, dependencies=[Depends(require_admin)])
def schedule_maintenance(inputs: MaintenanceInput):
    start_time = inputs.start_time.astimezone(timezone.utc)
    end_time = inputs.end_time.astimezone(timezone.utc)
    scope = ", ".join(inputs.affected_towers) if inputs.affected_towers else "all towers"
    with SessionLocal.begin() as session:
        event = MaintenanceEvent(
            society_id=1,
            event_type=inputs.event_type,
            title=inputs.title.strip(),
            description=inputs.description.strip(),
            start_time=start_time,
            end_time=end_time,
            affected_towers_json=json.dumps(inputs.affected_towers),
            severity=inputs.severity,
            status="SCHEDULED",
        )
        session.add(event)
        session.flush()
        start_label = start_time.strftime("%b %d, %H:%M UTC")
        end_label = end_time.strftime("%H:%M UTC")
        session.add(Alert(
            society_id=1,
            kind="MAINTENANCE",
            level=inputs.severity,
            message=f"{inputs.title.strip()} for {scope}, {start_label} to {end_label}.",
        ))
        return maintenance_payload(event)

@app.patch("/api/v1/maintenance/{event_id}", dependencies=[Depends(require_admin)])
def update_maintenance(event_id: int, inputs: MaintenanceStatusInput):
    with SessionLocal.begin() as session:
        event = session.get(MaintenanceEvent, event_id)
        if event is None or event.society_id != 1:
            raise HTTPException(404, "Maintenance event not found")
        event.status = inputs.status
        if inputs.status == "CANCELLED":
            session.add(Alert(society_id=1, kind="MAINTENANCE", level="INFO", message=f"Scheduled maintenance was cancelled: {event.title}."))
        return maintenance_payload(event)

@app.get("/api/v1/anomalies", dependencies=[Depends(require_admin)])
def anomalies():
    recent_after = state.simulated_at - timedelta(minutes=max(60, SIM_MINUTES_PER_TICK * 8))
    with SessionLocal() as session:
        rows = session.execute(
            select(MeterReading, Flat, Tower)
            .join(Meter, MeterReading.meter_id == Meter.id)
            .join(Flat, Meter.flat_id == Flat.id)
            .join(Tower, Flat.tower_id == Tower.id)
            .where(MeterReading.observed_at >= recent_after)
            .order_by(MeterReading.observed_at)
        ).all()
        review_rows = session.execute(
            select(Flat.flat_number, AnomalyReview.status, AnomalyReview.comment, AnomalyReview.updated_at)
            .join(AnomalyReview, AnomalyReview.flat_id == Flat.id)
        ).all()
    review_by_flat = {
        flat_number: {"status": review_status, "comment": comment, "updated_at": updated_at.isoformat()}
        for flat_number, review_status, comment, updated_at in review_rows
    }

    samples_by_flat: dict[str, tuple[Flat, Tower, list[MeterReading]]] = {}
    for reading, flat, tower in rows:
        if flat.flat_number not in samples_by_flat:
            samples_by_flat[flat.flat_number] = (flat, tower, [])
        samples_by_flat[flat.flat_number][2].append(reading)

    measured: dict[str, dict[str, Any]] = {}
    for flat_number, (flat, tower, readings) in samples_by_flat.items():
        recent = readings[-6:]
        if len(recent) < 6:
            continue
        household = Household(flat.flat_number, flat.household_type, flat.occupant_count, tower.name)
        expected = [
            interval_consumption(household, row.observed_at, seed=1)
            * SIM_MINUTES_PER_TICK
            / 15
            for row in recent
        ]
        overnight_indices = [index for index, row in enumerate(recent) if 0 <= row.observed_at.hour < 6]
        measured[flat_number] = {
            "flat": flat,
            "tower": tower,
            "ratio": sum(row.consumed_litres for row in recent) / max(sum(expected), 1.0),
            "actual": sum(row.consumed_litres for row in recent),
            "expected": sum(expected),
            "overnight_actual": sum(recent[index].consumed_litres for index in overnight_indices),
            "overnight_expected": sum(expected[index] for index in overnight_indices),
            "latest_actual": recent[-1].consumed_litres,
            "latest_expected": expected[-1],
        }

    peer_ratios = [sample["ratio"] for sample in measured.values()]
    results = []
    for flat_number, sample in measured.items():
        scored = score_usage_anomaly(
            sample["actual"],
            sample["expected"],
            peer_ratios,
            overnight_actual_litres=sample["overnight_actual"],
            overnight_expected_litres=sample["overnight_expected"],
            latest_actual_litres=sample["latest_actual"],
            latest_expected_litres=sample["latest_expected"],
        )
        if scored is None:
            continue
        overnight = scored["overnight_ratio"] >= 3.0 and sample["overnight_actual"] >= 10
        spike = scored["latest_sample_ratio"] >= 4.0 and sample["latest_actual"] >= 10
        if overnight:
            reason = "Sustained overnight consumption is above the household profile and peer flats."
        elif spike:
            reason = "The latest meter sample is unusually high against the household profile."
        else:
            reason = f"Recent usage is {scored['ratio_to_household_baseline']:.1f}× the household profile and unusual against peer flats."
        results.append({
            "flat_id": flat_number,
            "tower": sample["tower"].name,
            "detected_at": recent[-1].observed_at.isoformat(),
            **scored,
            "reason": reason,
            "possible_cause": "Possible leak or abnormal usage",
            "source": "SYNTHETIC_PEER_PROFILE_SCORE",
            "review": review_by_flat.get(flat_number),
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)

@app.patch("/api/v1/anomalies/{flat_number}/review")
def review_anomaly(flat_number: str, inputs: AnomalyReviewInput, admin: User = Depends(require_admin)):
    with SessionLocal.begin() as session:
        flat = session.scalar(select(Flat).where(Flat.flat_number == flat_number))
        if flat is None:
            raise HTTPException(404, "Flat not found")
        review = session.scalar(select(AnomalyReview).where(AnomalyReview.flat_id == flat.id))
        if review is None:
            review = AnomalyReview(flat_id=flat.id, status=inputs.status)
            session.add(review)
        review.status = inputs.status
        review.comment = inputs.comment.strip()
        review.reviewed_by_id = admin.id
        review.updated_at = datetime.now(timezone.utc)
        session.flush()
        return {"flat_id": flat.flat_number, "status": review.status, "comment": review.comment, "updated_at": review.updated_at.isoformat()}

@app.get("/api/v1/anomalies/reviews", dependencies=[Depends(require_admin)])
def anomaly_reviews():
    with SessionLocal() as session:
        rows = session.execute(
            select(Flat.flat_number, Tower.name, AnomalyReview.status, AnomalyReview.comment, AnomalyReview.updated_at)
            .join(AnomalyReview, AnomalyReview.flat_id == Flat.id)
            .join(Tower, Flat.tower_id == Tower.id)
            .order_by(AnomalyReview.updated_at.desc())
        ).all()
    return [
        {"flat_id": flat_number, "tower": tower, "status": review_status, "comment": comment, "updated_at": updated_at.isoformat()}
        for flat_number, tower, review_status, comment, updated_at in rows
    ]

@app.websocket("/ws/societies/{society_id}")
async def websocket_updates(websocket: WebSocket, society_id: str):
    await websocket.accept()
    try:
        auth_frame = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        user = user_from_token(str(auth_frame.get("token", "")))
        if user is None:
            await websocket.close(code=1008)
            return
        while True:
            await websocket.send_json({"type": "water_status", "society_id": society_id, "data": status()})
            await asyncio.sleep(2)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
