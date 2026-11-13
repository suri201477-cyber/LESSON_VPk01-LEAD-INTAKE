"""POST /lead: проверка входа → запись в SQLite → строка в events.log."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.db import DatabaseUnavailableError, save_lead
from app.logging_setup import log_error, log_info, log_warning, setup_logging, shutdown_logging
from app.notify import write_new_lead_event
from app.schemas import LeadAccepted, LeadIn


@asynccontextmanager
async def lifespan(_application: FastAPI):
    setup_logging()
    log_info("service_started")
    yield
    shutdown_logging()


def format_validation_error(exc: RequestValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors():
        error_type = str(error.get("type", ""))
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        field = ".".join(location)

        if error_type.startswith("json_"):
            messages.append("Невалидный JSON")
            continue
        if error_type == "string_too_long" and field:
            messages.append(f"Поле {field} слишком длинное")
            continue
        if field == "contact":
            messages.append("Поле contact обязательно и должно быть непустой строкой")
            continue
        if error_type == "missing" and field:
            messages.append(f"Поле {field} обязательно")
            continue
        if field:
            messages.append(f"Поле {field}: некорректное значение")
            continue
        messages.append("Некорректное тело запроса")

    unique: list[str] = []
    for message in messages:
        if message not in unique:
            unique.append(message)
    return "; ".join(unique) if unique else "Некорректный запрос"


def error_body(detail: str) -> dict[str, str]:
    return {"status": "error", "detail": detail}


def create_app() -> FastAPI:
    application = FastAPI(
        title="Lead Intake MVP",
        description="Приём заявок: webhook → SQLite → журнал событий.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        detail = format_validation_error(exc)
        log_warning(f"rejected_request: {detail}")
        return JSONResponse(status_code=400, content=error_body(detail))

    @application.post("/lead", response_model=LeadAccepted)
    def create_lead(payload: LeadIn):
        try:
            lead_id = save_lead(payload)
        except DatabaseUnavailableError:
            return JSONResponse(status_code=500, content=error_body("База данных недоступна"))

        try:
            write_new_lead_event(lead_id)
        except OSError as exc:
            log_error(f"event_log_failed: {exc}")
            return JSONResponse(
                status_code=500,
                content=error_body("Заявка сохранена, но не удалось записать журнал событий"),
            )

        return {"status": "ok", "id": lead_id}

    def custom_openapi() -> dict:
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        post = schema["paths"]["/lead"]["post"]
        post["responses"].pop("422", None)
        post["responses"]["400"] = {
            "description": "Невалидный JSON или не заполнено поле contact",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "detail": "Поле contact обязательно и должно быть непустой строкой",
                    }
                }
            },
        }
        post["responses"]["500"] = {
            "description": "База данных недоступна или не удалось записать журнал",
            "content": {
                "application/json": {
                    "example": {"status": "error", "detail": "База данных недоступна"}
                }
            },
        }
        schemas = schema.get("components", {}).get("schemas", {})
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
