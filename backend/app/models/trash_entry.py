from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TrashEntry(SQLModel, table=True):
    __tablename__ = "trash_entry"

    id: Optional[int] = Field(default=None, primary_key=True)
    entry_key: str = Field(index=True, unique=True)
    entity_type: str = Field(index=True, description="'image' or 'album'")
    display_name: str = Field(index=True)
    original_path: str = Field(index=True)
    original_date_group: Optional[str] = Field(default=None, index=True)
    trash_path: str = Field(index=True, unique=True)
    preview_path: Optional[str] = Field(default=None)
    preview_thumb_path: Optional[str] = Field(default=None)
    preview_cache_path: Optional[str] = Field(default=None)
    file_hash: Optional[str] = Field(default=None, index=True)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    file_size: Optional[int] = Field(default=None)
    mime_type: Optional[str] = Field(default=None)
    imported_at: Optional[datetime] = Field(default=None)
    file_created_at: Optional[datetime] = Field(default=None)
    source_created_at: Optional[datetime] = Field(default=None)
    photo_count: Optional[int] = Field(default=None)
    tags: Optional[list[int]] = Field(default_factory=list, sa_column=Column(JSON))
    metadata_json: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now, index=True)