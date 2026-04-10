from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AlbumImage(SQLModel, table=True):
    """Explicit many-to-many mapping between Album and ImageAsset.

    One row = "image X belongs to album Y (as a direct/leaf member)".
    The table replaces the previous approach of scanning ImageAsset.album
    JSON arrays at query time, enabling indexed lookups and JOINs.
    """

    __tablename__ = "album_image"

    id: Optional[int] = Field(default=None, primary_key=True)
    album_id: int = Field(index=True)       # Album.id
    image_id: int = Field(index=True)       # ImageAsset.id
    sort_order: int = Field(default=0)      # for manual ordering inside album
    created_at: datetime = Field(default_factory=datetime.now)
