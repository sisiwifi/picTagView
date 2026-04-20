from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Album(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(default="", index=True, unique=True)
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    path: str = Field(index=True)          # media-relative, e.g. "2024-07/vacation"
    category_id: int = Field(default=1, index=True)
    is_leaf: bool = Field(default=True)
    parent_id: Optional[int] = Field(default=None, index=True)
    cover: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    photo_count: int = Field(default=0)
    subtree_photo_count: int = Field(default=0)
    sort_mode: str = Field(default="alpha")  # alpha | date | manual
    settings: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
    stats: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
    date_group: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    # 用户删除已迁移到 trash + TrashEntry，此处不再存储 deleted_at
