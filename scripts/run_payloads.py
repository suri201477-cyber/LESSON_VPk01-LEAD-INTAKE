"""Прогоняет examples/test_payloads.json по живому серверу и пишет examples/RESULTS.md.

Сервер должен быть уже запущен: python -m app.main
Запуск из корня проекта: python scripts/run_payloads.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import db_path, events_log_path  # noqa: E402
from app.db import list_leads  # noqa: E402

PAYLOADS = ROOT / "examples" / "test_payloads.json"
RESULTS = ROOT / "examples" / "RESULTS.md"
URL = "http://127.0.0.1:8000/lead"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def prepare_body(body: dict) -> dict:
    prepared = dict(body)
    if prepared.get("comment") == "TOO_LONG":
        prepared["comment"] = "x" * 2001
    return prepared


def main() -> None:
    cases = json.loads(PAYLOADS.read_text(encoding="utf-8"))
    lines = [
        "# Результаты прогона test_payloads.json",
        "",
        "Сервер: `http://127.0.0.1:8000/lead`. Файл собран скриптом `scripts/run_payloads.py`.",
        "",
        "| # | Кейс | Ожидали | Получили | Совпало | Ответ |",
        "|---|------|---------|----------|---------|-------|",
    ]
    failed = 0

    with httpx.Client(timeout=10.0) as client:
        for index, case in enumerate(cases, start=1):
            if "raw" in case:
                response = client.post(
                    URL,
                    content=case["raw"].encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
            else:
                response = client.post(URL, json=prepare_body(case["body"]))

            actual = response.status_code
            expected = case["expected_status"]
            ok = actual == expected
            if not ok:
                failed += 1
            answer = response.text.replace("|", "/").replace("\n", " ")
            lines.append(
                f"| {index} | {case['title']} | {expected} | {actual} | {'да' if ok else 'нет'} | `{answer}` |"
            )

    lines.extend(["", "## База после прогона", ""])
    try:
        rows = list_leads()
    except OSError as exc:
        lines.append(f"Не удалось прочитать базу: {exc}")
        rows = []

    lines.append(f"Файл: `{display_path(db_path())}`")
    lines.append("")
    if not rows:
        lines.append("Записей нет.")
    else:
        lines.append("| id | created_at | name | contact | source | comment |")
        lines.append("|----|------------|------|---------|--------|---------|")
        for row in rows:
            comment = str(row["comment"] or "")
            if len(comment) > 40:
                comment = comment[:40] + "…"
            lines.append(
                f"| {row['id']} | {row['created_at']} | {row['name'] or '—'} | {row['contact']} | {row['source'] or '—'} | {comment or '—'} |"
            )
        lines.append("")
        lines.append(f"Всего заявок: {len(rows)}")

    lines.extend(["", "## Журнал событий", ""])
    events = events_log_path()
    lines.append(f"Файл: `{display_path(events)}`")
    lines.append("")
    if events.exists():
        lines.append("```text")
        lines.append(events.read_text(encoding="utf-8").rstrip())
        lines.append("```")
    else:
        lines.append("Файл журнала не создан.")

    lines.append("")
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Кейсов: {len(cases)}, не совпало: {failed}")
    print(f"Отчёт: {RESULTS}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
