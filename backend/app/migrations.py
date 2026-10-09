"""Run Alembic migrations while preserving databases created by older demo builds."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import DATABASE_URL, engine


LEGACY_BASE_TABLES = {
    "societies",
    "alerts",
    "maintenance_events",
    "simulation_runs",
    "tanker_deliveries",
    "tanks",
    "towers",
    "flats",
    "tank_readings",
    "meters",
    "users",
    "complaints",
    "meter_readings",
    "complaint_updates",
}


def migrate_schema() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("prepend_sys_path", str(backend_root))
    config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

    table_names = set(inspect(engine).get_table_names())
    if "societies" in table_names and "alembic_version" not in table_names:
        missing = LEGACY_BASE_TABLES - table_names
        if missing:
            names = ", ".join(sorted(missing))
            raise RuntimeError(f"Existing JalOS database is missing tables: {names}. Back it up, then run the local demo with --reset.")
        # The unversioned demo schema matches the original migration, not the
        # latest one. Stamp that baseline so subsequent migrations still run.
        command.stamp(config, "42d59c43c1dd")
    command.upgrade(config, "head")
