"""Пути к базе и журналам. Читаются в момент вызова, чтобы тесты могли подменить их через переменные окружения."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: str) -> Path:
    raw = os.environ.get(name, default)
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def db_path() -> Path:
    return _path_from_env("LEAD_DB_PATH", "data/leads.db")


def events_log_path() -> Path:
    return _path_from_env("LEAD_EVENTS_LOG", "logs/events.log")


def app_log_path() -> Path:
    return _path_from_env("LEAD_APP_LOG", "logs/app.log")
