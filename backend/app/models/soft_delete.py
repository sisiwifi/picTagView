from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PathSoftDelete(SQLModel, table=True):
    """Unified soft-delete record for both images and albums.

    One row = one deleted path.  The entity is considered deleted as long as
    a row exists with (entity_type, target_path).  Deleting the row = restore.

    entity_type : 'image' | 'album'
    owner_id    : ImageAsset.id or Album.id – stored for fast SQL filtering via
                  subquery; may be NULL for future entity types that lack an
                  integer PK.
    target_path : The normalised project-relative path that was deleted.
                  For images  – the specific media_path entry.
                  For albums  – Album.path.
    """

    __tablename__ = "path_soft_delete"

    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(
        index=True,
        description="'image' or 'album'",
    )
    owner_id: Optional[int] = Field(default=None, index=True)
    target_path: str = Field(index=True)
    deleted_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
