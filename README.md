# Lead Intake MVP

Webhook → SQLite → журнал событий.

Мини-сервис принимает заявку, сохраняет её в базу и оставляет след «заявка принята». Сделан как учебный фриланс-MVP: один сценарий, локальный запуск, без деплоя.

Проблема: заявки приходят из формы, соцсетей и таблиц и часть теряется.  
Решение: `POST /lead` + SQLite + запись в `logs/events.log` + лог ошибок.  
Результат: каждая принятая заявка лежит в базе, и по журналу видно, что она сохранена.

Уведомление — вариант A (журнал событий). Письмо менеджеру не используется: для локального MVP не нужен почтовый ящик и пароль.

## Запуск за несколько минут

Нужен Python 3.10 или новее. Команды ниже для PowerShell из корня проекта.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

Сервер слушает только этот компьютер: [http://127.0.0.1:8000](http://127.0.0.1:8000).  
Страница запроса: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Окно с сервером не закрывать. Дальше — второе окно PowerShell в той же папке.

Отправить пример заявки:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/lead -H "Content-Type: application/json" --data-binary "@examples/lead.json"
```

Ожидаемый ответ:

```json
{"status":"ok","id":1}
```

Если в базе уже есть учебные заявки, `id` будет следующим свободным номером.

Посмотреть базу:

```powershell
.\.venv\Scripts\python.exe scripts\show_leads.py
```

Посмотреть уведомление и ошибки:

```powershell
Get-Content -Encoding UTF8 .\logs\events.log
Get-Content -Encoding UTF8 .\logs\app.log
```

В `logs/events.log` успешная заявка выглядит так:

```text
New lead saved: 1
```

Тот же запрос из Python, если `curl` неудобен:

```powershell
.\.venv\Scripts\python.exe examples\send_lead.py
```

## Что приходит в POST /lead

| Поле | Обязательно | Смысл |
|------|-------------|--------|
| `contact` | да | телефон, email или ник. Пустая строка не подходит |
| `name` | нет | имя |
| `source` | нет | откуда заявка: `landing`, `instagram`, `sheet` |
| `comment` | нет | текст заявки, до 2000 символов |

Лишние поля игнорируются. Невалидный JSON или пустой `contact` → HTTP 400. База недоступна → HTTP 500, подробность только в `logs/app.log`.

Проверка ошибки 400:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/lead -H "Content-Type: application/json" --data-binary "@examples/no_contact.json"
```

Ответ:

```json
{"status":"error","detail":"Поле contact обязательно и должно быть непустой строкой"}
```

Такая заявка в базу не попадает. В `logs/app.log` появляется строка `rejected_request`.

## Где лежат результаты

| Что | Файл |
|-----|------|
| База заявок | `data/leads.db` |
| Уведомление «заявка принята» | `logs/events.log` |
| Старт сервиса и ошибки | `logs/app.log` |

В журнале событий только номер заявки. Телефон и имя остаются в базе.

Время в базе — UTC, с суффиксом `Z`. Время в `logs/app.log` — местное.

## Как показать ошибку базы (HTTP 500)

Остановить сервер (Ctrl+C) и в том же окне:

```powershell
New-Item -ItemType File -Force .\data\not-a-folder | Out-Null
$env:LEAD_DB_PATH = Join-Path (Get-Location) "data\not-a-folder\leads.db"
.\.venv\Scripts\python.exe -m app.main
```

Снова отправить `examples/lead.json`. Ответ будет `База данных недоступна` со статусом 500. В `logs/app.log` будет строка `database_unavailable`. В ответе клиенту нет пути к файлу и текста SQLite.

Вернуть обычный режим: остановить сервер, затем

```powershell
Remove-Item Env:\LEAD_DB_PATH
Remove-Item .\data\not-a-folder
.\.venv\Scripts\python.exe -m app.main
```

## Проверки

Автотесты:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Десять учебных запросов к уже запущенному серверу. Успешные заявки допишутся в базу. Чтобы отчёт совпал с чистым прогоном, сначала выполните сброс из следующего раздела.

```powershell
.\.venv\Scripts\python.exe scripts\run_payloads.py
```

Сводка последнего прогона: [examples/RESULTS.md](examples/RESULTS.md).

## Сброс базы и журналов

Остановить сервер, затем:

```powershell
Remove-Item -ErrorAction SilentlyContinue data\leads.db, logs\events.log, logs\app.log
```

## Как устроено

```text
форма / скрипт
    → POST /lead
    → проверка JSON и поля contact
    → INSERT в таблицу leads
    → строка в logs/events.log
    → ответ {"status":"ok","id":...}
```

| Файл | Роль |
|------|------|
| `app/main.py` | endpoint, ответы 400 и 500 |
| `app/schemas.py` | форма заявки |
| `app/db.py` | SQLite и таблица `leads` |
| `app/notify.py` | журнал событий |
| `app/logging_setup.py` | журнал ошибок |
| `app/config.py` | пути к базе и журналам |

Переменные окружения, если нужно подменить пути: `LEAD_DB_PATH`, `LEAD_EVENTS_LOG`, `LEAD_APP_LOG`.

## Сценарий демо, 1–2 минуты

1. Показать запущенный сервер и открыть [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
2. Отправить `examples/lead.json` командой `curl.exe` выше.
3. Показать ответ `{"status":"ok","id":...}`.
4. Запустить `scripts/show_leads.py` и показать новую строку: имя, контакт, источник, комментарий.
5. Открыть `logs/events.log` и показать `New lead saved: <id>` с тем же номером.
6. По желанию отправить `examples/no_contact.json` и показать 400, затем строку `rejected_request` в `logs/app.log`.

Фраза в конце: заявка не осталась в мессенджере, она в базе, и журнал подтверждает, что она принята.

## Сценарий короткой защиты

- Кому это нужно: небольшой бизнес, у которого заявки приходят из разных мест и часть теряется.
- Цепочка: endpoint → проверка входа → SQLite → журнал событий.
- Обязателен только `contact`. Нет контакта или сломан JSON — 400, в базу ничего не пишется.
- Если файл базы недоступен — 500 и строка в `logs/app.log`. Клиенту не отдаются внутренние детали.
- Журнал событий выбран вместо почты: он работает локально и его можно показать на демо без SMTP.
- Дальше по желанию заказчика: дедупликация, деплой, страница списка заявок, письмо или мессенджер.

## Портфолио

**Кейс:** Lead Intake MVP (Webhook → DB → Notification)

Проблема: заявки теряются, всё вручную.  
Решение: endpoint + SQLite + уведомление + логирование.  
Результат: фиксируем каждый лид и исключаем «потери».

## Что сознательно не входит в эту версию

Один endpoint и один сценарий. Нет дедупликации, личного кабинета, авторизации и выкладки на сервер. Повторная отправка той же заявки создаст вторую строку.
