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


def normalize_stored_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def build_soft_delete_maps(session) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
    image_deleted: dict[int, set[str]] = {}
    album_deleted: dict[int, set[str]] = {}
    rows = session.exec(select(PathSoftDelete)).all()
    for row in rows:
        if not row.target_path:
            continue
        normalized = normalize_stored_path(row.target_path)
        owner_id = row.owner_id
        if row.entity_type == "image" and owner_id is not None:
            image_deleted.setdefault(owner_id, set()).add(normalized)
        elif row.entity_type == "album" and owner_id is not None:
            album_deleted.setdefault(owner_id, set()).add(normalized)
    return image_deleted, album_deleted


def asset_visible(asset: ImageAsset, image_deleted: dict[int, set[str]]) -> bool:
    if asset.id is None:
        return True
    deleted_paths = image_deleted.get(asset.id, set())
    media_paths = [
        normalize_stored_path(p)
        for p in (asset.media_path or [])
        if isinstance(p, str) and p
    ]
    if not media_paths:
        return True
    return any(path not in deleted_paths for path in media_paths)


def album_visible(album: Album, album_deleted: dict[int, set[str]]) -> bool:
    if album.id is None:
        return True
    deleted_paths = album_deleted.get(album.id, set())
    return normalize_stored_path(album.path) not in deleted_paths