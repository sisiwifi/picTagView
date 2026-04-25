import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.core.config import CACHE_DIR, PROJECT_ROOT, TEMP_DIR
from app.models.image_asset import ImageAsset


@dataclass(frozen=True)
class PreviewAvailabilityIndex:
    temp_file_names: frozenset[str]
    cache_file_names: frozenset[str]


@dataclass(frozen=True)
class AssetPreview:
    thumb_url: str = ""
    cache_thumb_url: Optional[str] = None


class AssetPreviewResolver:
    def __init__(self, availability_index: PreviewAvailabilityIndex):
        self._availability_index = availability_index
        self._cache: dict[int, AssetPreview] = {}

    def resolve(self, asset: ImageAsset) -> AssetPreview:
        cache_key = asset.id if asset.id is not None else id(asset)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        preview = resolve_asset_preview(asset, self._availability_index)
        self._cache[cache_key] = preview
        return preview


def resolve_stored_path(stored_path: Optional[str]) -> Optional[Path]:
    if not stored_path:
        return None
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def _list_file_names(directory: Path) -> frozenset[str]:
    try:
        with os.scandir(directory) as entries:
            return frozenset(entry.name for entry in entries if entry.is_file())
    except FileNotFoundError:
        return frozenset()


def build_preview_availability_index() -> PreviewAvailabilityIndex:
    return PreviewAvailabilityIndex(
        temp_file_names=_list_file_names(TEMP_DIR),
        cache_file_names=_list_file_names(CACHE_DIR),
    )


def _thumb_url_from_stored_path(
    stored_path: str,
    availability_index: PreviewAvailabilityIndex | None = None,
) -> str:
    resolved = resolve_stored_path(stored_path)
    if not resolved:
        return ""
    temp_dir = TEMP_DIR.resolve()
    try:
        resolved.relative_to(temp_dir)
    except ValueError:
        return ""
    if availability_index is None:
        if not resolved.exists():
            return ""
    elif resolved.name not in availability_index.temp_file_names:
        return ""
    return f"/thumbnails/{resolved.name}"


def thumb_url(
    asset: ImageAsset,
    availability_index: PreviewAvailabilityIndex | None = None,
) -> str:
    for thumb in asset.thumbs or []:
        if not isinstance(thumb, dict):
            continue
        p = thumb.get("path")
        if not isinstance(p, str) or not p:
            continue
        url = _thumb_url_from_stored_path(p, availability_index)
        if url:
            return url
    return ""


def cache_thumb_url(
    asset: ImageAsset,
    availability_index: PreviewAvailabilityIndex | None = None,
) -> Optional[str]:
    if not asset.file_hash:
        return None
    cache_name = f"{asset.file_hash}_cache.webp"
    if availability_index is None:
        cache_file = CACHE_DIR / cache_name
        if cache_file.exists():
            return f"/cache/{cache_name}"
        return None
    if cache_name in availability_index.cache_file_names:
        return f"/cache/{cache_name}"
    return None


def resolve_asset_preview(
    asset: ImageAsset,
    availability_index: PreviewAvailabilityIndex | None = None,
) -> AssetPreview:
    return AssetPreview(
        thumb_url=thumb_url(asset, availability_index),
        cache_thumb_url=cache_thumb_url(asset, availability_index),
    )


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
