"""Вход заявки. Обязательное поле одно: contact."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_optional(value: object) -> object:
    if value is None or not isinstance(value, str):
        return value
    stripped = value.strip()
    return stripped or None


class LeadIn(BaseModel):
    """Заявка из формы, таблицы или другого канала."""

    name: str | None = Field(default=None, max_length=200)
    contact: str = Field(min_length=1, max_length=200)
    source: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Ирина",
                    "contact": "+79990000000",
                    "source": "landing",
                    "comment": "Хочу консультацию по тарифам",
                }
            ]
        }
    )

    @field_validator("name", "source", "comment", mode="before")
    @classmethod
    def clean_optional(cls, value: object) -> object:
        return _strip_optional(value)

    @field_validator("contact", mode="before")
    @classmethod
    def clean_contact(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class LeadAccepted(BaseModel):
    status: str
    id: int
