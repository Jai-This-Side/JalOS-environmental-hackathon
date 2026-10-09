"""Verify an unversioned original demo database upgrades through all revisions."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="jalos-legacy-migration-") as temp_dir:
        database_file = Path(temp_dir) / "legacy.sqlite3"
        database_url = URL.create("sqlite+pysqlite", database=str(database_file)).render_as_string(hide_password=False)
        os.environ["DATABASE_URL"] = database_url

        config = Config(str(ROOT / "backend" / "alembic.ini"))
        config.set_main_option("prepend_sys_path", str(ROOT / "backend"))
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
        command.upgrade(config, "42d59c43c1dd")

        with closing(sqlite3.connect(database_file)) as connection:
            connection.execute("DROP TABLE alembic_version")
            connection.commit()

        from app.database import engine
        from app.migrations import migrate_schema

        migrate_schema()
        engine.dispose()

        with closing(sqlite3.connect(database_file)) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            complaint_columns = {row[1] for row in connection.execute("PRAGMA table_info(complaints)")}
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]

        required_tables = {"anomaly_reviews", "alert_reads"}
        if revision != "65f8c49d2b31" or not required_tables.issubset(tables) or "photo_path" not in complaint_columns:
            raise RuntimeError("Legacy schema did not reach the latest JalOS database revision")
        print(f"PASS unversioned legacy schema upgraded to {revision}")


if __name__ == "__main__":
    main()
