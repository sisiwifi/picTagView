from pathlib import Path
from typing import Optional

from sqlalchemy import exists, not_
from sqlmodel import select

from app.core.config import CACHE_DIR, PROJECT_ROOT, TEMP_DIR
from app.models.album import Album
from app.models.image_asset import ImageAsset
from app.models.soft_delete import PathSoftDelete


def ia_not_deleted():
    return not_(
        exists(
            select(PathSoftDelete.id)
            .where(PathSoftDelete.entity_type == "image")
            .where(PathSoftDelete.owner_id == ImageAsset.id)
        )
    )


def album_not_deleted():
    return not_(
        exists(
            select(PathSoftDelete.id)
            .where(PathSoftDelete.entity_type == "album")
            .where(PathSoftDelete.owner_id == Album.id)
        )
    )


def resolve_stored_path(stored_path: Optional[str]) -> Optional[Path]:
    if not stored_path:
        return None
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def thumb_url(asset: ImageAsset) -> str:
    for thumb in asset.thumbs or []:
        if not isinstance(thumb, dict):
            continue
        p = thumb.get("path")
        if not isinstance(p, str) or not p:
            continue
        resolved = resolve_stored_path(p)
        if not resolved or not resolved.exists():
            continue
        try:
            resolved.relative_to(TEMP_DIR)
        except ValueError:
            continue
        return f"/thumbnails/{resolved.name}"
    return ""


def cache_thumb_url(asset: ImageAsset) -> Optional[str]:
    cache_file = CACHE_DIR / f"{asset.file_hash}_cache.webp"
    if cache_file.exists():
        return f"/cache/{asset.file_hash}_cache.webp"
    return None