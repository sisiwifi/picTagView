from __future__ import annotations

import json as _json
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, String
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


class _NullSafeJSON(TypeDecorator):
    """JSON column that stores Python None as SQL NULL (never as JSON 'null' text).

    SQLAlchemy's built-in JSON type serialises None → 'null' on SQLite regardless
    of the none_as_null flag in some versions.  This decorator intercepts the
    value at the Python→DB boundary and forces None through as SQL NULL.
    On the DB→Python side any bare 'null' / '["null"]' artefact is also
    normalised back to None so existing dirty rows are handled transparently.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Normalise known bogus serialisations left by previous SQLAlchemy behaviour
        if value in ("null", '"null"', "[null]", '["null"]', "[]"):
            return None
        try:
            return _json.loads(value)
        except Exception:
            return None



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
    # 软删除：JSON 数组，按 media_path 位置对应；null 表示所有位置均未删除
    # 示例: [null, "2024-07-01T00:00:00"] 表示位置0未删除，位置1已删除
    deleted_at: Optional[list] = Field(default=None, sa_column=Column(_NullSafeJSON))
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
