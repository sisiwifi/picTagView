from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def default_usage_count() -> dict[str, int]:
    return {"image": 0}


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(default="", index=True, unique=True)
    name: str = Field(index=True, unique=True, max_length=128)
    display_name: str = Field(default="", max_length=128)
    description: str = Field(default="", max_length=1024)
    usage_count: dict = Field(default_factory=default_usage_count, sa_column=Column(JSON))
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)