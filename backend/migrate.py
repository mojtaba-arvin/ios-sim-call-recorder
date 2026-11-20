# Apply ordered SQL migrations once, recording each committed version.
from __future__ import annotations

from pathlib import Path
import psycopg

from bridge_core.config import database_url_from_env

_LOCK_KEY = "hashtext('ios-sim-call-recorder:migrations')"


def main():
    dsn = database_url_from_env()
    migrations = Path(__file__).parent / "migrations"
    with psycopg.connect(dsn) as conn:
        # Session-level advisory lock prevents parallel ECS tasks from applying
        # the same migration at the same time.
        conn.execute(f"SELECT pg_advisory_lock({_LOCK_KEY})")
        conn.commit()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )"""
            )
            applied = {
                row[0]
                for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
            }
            conn.commit()
            for path in sorted(migrations.glob("*.sql")):
                if path.name in applied:
                    continue
                sql = path.read_text(encoding="utf-8")
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations(version) VALUES (%s)",
                        (path.name,),
                    )
                print(f"applied {path.name}")
        finally:
            conn.execute(f"SELECT pg_advisory_unlock({_LOCK_KEY})")
            conn.commit()


if __name__ == "__main__":
    main()
