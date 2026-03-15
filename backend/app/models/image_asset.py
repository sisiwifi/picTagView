from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ImageAsset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    original_path: str = Field(index=True)
    file_hash: str = Field(index=True, unique=True)
    thumb_path: Optional[str] = Field(default=None)
    media_path: Optional[str] = Field(default=None)
    date_group: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
