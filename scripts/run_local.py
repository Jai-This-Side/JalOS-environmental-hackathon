"""Start the JalOS API and synthetic simulator using a local SQLite database."""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DIR = ROOT / ".local"
DATABASE_FILE = LOCAL_DIR / "jalos.sqlite3"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("JALOS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("JALOS_PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="Reload the API after Python source changes")
    parser.add_argument("--reset", action="store_true", help="Delete the local demo database before starting")
    args = parser.parse_args()

    if args.reset and "DATABASE_URL" in os.environ:
        raise SystemExit("--reset only resets the runner-managed .local SQLite database. Remove --reset when DATABASE_URL is set.")

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    if args.reset and DATABASE_FILE.exists():
        DATABASE_FILE.unlink()

    os.environ.setdefault(
        "DATABASE_URL",
        URL.create("sqlite+pysqlite", database=str(DATABASE_FILE)).render_as_string(hide_password=False),
    )
    os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
    os.environ.setdefault("DEMO_ADMIN_EMAIL", "admin@jalos.local")
    os.environ.setdefault("DEMO_ADMIN_PASSWORD", "AdminDemo-2026!Change")
    os.environ.setdefault("DEMO_RESIDENT_EMAIL", "resident@jalos.local")
    os.environ.setdefault("DEMO_RESIDENT_PASSWORD", "ResidentDemo-2026!Change")
    os.environ.setdefault("JALOS_SIM_TICK_SECONDS", "1")
    os.environ.setdefault("JALOS_SIM_MINUTES_PER_TICK", "5")

    if len(os.environ["JWT_SECRET"].encode()) < 32:
        raise SystemExit("JWT_SECRET must contain at least 32 bytes. Remove the short value and retry.")

    sys.path.insert(0, str(ROOT / "backend"))
    import uvicorn

    print("JalOS local demo is starting with synthetic data and SQLite.")
    print(f"API: http://127.0.0.1:{args.port}/docs")
    print(f"Health: http://127.0.0.1:{args.port}/api/v1/health/components")
    print(f"Admin: {os.environ['DEMO_ADMIN_EMAIL']} / {os.environ['DEMO_ADMIN_PASSWORD']}")
    print(f"Resident: {os.environ['DEMO_RESIDENT_EMAIL']} / {os.environ['DEMO_RESIDENT_PASSWORD']}")
    print("These built-in credentials are for local development only.")
    uvicorn.run(
        "app.main:app",
        app_dir=str(ROOT / "backend"),
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
