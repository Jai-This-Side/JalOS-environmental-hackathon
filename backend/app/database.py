import json
import os
from datetime import timedelta
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.models import Society, Tower, Flat, Tank, Meter, User, TankerDelivery, utcnow
from app.simulation import seeded_households

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://jalos:jalos_dev@postgres:5432/jalos")
_url = make_url(DATABASE_URL)
_connect_args = {"check_same_thread": False} if _url.get_backend_name() == "sqlite" else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
if _url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_constraints(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def initialize_database():
    from app.migrations import migrate_schema

    migrate_schema()
    with SessionLocal.begin() as session:
        society = session.scalar(select(Society).where(Society.name == "Jal Residency"))
        if society is None:
            society = Society(name="Jal Residency", config_json=json.dumps({"tower_count": 8, "flat_count": 300, "resident_count_estimate": 1200, "tank_capacity_litres": 300000, "initial_inventory_litres": 187400, "critical_reserve_litres": 45000, "tanker_eta_hours": 12, "tanker_quantity_litres": 12000, "synthetic_data": True}))
            session.add(society)
            session.flush()
            towers = {letter: Tower(society_id=society.id, name=f"Tower {letter}") for letter in "ABCDEFGH"}
            session.add_all(towers.values())
            session.flush()
            tank_specs = [("UG Tank 1", 100000, 15000), ("UG Tank 2", 80000, 12000), ("Overhead Tank 1", 70000, 10000), ("Overhead Tank 2", 50000, 8000)]
            session.add_all([Tank(society_id=society.id, name=name, capacity_litres=capacity, critical_reserve_litres=reserve) for name, capacity, reserve in tank_specs])
            session.add(TankerDelivery(society_id=society.id, scheduled_arrival=utcnow() + timedelta(hours=12), expected_quantity_litres=12000, status="SCHEDULED", note="Seeded synthetic demo delivery"))
            households = seeded_households()
            flats = [Flat(tower_id=towers[home.tower].id, flat_number=home.flat_id, household_type=home.household_type, occupant_count=home.occupants) for home in households]
            session.add_all(flats)
            session.flush()
            session.add_all([Meter(flat_id=flat.id, serial=f"SIM-{home.flat_id}", source="SYNTHETIC_VIRTUAL_METER") for home, flat in zip(households, flats)])
        from app.security import hash_password
        flat_id = session.scalar(select(Flat.id).order_by(Flat.id).limit(1))
        demo_users = [
            ("DEMO_ADMIN_EMAIL", "DEMO_ADMIN_PASSWORD", "ADMIN", None),
            ("DEMO_RESIDENT_EMAIL", "DEMO_RESIDENT_PASSWORD", "RESIDENT", flat_id),
        ]
        for email_key, password_key, role, resident_flat_id in demo_users:
            email = os.getenv(email_key, "").strip().lower()
            password = os.getenv(password_key, "")
            if not email or not password:
                raise RuntimeError(f"Set {email_key} and {password_key} in the local environment")
            if len(password) < 12:
                raise RuntimeError(f"{password_key} must be at least 12 characters")
            existing = session.scalar(select(User).where(User.email == email))
            if existing is None:
                session.add(User(email=email, password_hash=hash_password(password), role=role, flat_id=resident_flat_id))
