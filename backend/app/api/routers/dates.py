from collections import defaultdict

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import album_not_deleted, cache_thumb_url, ia_not_deleted, resolve_stored_path, thumb_url
from app.api.schemas import DateItem, DateItemsResponse, DateViewResponse, MonthGroup, YearGroup
from app.core.config import CACHE_DIR, TEMP_DIR
from app.db.session import get_session
from app.models.album import Album
from app.models.image_asset import ImageAsset

router = APIRouter()


@router.get("/api/dates", response_model=DateViewResponse)
def dates_view() -> DateViewResponse:
    with get_session() as session:
        assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group != None)  # noqa: E711
            .where(ia_not_deleted())
            .order_by(col(ImageAsset.id))
        ).all()

        direct_map: dict[str, list[ImageAsset]] = defaultdict(list)
        for asset in assets:
            if asset.album:
                continue
            if asset.date_group:
                direct_map[asset.date_group].append(asset)

        top_albums = session.exec(
            select(Album)
            .where(Album.parent_id == None)  # noqa: E711
            .where(album_not_deleted())
            .where(Album.date_group != None)  # noqa: E711
        ).all()

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
        assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group == date_group)
            .where(ia_not_deleted())
            .order_by(col(ImageAsset.id))
        ).all()

        direct_items: list[DateItem] = []
        for asset in assets:
            if asset.album:
                continue
            if not asset.media_path:
                continue
            direct_items.append(
                DateItem(
                    type="image",
                    name=asset.full_filename or "",
                    thumb_url=thumb_url(asset),
                    id=asset.id,
                    cache_thumb_url=cache_thumb_url(asset),
                )
            )

        top_albums = session.exec(
            select(Album)
            .where(Album.date_group == date_group)
            .where(Album.parent_id == None)  # noqa: E711
            .where(album_not_deleted())
            .order_by(col(Album.title))
        ).all()

        album_items: list[DateItem] = []
        for album in top_albums:
            row_thumb_url = ""
            row_cache_thumb_url = None
            cover_photo_id = None
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
                    public_id=album.public_id,
                )
            )

    if not direct_items and not album_items:
        raise HTTPException(status_code=404, detail=f"No assets for {date_group}")

    return DateItemsResponse(date_group=date_group, items=direct_items + album_items)