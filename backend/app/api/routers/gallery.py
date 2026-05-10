from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from sqlmodel import col, select

from app.api.common import AssetPreview, AssetPreviewResolver, build_preview_availability_index, date_group_media_predicate, pick_asset_media_path
from app.api.schemas import DateItem, GalleryItemsResponse, GalleryOverviewResponse
from app.db.session import get_session
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids
from app.services.recent_import_service import get_latest_recent_import_operation
from app.services.visible_album_service import album_has_visible_images, build_visible_album_stats, list_visible_assets

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


def _item_sort_key(name: str | None) -> str:
    return (name or "").casefold()


def _to_unix_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp())


def _pick_representative_asset(
    assets: list[ImageAsset],
    preview_resolver: AssetPreviewResolver,
) -> tuple[ImageAsset | None, AssetPreview | None]:
    cache_candidate: tuple[ImageAsset, AssetPreview] | None = None
    for asset in assets:
        preview = preview_resolver.resolve(asset)
        if preview.thumb_url:
            return asset, preview
        if cache_candidate is None and preview.cache_thumb_url:
            cache_candidate = (asset, preview)
    if cache_candidate is not None:
        return cache_candidate
    if not assets:
        return None, None
    asset = assets[0]
    return asset, preview_resolver.resolve(asset)


def _asset_time_sort_key(asset: ImageAsset) -> tuple[int, str, int]:
    ts = _to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at) or 0
    return ts, _item_sort_key(asset.full_filename), int(asset.id or 0)


def _build_image_item(
    asset: ImageAsset,
    preview_resolver: AssetPreviewResolver,
    media_predicate=None,
) -> DateItem | None:
    media_index, media_rel_path = pick_asset_media_path(asset, media_predicate)
    if media_index is None or not media_rel_path:
        return None
    preview = preview_resolver.resolve(asset)
    return DateItem(
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
        is_animated=bool(asset.is_animated),
        animation_meta=asset.normalized_animation_meta if asset.is_animated else None,
    )


def _build_album_item(
    album: Album,
    stats_by_public_id,
    preview_resolver: AssetPreviewResolver,
) -> DateItem:
    stats = stats_by_public_id.get(album.public_id or "")
    row_thumb_url = ""
    row_cache_thumb_url = None
    cover_asset = stats.cover_asset if stats else None
    cover_photo_id = cover_asset.id if cover_asset else None
    cover_width = cover_asset.width if cover_asset else None
    cover_height = cover_asset.height if cover_asset else None
    if cover_asset:
        cover_preview = preview_resolver.resolve(cover_asset)
        row_thumb_url = cover_preview.thumb_url
        row_cache_thumb_url = cover_preview.cache_thumb_url

    return DateItem(
        type="album",
        name=album.title,
        thumb_url=row_thumb_url,
        count=stats.subtree_photo_count if stats else 0,
        id=cover_photo_id,
        category_id=None,
        cache_thumb_url=row_cache_thumb_url,
        width=cover_width,
        height=cover_height,
        public_id=album.public_id,
        album_path=album.path,
        sort_ts=_to_unix_ts(album.updated_at or album.created_at),
        photo_count=stats.direct_photo_count if stats else 0,
        created_at=album.created_at,
        is_animated=bool(cover_asset.is_animated) if cover_asset else False,
        animation_meta=cover_asset.normalized_animation_meta if cover_asset and cover_asset.is_animated else None,
    )


def _build_direct_image_items(
    assets: list[ImageAsset],
    preview_resolver: AssetPreviewResolver,
) -> list[DateItem]:
    items: list[DateItem] = []
    for asset in assets:
        predicate = date_group_media_predicate(asset.date_group) if asset.date_group else None
        item = _build_image_item(asset, preview_resolver, predicate)
        if item is not None:
            items.append(item)
    return items


def _build_overview_items(
    assets: list[ImageAsset],
    preview_resolver: AssetPreviewResolver,
    *,
    limit: int,
) -> list[DateItem]:
    items: list[DateItem] = []
    for asset in sorted(assets, key=_asset_time_sort_key):
        item = _build_image_item(asset, preview_resolver)
        if item is not None:
            items.append(item)
        if len(items) >= limit:
            break
    return items


@router.get("/recent/overview", response_model=GalleryOverviewResponse)
def recent_overview(limit: int = Query(default=11, ge=1, le=60)) -> GalleryOverviewResponse:
    with get_session() as session:
        snapshot = get_latest_recent_import_operation(session)
        if snapshot is None:
            return GalleryOverviewResponse(scope="recent", total=0, items=[])

        active_category_ids = get_active_category_ids(session)
        visible_assets = list_visible_assets(session, active_category_ids)
        visible_asset_by_id = {
            int(asset.id): asset
            for asset in visible_assets
            if asset.id is not None
        }
        snapshot_image_ids = snapshot.successful_image_ids or snapshot.preview_image_ids or []
        preview_assets = [
            visible_asset_by_id[asset_id]
            for asset_id in snapshot_image_ids
            if asset_id in visible_asset_by_id
        ]
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())

        return GalleryOverviewResponse(
            scope="recent",
            total=len(preview_assets),
            items=_build_overview_items(preview_assets, preview_resolver, limit=limit),
        )


@router.get("/all/overview", response_model=GalleryOverviewResponse)
def all_overview(limit: int = Query(default=11, ge=1, le=60)) -> GalleryOverviewResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        visible_assets = list_visible_assets(session, active_category_ids)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())
        return GalleryOverviewResponse(
            scope="all",
            total=len(visible_assets),
            items=_build_overview_items(visible_assets, preview_resolver, limit=limit),
        )


@router.get("/recent/items", response_model=GalleryItemsResponse)
def recent_items() -> GalleryItemsResponse:
    with get_session() as session:
        snapshot = get_latest_recent_import_operation(session)
        if snapshot is None:
            return GalleryItemsResponse(scope="recent", items=[])

        active_category_ids = get_active_category_ids(session)
        visible_assets = list_visible_assets(session, active_category_ids)
        stats_by_public_id = build_visible_album_stats(session, visible_assets)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())

        visible_asset_by_id = {
            int(asset.id): asset
            for asset in visible_assets
            if asset.id is not None
        }
        direct_assets = [
            visible_asset_by_id[asset_id]
            for asset_id in (snapshot.direct_image_ids or [])
            if asset_id in visible_asset_by_id
        ]

        requested_public_ids = [
            public_id
            for public_id in (snapshot.top_album_public_ids or [])
            if isinstance(public_id, str) and public_id
        ]
        album_by_public_id = {
            album.public_id: album
            for album in session.exec(
                select(Album).where(Album.public_id.in_(requested_public_ids))  # type: ignore[arg-type]
            ).all()
            if album.public_id
        }
        albums = [
            album_by_public_id[public_id]
            for public_id in requested_public_ids
            if public_id in album_by_public_id and album_has_visible_images(album_by_public_id[public_id], stats_by_public_id)
        ]

        album_items = [_build_album_item(album, stats_by_public_id, preview_resolver) for album in albums]
        direct_items = _build_direct_image_items(direct_assets, preview_resolver)
        return GalleryItemsResponse(scope="recent", items=album_items + direct_items)


@router.get("/all/items", response_model=GalleryItemsResponse)
def all_items() -> GalleryItemsResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        visible_assets = list_visible_assets(session, active_category_ids)
        stats_by_public_id = build_visible_album_stats(session, visible_assets)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())

        album_image_ids: set[int] = set(session.exec(select(AlbumImage.image_id)).all())
        direct_assets = [
            asset for asset in visible_assets
            if asset.id is not None and asset.id not in album_image_ids
        ]
        top_albums = session.exec(
            select(Album)
            .where(Album.parent_id == None)  # noqa: E711
            .order_by(col(Album.title))
        ).all()
        top_albums = [
            album for album in top_albums
            if album_has_visible_images(album, stats_by_public_id)
        ]

        album_items = [_build_album_item(album, stats_by_public_id, preview_resolver) for album in top_albums]
        direct_items = _build_direct_image_items(direct_assets, preview_resolver)
        return GalleryItemsResponse(scope="all", items=album_items + direct_items)
