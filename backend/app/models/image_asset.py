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
    # thumb_path removed — thumbnail metadata is exclusively stored in `thumbs`
    thumbs: Optional[list[dict]] = Field(default_factory=list, sa_column=Column(JSON))
    media_path: Optional[list[str]] = Field(default_factory=list, sa_column=Column(JSON))
    date_group: Optional[str] = Field(default=None, index=True)
    file_created_at: Optional[datetime] = Field(default=None, index=True)
    imported_at: datetime = Field(default_factory=datetime.now, index=True)
    # 软删除已迁移到独立表 path_soft_delete，此处不再存储 deleted_at
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    file_size: Optional[int] = Field(default=None)
    mime_type: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    tags: Optional[list[str]] = Field(default_factory=list, sa_column=Column(JSON))
    # 所属相册：[[public_id_1, public_id_2], [...]] 每个内层数组是从根到叶的完整路径
    album: Optional[list[list[str]]] = Field(default_factory=list, sa_column=Column(JSON))
    collection: Optional[list] = Field(default_factory=list, sa_column=Column(JSON))  # 所属收藏集
    created_at: datetime = Field(default_factory=datetime.now)
