"""Отправляет одну заявку на локальный сервер. Удобно, если консоль портит кириллицу.

Из корня проекта:
    python examples/send_lead.py
    python examples/send_lead.py --name "Ирина" --contact "+79990000000" --source landing --comment "Нужна консультация"
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8000/lead"


def main() -> None:
    parser = argparse.ArgumentParser(description="Отправить заявку на POST /lead")
    parser.add_argument("--name", default="Ирина")
    parser.add_argument("--contact", default="+79990000000")
    parser.add_argument("--source", default="landing")
    parser.add_argument("--comment", default="Хочу консультацию по тарифам")
    args = parser.parse_args()

    payload = {
        "name": args.name,
        "contact": args.contact,
        "source": args.source,
        "comment": args.comment,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            print(response.status)
            print(body)
    except urllib.error.HTTPError as exc:
        print(exc.code)
        print(exc.read().decode("utf-8"))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
