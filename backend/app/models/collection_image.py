from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class CollectionImage(SQLModel, table=True):
    """Explicit many-to-many mapping between Collection and ImageAsset.

    One row = "image X belongs to collection Y (as a direct/leaf member)".
    The table mirrors the album_image pattern so collection browsing can rely
    on indexed joins instead of denormalized JSON scans.
    """

    __tablename__ = "collection_image"
    __table_args__ = (
        UniqueConstraint("collection_id", "image_id", name="uq_collection_image_collection_image"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: int = Field(index=True)
    image_id: int = Field(index=True)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)