from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database = tmp_path / "leads.db"
    events = tmp_path / "events.log"
    app_log = tmp_path / "app.log"
    monkeypatch.setenv("LEAD_DB_PATH", str(database))
    monkeypatch.setenv("LEAD_EVENTS_LOG", str(events))
    monkeypatch.setenv("LEAD_APP_LOG", str(app_log))

    with TestClient(create_app()) as client:
        yield SimpleNamespace(client=client, db=database, events=events, app_log=app_log)


def _rows(database: Path) -> list[tuple]:
    if not database.exists():
        return []
    connection = sqlite3.connect(database)
    try:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'leads'"
        ).fetchone()
        if table is None:
            return []
        return connection.execute(
            "SELECT name, contact, source, comment FROM leads ORDER BY id"
        ).fetchall()
    finally:
        connection.close()


def test_saves_lead_and_writes_event(env):
    response = env.client.post(
        "/lead",
        json={
            "name": "Ирина",
            "contact": "+79990000000",
            "source": "landing",
            "comment": "Хочу консультацию по тарифам",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "id": 1}
    assert _rows(env.db) == [
        ("Ирина", "+79990000000", "landing", "Хочу консультацию по тарифам")
    ]
    assert env.events.read_text(encoding="utf-8") == "New lead saved: 1\n"


def test_strips_whitespace_and_empty_optional_fields(env):
    response = env.client.post(
        "/lead",
        json={
            "name": "  Мария  ",
            "contact": "  +79995554433  ",
            "source": "   ",
            "comment": "  Нужен созвон  ",
        },
    )

    assert response.status_code == 200
    assert _rows(env.db) == [("Мария", "+79995554433", None, "Нужен созвон")]


def test_contact_only(env):
    response = env.client.post("/lead", json={"contact": "+70001112233"})

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert _rows(env.db) == [(None, "+70001112233", None, None)]


def test_second_lead_gets_next_id(env):
    first = env.client.post("/lead", json={"contact": "a@example.com"})
    second = env.client.post("/lead", json={"contact": "b@example.com"})

    assert first.json()["id"] == 1
    assert second.json()["id"] == 2
    assert env.events.read_text(encoding="utf-8") == "New lead saved: 1\nNew lead saved: 2\n"


def test_missing_contact_returns_400_and_does_not_save(env):
    response = env.client.post("/lead", json={"name": "Без телефона", "source": "landing"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert "contact" in body["detail"]
    assert _rows(env.db) == []
    assert not env.events.exists()
    assert "rejected_request" in env.app_log.read_text(encoding="utf-8")


def test_empty_and_blank_contact_return_400(env):
    empty = env.client.post("/lead", json={"contact": ""})
    blank = env.client.post("/lead", json={"contact": "   "})
    null_contact = env.client.post("/lead", json={"contact": None})

    assert empty.status_code == 400
    assert blank.status_code == 400
    assert null_contact.status_code == 400
    assert _rows(env.db) == []


def test_invalid_json_returns_400(env):
    response = env.client.post(
        "/lead",
        content='{"name": "Ирина", '.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Невалидный JSON"
    assert not env.events.exists()


def test_non_object_json_returns_400(env):
    response = env.client.post("/lead", json=["+79990000000"])

    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_comment_too_long_returns_400(env):
    response = env.client.post(
        "/lead",
        json={"contact": "+79990000001", "comment": "x" * 2001},
    )

    assert response.status_code == 400
    assert "comment" in response.json()["detail"]
    assert _rows(env.db) == []


def test_database_unavailable_returns_500_and_writes_log(env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("file", encoding="utf-8")
    monkeypatch.setenv("LEAD_DB_PATH", str(blocker / "leads.db"))

    response = env.client.post("/lead", json={"contact": "+79990000000", "name": "Ирина"})

    assert response.status_code == 500
    body = response.json()
    assert body == {"status": "error", "detail": "База данных недоступна"}
    assert "not-a-directory" not in response.text
    log_text = env.app_log.read_text(encoding="utf-8")
    assert "database_unavailable" in log_text
    assert not env.events.exists()


def test_get_lead_is_not_allowed(env):
    response = env.client.get("/lead")
    assert response.status_code == 405


def test_docs_hide_default_422(env):
    schema = env.client.get("/openapi.json").json()
    responses = schema["paths"]["/lead"]["post"]["responses"]
    assert "422" not in responses
    assert "400" in responses
    assert "500" in responses
    schema_names = set(schema["components"]["schemas"])
    assert "HTTPValidationError" not in schema_names
    assert "ValidationError" not in schema_names


def test_event_log_failure_returns_500_after_save(env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    blocker = tmp_path / "events-blocked"
    blocker.write_text("file", encoding="utf-8")
    monkeypatch.setenv("LEAD_EVENTS_LOG", str(blocker / "events.log"))

    response = env.client.post("/lead", json={"contact": "+79990000000"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Заявка сохранена, но не удалось записать журнал событий"
    assert _rows(env.db) == [(None, "+79990000000", None, None)]
    assert "event_log_failed" in env.app_log.read_text(encoding="utf-8")
