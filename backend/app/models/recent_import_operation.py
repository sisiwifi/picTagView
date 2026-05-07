from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class RecentImportOperation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    successful_image_ids: list[int] | None = Field(default_factory=list, sa_column=Column(JSON))
    preview_image_ids: list[int] | None = Field(default_factory=list, sa_column=Column(JSON))
    direct_image_ids: list[int] | None = Field(default_factory=list, sa_column=Column(JSON))
    top_album_public_ids: list[str] | None = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now, index=True)
