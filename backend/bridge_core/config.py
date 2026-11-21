"""Environment configuration helpers shared by API and worker entry points."""
from __future__ import annotations

import os
from urllib.parse import quote


def database_url_from_env() -> str:
    direct = os.environ.get("DATABASE_URL", "").strip()
    if direct:
        return direct
    required = ("DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD")
    values = {key: os.environ.get(key, "").strip() for key in required}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RuntimeError("database connection settings are incomplete")
    return (
        f"postgresql://{quote(values['DATABASE_USER'], safe='')}:"
        f"{quote(values['DATABASE_PASSWORD'], safe='')}@"
        f"{values['DATABASE_HOST']}:{values['DATABASE_PORT']}/"
        f"{quote(values['DATABASE_NAME'], safe='')}?sslmode=require"
    )
