import os
import subprocess
import sys
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import (
    AssetPreviewResolver,
    album_media_predicate,
    build_preview_availability_index,
    pick_asset_media_path,
)
from app.api.schemas import AlbumDetailResponse, AlbumInfo, AlbumItem, BreadcrumbItem, CoverSelectionRequest, CoverSelectionResponse
from app.core.config import MEDIA_DIR
from app.db.session import get_session
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids, is_category_visible
from app.services.cover_service import extract_cover_photo_id
from app.services.visible_album_service import album_has_visible_images, build_visible_album_stats, list_visible_assets, set_album_cover

router = APIRouter()


def _item_sort_key(name: str | None) -> str:
    return (name or "").casefold()


def _to_unix_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp())


def _build_album_response(album: Album, session, active_category_ids: set[int]) -> AlbumDetailResponse:
    """Shared logic for building album detail response."""
    visible_assets = list_visible_assets(session, active_category_ids, album.date_group)
    stats_by_public_id = build_visible_album_stats(session, visible_assets, album.date_group)
    preview_resolver = AssetPreviewResolver(build_preview_availability_index())

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
        if album_has_visible_images(sub_album, stats_by_public_id)
    ]

    sub_items: list[AlbumItem] = []
    for sa in sub_albums:
        row_thumb_url = ""
        row_cache_thumb_url = None
        stats = stats_by_public_id.get(sa.public_id or "")
        cover_asset = stats.cover_asset if stats else None
        cover_photo_id = cover_asset.id if cover_asset else None
        cover_width = cover_asset.width if cover_asset else None
        cover_height = cover_asset.height if cover_asset else None
        if cover_asset:
            cover_preview = preview_resolver.resolve(cover_asset)
            row_thumb_url = cover_preview.thumb_url
            row_cache_thumb_url = cover_preview.cache_thumb_url

        sub_items.append(AlbumItem(
            type="album",
            name=sa.title,
            thumb_url=row_thumb_url,
            count=stats.subtree_photo_count if stats else 0,
            id=cover_photo_id,
            category_id=None,
            cache_thumb_url=row_cache_thumb_url,
            width=cover_width,
            height=cover_height,
            public_id=sa.public_id,
            album_path=sa.path,
            sort_ts=_to_unix_ts(sa.updated_at or sa.created_at),
            photo_count=stats.direct_photo_count if stats else 0,
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

    album_stats = stats_by_public_id.get(album.public_id or "")
    if not album_stats or album_stats.subtree_photo_count <= 0:
        raise HTTPException(status_code=404, detail="Album not found")
    current_cover_photo_id = album_stats.cover_asset.id if album_stats.cover_asset else None

    image_items: list[AlbumItem] = []
    for asset in album_assets:
        media_index, media_rel_path = pick_asset_media_path(asset, album_media_predicate(album.path))
        if media_index is None or not media_rel_path:
            continue
        preview = preview_resolver.resolve(asset)
        image_items.append(AlbumItem(
            type="image",
            name=asset.full_filename or "",
            thumb_url=preview.thumb_url,
            id=asset.id,
            category_id=asset.category_id or DEFAULT_CATEGORY_ID,
            cache_thumb_url=preview.cache_thumb_url,
            width=asset.width,
            height=asset.height,
            sort_ts=_to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at),
            tags=asset.tags or [],
            file_size=asset.file_size,
            imported_at=asset.imported_at,
            file_created_at=asset.file_created_at,
            media_index=media_index,
            media_rel_path=media_rel_path,
            is_cover=bool(current_cover_photo_id is not None and asset.id == current_cover_photo_id),
        ))
    image_items.sort(key=lambda item: _item_sort_key(item.name))

    return AlbumDetailResponse(
        album=AlbumInfo(
            public_id=album.public_id,
            title=album.title,
            description=album.description,
            date_group=album.date_group,
            photo_count=album_stats.direct_photo_count,
            subtree_photo_count=album_stats.subtree_photo_count,
            cover_photo_id=current_cover_photo_id,
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
        return _build_album_response(album, session, active_category_ids)


@router.post("/api/albums/{album_id}/cover", response_model=CoverSelectionResponse)
def update_album_cover(album_id: str, body: CoverSelectionRequest) -> CoverSelectionResponse:
    with get_session() as session:
        album = session.exec(
            select(Album).where(Album.public_id == album_id)
        ).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")

        try:
            album = set_album_cover(session, album=album, image_id=body.image_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        session.commit()
        session.refresh(album)
        return CoverSelectionResponse(
            public_id=album.public_id or "",
            cover_photo_id=extract_cover_photo_id(album.cover),
            updated_at=album.updated_at or album.created_at,
        )