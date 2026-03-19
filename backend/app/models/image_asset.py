from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ImageAsset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    original_path: str = Field(index=True)
    full_filename: Optional[str] = Field(default=None, index=True)
    file_hash: str = Field(index=True, unique=True)
    quick_hash: Optional[str] = Field(default=None, index=True)
    thumb_path: Optional[str] = Field(default=None)
    thumbs: Optional[list[dict]] = Field(default_factory=list, sa_column=Column(JSON))
    media_path: Optional[str] = Field(default=None)
    date_group: Optional[str] = Field(default=None, index=True)
    file_created_at: Optional[datetime] = Field(default=None, index=True)
    imported_at: datetime = Field(default_factory=datetime.now, index=True)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    file_size: Optional[int] = Field(default=None)
    mime_type: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    tags: Optional[list[str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)
