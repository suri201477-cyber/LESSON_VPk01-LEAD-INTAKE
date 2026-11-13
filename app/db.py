"""SQLite: одна таблица leads. Соединение открывается на время одного запроса."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.config import db_path
from app.logging_setup import log_error
from app.schemas import LeadIn

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT,
    contact TEXT NOT NULL,
    source TEXT,
    comment TEXT
)
"""

INSERT_SQL = """
INSERT INTO leads (created_at, name, contact, source, comment)
VALUES (?, ?, ?, ?, ?)
"""

SELECT_SQL = """
SELECT id, created_at, name, contact, source, comment
FROM leads
ORDER BY id
"""


class DatabaseUnavailableError(Exception):
    """Базу не удалось открыть или записать. Наружу отдаём HTTP 500 без деталей SQLite."""


def get_connection() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    return connection


def save_lead(lead: LeadIn) -> int:
    try:
        connection = get_connection()
    except (sqlite3.Error, OSError) as exc:
        log_error(f"database_unavailable: {exc}")
        raise DatabaseUnavailableError() from exc

    try:
        connection.execute(CREATE_TABLE_SQL)
        cursor = connection.execute(
            INSERT_SQL,
            (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                lead.name,
                lead.contact,
                lead.source,
                lead.comment,
            ),
        )
        connection.commit()
        lead_id = cursor.lastrowid
    except sqlite3.Error as exc:
        log_error(f"database_unavailable: {exc}")
        raise DatabaseUnavailableError() from exc
    finally:
        connection.close()

    if lead_id is None:
        log_error("database_unavailable: insert did not return id")
        raise DatabaseUnavailableError()
    return int(lead_id)


def list_leads() -> list[dict[str, object]]:
    path = db_path()
    if not path.exists():
        return []

    connection = get_connection()
    try:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'leads'"
        ).fetchone()
        if table is None:
            return []
        rows = connection.execute(SELECT_SQL).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
