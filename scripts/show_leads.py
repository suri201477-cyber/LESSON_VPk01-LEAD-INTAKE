"""Печатает заявки из SQLite. Запуск из корня проекта: python scripts/show_leads.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import db_path  # noqa: E402
from app.db import list_leads  # noqa: E402


def _show(value: object) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def main() -> None:
    try:
        rows = list_leads()
    except OSError as exc:
        print(f"Не удалось открыть базу: {exc}")
        print(f"Файл базы: {db_path()}")
        sys.exit(1)

    print(f"Файл базы: {db_path()}")
    if not rows:
        print("В базе пока нет заявок.")
        return

    for row in rows:
        print(f"#{row['id']}  {row['created_at']}")
        print(f"  name:    {_show(row['name'])}")
        print(f"  contact: {_show(row['contact'])}")
        print(f"  source:  {_show(row['source'])}")
        print(f"  comment: {_show(row['comment'])}")
        print()
    print(f"Всего заявок: {len(rows)}")


if __name__ == "__main__":
    main()
