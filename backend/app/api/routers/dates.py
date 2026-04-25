from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import (
    AssetPreview,
    AssetPreviewResolver,
    build_preview_availability_index,
    date_group_media_predicate,
    pick_asset_media_path,
)
from app.api.schemas import DateItem, DateItemsResponse, DateViewResponse, MonthGroup, YearGroup
from app.db.session import get_session
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids, is_category_visible
from app.services.visible_album_service import album_has_visible_images, build_visible_album_stats, list_visible_assets

router = APIRouter()


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


@router.get("/api/dates", response_model=DateViewResponse)
def dates_view() -> DateViewResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        assets = list_visible_assets(session, active_category_ids)
        stats_by_public_id = build_visible_album_stats(session, assets)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())

        # Build set of image IDs that belong to any album via album_image table
        album_image_ids: set[int] = set(
            session.exec(select(AlbumImage.image_id)).all()
        )

        direct_map: dict[str, list[ImageAsset]] = defaultdict(list)
        for asset in assets:
            if asset.id is not None and asset.id in album_image_ids:
                continue
            if asset.date_group:
                direct_map[asset.date_group].append(asset)

        top_albums = session.exec(
            select(Album)
            .where(Album.parent_id == None)  # noqa: E711
            .where(Album.date_group != None)  # noqa: E711
        ).all()
        top_albums = [
            album for album in top_albums
            if album_has_visible_images(album, stats_by_public_id)
        ]

        album_map: dict[str, list[Album]] = defaultdict(list)
        for album in top_albums:
            if album.date_group:
                album_map[album.date_group].append(album)

        all_groups = sorted(
            set(direct_map.keys()) | set(album_map.keys()),
            key=lambda g: (int(g.split("-")[0]), int(g.split("-")[1])),
        )

        year_map: dict[int, list[MonthGroup]] = defaultdict(list)
        for group in all_groups:
            parts = group.split("-")
            year, month = int(parts[0]), int(parts[1])

            direct_assets = direct_map.get(group, [])
            group_albums = album_map.get(group, [])

            count = len(direct_assets) + sum(
                (stats_by_public_id.get(album.public_id or "").subtree_photo_count if stats_by_public_id.get(album.public_id or "") else 0)
                for album in group_albums
            )
            if count == 0:
                continue

            row_thumb_url = ""
            row_cache_thumb_url = None
            cover_id = None

            rep, rep_preview = _pick_representative_asset(direct_assets, preview_resolver)

            if rep:
                cover_id = rep.id
                row_thumb_url = rep_preview.thumb_url if rep_preview else ""
                row_cache_thumb_url = None if row_thumb_url else (rep_preview.cache_thumb_url if rep_preview else None)
            else:
                for album in group_albums:
                    stats = stats_by_public_id.get(album.public_id or "")
                    cover_asset = stats.cover_asset if stats else None
                    if cover_asset:
                        cover_preview = preview_resolver.resolve(cover_asset)
                        cover_id = cover_asset.id
                        row_thumb_url = cover_preview.thumb_url
                        row_cache_thumb_url = None if row_thumb_url else cover_preview.cache_thumb_url
                        if row_thumb_url or row_cache_thumb_url:
                            break

            year_map[year].append(
                MonthGroup(
                    group=group,
                    year=year,
                    month=month,
                    count=count,
                    thumb_url=row_thumb_url,
                    cache_thumb_url=row_cache_thumb_url,
                    id=cover_id,
                )
            )

    years = [YearGroup(year=y, months=year_map[y]) for y in sorted(year_map.keys())]
    return DateViewResponse(years=years)


@router.get("/api/dates/{date_group}/items", response_model=DateItemsResponse)
def date_group_items(date_group: str) -> DateItemsResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        assets = list_visible_assets(session, active_category_ids, date_group)
        stats_by_public_id = build_visible_album_stats(session, assets, date_group)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())

        # Build set of image IDs that belong to any album via album_image table
        album_image_ids: set[int] = set(
            session.exec(
                select(AlbumImage.image_id)
                .where(AlbumImage.image_id.in_(  # type: ignore[union-attr]
                    select(ImageAsset.id).where(ImageAsset.date_group == date_group)
                ))
            ).all()
        )

        direct_items: list[DateItem] = []
        for asset in assets:
            if asset.id is not None and asset.id in album_image_ids:
                continue
            media_index, media_rel_path = pick_asset_media_path(asset, date_group_media_predicate(date_group))
            if media_index is None or not media_rel_path:
                continue
            preview = preview_resolver.resolve(asset)
            direct_items.append(
                DateItem(
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
                )
            )
        direct_items.sort(key=lambda item: _item_sort_key(item.name))

        top_albums = session.exec(
            select(Album)
            .where(Album.date_group == date_group)
            .where(Album.parent_id == None)  # noqa: E711
            .order_by(col(Album.title))
        ).all()
        top_albums = [
            album for album in top_albums
            if album_has_visible_images(album, stats_by_public_id)
        ]

        album_items: list[DateItem] = []
        for album in top_albums:
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

            album_items.append(
                DateItem(
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
                )
            )
        album_items.sort(key=lambda item: _item_sort_key(item.name))

    if not direct_items and not album_items:
        raise HTTPException(status_code=404, detail=f"No assets for {date_group}")

    return DateItemsResponse(date_group=date_group, items=album_items + direct_items)