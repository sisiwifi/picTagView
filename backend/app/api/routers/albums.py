from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import (
    album_visible,
    asset_visible,
    build_soft_delete_maps,
    cache_thumb_url,
    resolve_stored_path,
    thumb_url,
)
from app.api.schemas import AlbumDetailResponse, AlbumInfo, AlbumItem, BreadcrumbItem
from app.core.config import CACHE_DIR, TEMP_DIR
from app.db.session import get_session
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset

router = APIRouter()


def _item_sort_key(name: str | None) -> str:
    return (name or "").casefold()


def _to_unix_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp())


def _build_album_response(album: Album, session) -> AlbumDetailResponse:
    """Shared logic for building album detail response."""
    image_deleted, album_deleted = build_soft_delete_maps(session)
    if not album_visible(album, album_deleted):
        raise HTTPException(status_code=404, detail="Album not found")

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
    sub_albums = [sa for sa in sub_albums if album_visible(sa, album_deleted)]

    sub_items: list[AlbumItem] = []
    for sa in sub_albums:
        row_thumb_url = ""
        row_cache_thumb_url = None
        cover_photo_id = None
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
            cache_thumb_url=row_cache_thumb_url,
            public_id=sa.public_id,
            album_path=sa.path,
            sort_ts=_to_unix_ts(sa.updated_at or sa.created_at),
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

    image_items: list[AlbumItem] = []
    for asset in album_assets:
        if not asset_visible(asset, image_deleted):
            continue
        thumb = thumb_url(asset)
        cache_thumb = cache_thumb_url(asset)
        image_items.append(AlbumItem(
            type="image",
            name=asset.full_filename or "",
            thumb_url=thumb,
            id=asset.id,
            cache_thumb_url=cache_thumb,
            sort_ts=_to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at),
            tags=asset.tags or [],
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
        album = session.exec(
            select(Album).where(Album.path == album_path)
        ).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        return _build_album_response(album, session)


@router.get("/api/albums/{album_id}", response_model=AlbumDetailResponse)
def album_detail(album_id: str) -> AlbumDetailResponse:
    with get_session() as session:
        album = session.exec(
            select(Album).where(Album.public_id == album_id)
        ).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        return _build_album_response(album, session)