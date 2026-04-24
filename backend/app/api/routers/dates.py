from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import exists
from sqlmodel import col, select

from app.api.common import (
    cache_thumb_url,
    date_group_media_predicate,
    pick_asset_media_path,
    resolve_stored_path,
    thumb_url,
)
from app.api.schemas import DateItem, DateItemsResponse, DateViewResponse, MonthGroup, YearGroup
from app.core.config import CACHE_DIR, TEMP_DIR
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


@router.get("/api/dates", response_model=DateViewResponse)
def dates_view() -> DateViewResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        assets = list_visible_assets(session, active_category_ids)
        stats_by_public_id = build_visible_album_stats(session, assets)

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

            rep = next((a for a in direct_assets if thumb_url(a)), None)
            if not rep:
                rep = next((a for a in direct_assets if cache_thumb_url(a)), None)
            if not rep and direct_assets:
                rep = direct_assets[0]

            if rep:
                cover_id = rep.id
                row_thumb_url = thumb_url(rep)
                if not row_thumb_url:
                    row_cache_thumb_url = cache_thumb_url(rep)
            else:
                for album in group_albums:
                    stats = stats_by_public_id.get(album.public_id or "")
                    cover_asset = stats.cover_asset if stats else None
                    if cover_asset:
                        cover_id = cover_asset.id
                        row_thumb_url = thumb_url(cover_asset)
                        if not row_thumb_url:
                            row_cache_thumb_url = cache_thumb_url(cover_asset)
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
            thumb = thumb_url(asset)
            cache_thumb = cache_thumb_url(asset)
            direct_items.append(
                DateItem(
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
                row_thumb_url = thumb_url(cover_asset)
                row_cache_thumb_url = cache_thumb_url(cover_asset)

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