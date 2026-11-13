"""Служебный журнал: старт сервиса и ошибки. Персональные данные заявок сюда не пишем."""

from __future__ import annotations

import logging

from app.config import app_log_path

LOGGER_NAME = "lead_intake"


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    path = app_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def shutdown_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def log_error(message: str) -> None:
    logging.getLogger(LOGGER_NAME).error(message)


def log_warning(message: str) -> None:
    logging.getLogger(LOGGER_NAME).warning(message)


def log_info(message: str) -> None:
    logging.getLogger(LOGGER_NAME).info(message)
