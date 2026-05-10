from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

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
    # 用户删除已迁移到 trash + TrashEntry，此处不再存储 deleted_at
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    file_size: Optional[int] = Field(default=None)
    mime_type: Optional[str] = Field(default=None)
    is_animated: Optional[bool] = Field(default=None, index=True)
    animation_meta: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    category_id: int = Field(default=1, index=True)
    # 存储 Tag 的 id 整数列表，如 [23, 45, 91]；查询标签详情时通过 /api/tags?ids=... 批量获取
    tags: Optional[list[int]] = Field(default_factory=list, sa_column=Column(JSON))
    # 所属相册：[[public_id_1, public_id_2], [...]] 每个内层数组是从根到叶的完整路径
    album: Optional[list[list[str]]] = Field(default_factory=list, sa_column=Column(JSON))
    collection: Optional[list] = Field(default_factory=list, sa_column=Column(JSON))  # 兼容字段；实际收藏关系由 collection_image 承载
    created_at: datetime = Field(default_factory=datetime.now)

    @staticmethod
    def _normalize_frame_count(value: Any) -> int:
        try:
            parsed = int(value or 1)
        except Exception:
            parsed = 1
        return max(parsed, 1)

    @staticmethod
    def _normalize_animation_format(value: Any) -> Optional[str]:
        normalized = str(value or "").strip().upper()
        return normalized or None

    @classmethod
    def normalize_animation_meta(cls, value: Any) -> Optional[dict[str, Any]]:
        if not isinstance(value, dict):
            return None
        normalized_format = cls._normalize_animation_format(
            value.get("format") or value.get("animation_format")
        )
        has_frame_count = value.get("frame_count") is not None
        normalized_frame_count = cls._normalize_frame_count(value.get("frame_count")) if has_frame_count else 1
        if not normalized_format and not has_frame_count:
            return None
        return {
            "frame_count": normalized_frame_count,
            "format": normalized_format,
        }

    @property
    def normalized_animation_meta(self) -> Optional[dict[str, Any]]:
        return self.normalize_animation_meta(self.animation_meta)

    @property
    def frame_count(self) -> int:
        meta = self.normalize_animation_meta(self.animation_meta)
        if not meta:
            return 1
        return self._normalize_frame_count(meta.get("frame_count"))

    @frame_count.setter
    def frame_count(self, value: Any) -> None:
        meta = self.normalize_animation_meta(self.animation_meta) or {}
        normalized_frame_count = self._normalize_frame_count(value)
        normalized_format = self._normalize_animation_format(meta.get("format"))
        if normalized_frame_count <= 1 and not normalized_format:
            self.animation_meta = None
            return
        self.animation_meta = {
            "frame_count": normalized_frame_count,
            "format": normalized_format,
        }

    @property
    def animation_format(self) -> Optional[str]:
        meta = self.normalize_animation_meta(self.animation_meta)
        if not meta:
            return None
        return self._normalize_animation_format(meta.get("format"))

    @animation_format.setter
    def animation_format(self, value: Any) -> None:
        meta = self.normalize_animation_meta(self.animation_meta) or {}
        normalized_format = self._normalize_animation_format(value)
        normalized_frame_count = self._normalize_frame_count(meta.get("frame_count"))
        if normalized_frame_count <= 1 and not normalized_format:
            self.animation_meta = None
            return
        self.animation_meta = {
            "frame_count": normalized_frame_count,
            "format": normalized_format,
        }
