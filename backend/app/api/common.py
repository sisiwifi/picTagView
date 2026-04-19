from pathlib import Path
from typing import Callable, Optional

from app.core.config import CACHE_DIR, PROJECT_ROOT, TEMP_DIR
from app.models.image_asset import ImageAsset


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


def media_url(asset: ImageAsset) -> Optional[str]:
    for stored in (asset.media_path or []):
        if not isinstance(stored, str) or not stored:
            continue
        url = media_url_for_path(stored)
        if url:
            return url
    return None


def media_url_for_path(media_rel_path: Optional[str]) -> Optional[str]:
    if not media_rel_path:
        return None
    resolved = resolve_stored_path(media_rel_path)
    if not resolved or not resolved.exists():
        return None
    norm = normalize_stored_path(media_rel_path)
    if not norm.startswith("media/"):
        return None
    return f"/{norm}"


def normalize_stored_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def iter_asset_media_paths(asset: ImageAsset) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for index, stored in enumerate(asset.media_path or []):
        if not isinstance(stored, str) or not stored:
            continue
        normalized = normalize_stored_path(stored)
        if not normalized.startswith("media/"):
            continue
        items.append((index, normalized))
    return items


def pick_asset_media_path(
    asset: ImageAsset,
    predicate: Optional[Callable[[str], bool]] = None,
) -> tuple[Optional[int], Optional[str]]:
    fallback_index: Optional[int] = None
    fallback_path: Optional[str] = None
    for index, normalized in iter_asset_media_paths(asset):
        if fallback_path is None:
            fallback_index = index
            fallback_path = normalized
        if predicate is None or predicate(normalized):
            return index, normalized
    return fallback_index, fallback_path


def date_group_media_predicate(date_group: str) -> Callable[[str], bool]:
    prefix = f"media/{normalize_stored_path(date_group)}/"

    def _predicate(media_rel_path: str) -> bool:
        if not media_rel_path.startswith(prefix):
            return False
        remaining = media_rel_path[len(prefix):]
        return "/" not in remaining

    return _predicate


def album_media_predicate(album_path: str) -> Callable[[str], bool]:
    normalized_album_path = normalize_stored_path(album_path)
    prefix = f"media/{normalized_album_path}/"

    def _predicate(media_rel_path: str) -> bool:
        return media_rel_path.startswith(prefix)

    return _predicate
