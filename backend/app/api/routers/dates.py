from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import exists
from sqlmodel import col, select

from app.api.common import (
    album_visible,
    asset_visible,
    build_soft_delete_maps,
    cache_thumb_url,
    resolve_stored_path,
    thumb_url,
)
from app.api.schemas import DateItem, DateItemsResponse, DateViewResponse, MonthGroup, YearGroup
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


@router.get("/api/dates", response_model=DateViewResponse)
def dates_view() -> DateViewResponse:
    with get_session() as session:
        all_assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group != None)  # noqa: E711
            .order_by(col(ImageAsset.id))
        ).all()
        image_deleted, album_deleted = build_soft_delete_maps(session)
        assets = [asset for asset in all_assets if asset_visible(asset, image_deleted)]

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
        top_albums = [album for album in top_albums if album_visible(album, album_deleted)]

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

            count = len(direct_assets) + sum(a.subtree_photo_count or 0 for a in group_albums)
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
                    cover_photo_id = None
                    if album.cover and isinstance(album.cover, dict):
                        cover_photo_id = album.cover.get("photo_id")
                    if cover_photo_id is not None:
                        asset_for_cover = session.get(ImageAsset, cover_photo_id)
                        if asset_for_cover:
                            cover_id = asset_for_cover.id
                            row_thumb_url = thumb_url(asset_for_cover)
                            if not row_thumb_url:
                                row_cache_thumb_url = cache_thumb_url(asset_for_cover)
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
        all_assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group == date_group)
            .order_by(col(ImageAsset.id))
        ).all()
        image_deleted, album_deleted = build_soft_delete_maps(session)
        assets = [asset for asset in all_assets if asset_visible(asset, image_deleted)]

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
            if not asset.media_path:
                continue
            thumb = thumb_url(asset)
            cache_thumb = cache_thumb_url(asset)
            direct_items.append(
                DateItem(
                    type="image",
                    name=asset.full_filename or "",
                    thumb_url=thumb,
                    id=asset.id,
                    cache_thumb_url=cache_thumb,
                    width=asset.width,
                    height=asset.height,
                    sort_ts=_to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at),
                    tags=asset.tags or [],
                    file_size=asset.file_size,
                    imported_at=asset.imported_at,
                    file_created_at=asset.file_created_at,
                )
            )
        direct_items.sort(key=lambda item: _item_sort_key(item.name))

        top_albums = session.exec(
            select(Album)
            .where(Album.date_group == date_group)
            .where(Album.parent_id == None)  # noqa: E711
            .order_by(col(Album.title))
        ).all()
        top_albums = [album for album in top_albums if album_visible(album, album_deleted)]

        album_items: list[DateItem] = []
        for album in top_albums:
            row_thumb_url = ""
            row_cache_thumb_url = None
            cover_photo_id = None
            cover_width = None
            cover_height = None
            if album.cover and isinstance(album.cover, dict):
                cover_photo_id = album.cover.get("photo_id")
                tp = album.cover.get("thumb_path", "")
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

            album_items.append(
                DateItem(
                    type="album",
                    name=album.title,
                    thumb_url=row_thumb_url,
                    count=album.subtree_photo_count,
                    id=cover_photo_id,
                    cache_thumb_url=row_cache_thumb_url,
                    width=cover_width,
                    height=cover_height,
                    public_id=album.public_id,
                    album_path=album.path,
                    sort_ts=_to_unix_ts(album.updated_at or album.created_at),
                )
            )
        album_items.sort(key=lambda item: _item_sort_key(item.name))

    if not direct_items and not album_items:
        raise HTTPException(status_code=404, detail=f"No assets for {date_group}")

    return DateItemsResponse(date_group=date_group, items=album_items + direct_items)