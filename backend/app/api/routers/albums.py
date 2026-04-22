import os
import subprocess
import sys
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import (
    album_media_predicate,
    cache_thumb_url,
    pick_asset_media_path,
    resolve_stored_path,
    thumb_url,
)
from app.api.schemas import AlbumDetailResponse, AlbumInfo, AlbumItem, BreadcrumbItem
from app.core.config import CACHE_DIR, MEDIA_DIR, TEMP_DIR
from app.db.session import get_session
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids, is_category_visible

router = APIRouter()


def _item_sort_key(name: str | None) -> str:
    return (name or "").casefold()


def _to_unix_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp())


def _is_album_visible(session, album: Album, active_category_ids: set[int]) -> bool:
    current = album
    while current:
        if not is_category_visible(current.category_id, active_category_ids):
            return False
        if current.parent_id is None:
            break
        current = session.get(Album, current.parent_id)
    return True


def _build_album_response(album: Album, session, active_category_ids: set[int]) -> AlbumDetailResponse:
    """Shared logic for building album detail response."""
    parent_public_id = None
    ancestors: list[BreadcrumbItem] = []
    cur = album
    while cur.parent_id is not None:
        par = session.get(Album, cur.parent_id)
        if not par:
            break
        ancestors.insert(0, BreadcrumbItem(public_id=par.public_id, title=par.title))
        if cur is album:
            parent_public_id = par.public_id
        cur = par

    sub_albums = session.exec(
        select(Album)
        .where(Album.parent_id == album.id)
        .order_by(col(Album.title))
    ).all()
    sub_albums = [
        sub_album for sub_album in sub_albums
        if _is_album_visible(session, sub_album, active_category_ids)
    ]

    sub_items: list[AlbumItem] = []
    for sa in sub_albums:
        row_thumb_url = ""
        row_cache_thumb_url = None
        cover_photo_id = None
        cover_width = None
        cover_height = None
        if sa.cover and isinstance(sa.cover, dict):
            cover_photo_id = sa.cover.get("photo_id")
            tp = sa.cover.get("thumb_path", "")
            if tp:
                resolved = resolve_stored_path(tp)
                if resolved and resolved.exists():
                    try:
                        resolved.relative_to(TEMP_DIR)
                        row_thumb_url = f"/thumbnails/{resolved.name}"
                    except ValueError:
                        try:
                            resolved.relative_to(CACHE_DIR)
                            row_cache_thumb_url = f"/cache/{resolved.name}"
                        except ValueError:
                            pass

        if cover_photo_id is not None:
            asset_for_cover = session.get(ImageAsset, cover_photo_id)
            if asset_for_cover:
                cover_width = asset_for_cover.width
                cover_height = asset_for_cover.height
                if not row_thumb_url:
                    row_thumb_url = thumb_url(asset_for_cover)
                if not row_cache_thumb_url:
                    row_cache_thumb_url = cache_thumb_url(asset_for_cover)

        sub_items.append(AlbumItem(
            type="album",
            name=sa.title,
            thumb_url=row_thumb_url,
            count=sa.subtree_photo_count,
            id=cover_photo_id,
            category_id=sa.category_id or DEFAULT_CATEGORY_ID,
            cache_thumb_url=row_cache_thumb_url,
            width=cover_width,
            height=cover_height,
            public_id=sa.public_id,
            album_path=sa.path,
            sort_ts=_to_unix_ts(sa.updated_at or sa.created_at),
            photo_count=sa.photo_count,
            created_at=sa.created_at,
        ))
    sub_items.sort(key=lambda item: _item_sort_key(item.name))

    # Use album_image mapping table instead of scanning all ImageAssets
    album_assets = session.exec(
        select(ImageAsset)
        .where(
            ImageAsset.id.in_(  # type: ignore[union-attr]
                select(AlbumImage.image_id).where(AlbumImage.album_id == album.id)
            )
        )
        .order_by(col(ImageAsset.id))
    ).all()
    album_assets = [
        asset for asset in album_assets
        if is_category_visible(asset.category_id, active_category_ids)
    ]

    image_items: list[AlbumItem] = []
    for asset in album_assets:
        media_index, media_rel_path = pick_asset_media_path(asset, album_media_predicate(album.path))
        if media_index is None or not media_rel_path:
            continue
        thumb = thumb_url(asset)
        cache_thumb = cache_thumb_url(asset)
        image_items.append(AlbumItem(
            type="image",
            name=asset.full_filename or "",
            thumb_url=thumb,
            id=asset.id,
            category_id=asset.category_id or DEFAULT_CATEGORY_ID,
            cache_thumb_url=cache_thumb,
            width=asset.width,
            height=asset.height,
            sort_ts=_to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at),
            tags=asset.tags or [],
            file_size=asset.file_size,
            imported_at=asset.imported_at,
            file_created_at=asset.file_created_at,
            media_index=media_index,
            media_rel_path=media_rel_path,
        ))
    image_items.sort(key=lambda item: _item_sort_key(item.name))

    return AlbumDetailResponse(
        album=AlbumInfo(
            public_id=album.public_id,
            title=album.title,
            description=album.description,
            date_group=album.date_group,
            photo_count=album.photo_count,
            subtree_photo_count=album.subtree_photo_count,
            parent_public_id=parent_public_id,
            ancestors=ancestors,
        ),
        items=sub_items + image_items,
    )


@router.get("/api/albums/by-path/{album_path:path}", response_model=AlbumDetailResponse)
def album_by_path(album_path: str) -> AlbumDetailResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        album = session.exec(
            select(Album).where(Album.path == album_path)
        ).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        if not _is_album_visible(session, album, active_category_ids):
            raise HTTPException(status_code=404, detail="Album not found")
        return _build_album_response(album, session, active_category_ids)


@router.get("/api/albums/open-by-path/{album_path:path}")
def open_album_by_path(album_path: str) -> dict:
    target = (MEDIA_DIR / album_path).resolve()
    media_root = MEDIA_DIR.resolve()

    try:
        target.relative_to(media_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Album path is invalid") from exc

    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Album directory not found")

    if sys.platform == "win32":
        os.startfile(str(target))
        return {"status": "ok", "mode": "system", "path": str(target)}
    if sys.platform == "darwin":
        subprocess.run(["open", str(target)], check=False)
    else:
        subprocess.run(["xdg-open", str(target)], check=False)

    return {"status": "ok", "mode": "system", "path": str(target)}


@router.get("/api/albums/{album_id}", response_model=AlbumDetailResponse)
def album_detail(album_id: str) -> AlbumDetailResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        album = session.exec(
            select(Album).where(Album.public_id == album_id)
        ).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        if not _is_album_visible(session, album, active_category_ids):
            raise HTTPException(status_code=404, detail="Album not found")
        return _build_album_response(album, session, active_category_ids)