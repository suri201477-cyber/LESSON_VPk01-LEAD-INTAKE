"""Вариант A: уведомление — строка в журнале событий.

Формат фиксированный: New lead saved: <id>
В строке нет телефона и имени: персональные данные остаются только в базе.
"""

from __future__ import annotations

from app.config import events_log_path


def write_new_lead_event(lead_id: int) -> None:
    path = events_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as events_file:
        events_file.write(f"New lead saved: {lead_id}\n")
