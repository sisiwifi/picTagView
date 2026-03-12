import json
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlmodel import select

from app.api.schemas import (
    DateItem,
    DateItemsResponse,
    DateViewResponse,
    ImportResponse,
    MonthGroup,
    YearGroup,
)
from app.core.config import MEDIA_DIR
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.import_service import import_files, refresh_library

router = APIRouter()


@router.get("/")
def root() -> dict:
    return {"status": "ok"}


@router.post("/api/import", response_model=ImportResponse)
async def import_images(
    files: List[UploadFile] = File(...),
    last_modified_json: Optional[str] = Form(None),
) -> ImportResponse:
    """
    Import image files.  The frontend may send a JSON array of `file.lastModified`
    values (milliseconds since epoch) in `last_modified_json`, one per file in
    the same order.  These timestamps are used to derive the YYYY-M date group
    via min(ctime, mtime) semantics (matching groupByDate logic).
    """
    last_modified_times: Optional[List[Optional[int]]] = None
    if last_modified_json:
        try:
            last_modified_times = json.loads(last_modified_json)
        except Exception:
            last_modified_times = None

    result = await import_files(files, last_modified_times)
    return ImportResponse(**result)


@router.get("/api/images/count")
def images_count() -> dict:
    """Return the total number of imported image assets."""
    with get_session() as session:
        count = session.query(ImageAsset).count()
    return {"count": count}


@router.post("/api/admin/refresh")
def refresh() -> dict:
    """
    Refresh the media library:
    1. Prune DB records whose media file no longer exists (and remove their thumbnails).
    2. Repair: scan MEDIA_DIR for image files missing from DB or lacking thumbnails.
    Returns { pruned, repaired, errors }.
    """
    return refresh_library()


@router.get("/api/dates", response_model=DateViewResponse)
def dates_view() -> DateViewResponse:
    """
    Return all date groups (YYYY-M) grouped by year, each with:
    - image count
    - thumbnail URL of the first image in that group
    """
    with get_session() as session:
        assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group != None)  # noqa: E711
            .order_by(ImageAsset.id)
        ).all()

    # Build mapping: date_group -> list of assets
    group_map: dict[str, list[ImageAsset]] = defaultdict(list)
    for asset in assets:
        group_map[asset.date_group].append(asset)

    def sort_key(g: str):
        parts = g.split("-")
        return (int(parts[0]), int(parts[1]))

    sorted_groups = sorted(group_map.keys(), key=sort_key)

    year_map: dict[int, list[MonthGroup]] = defaultdict(list)
    for group in sorted_groups:
        parts = group.split("-")
        year, month = int(parts[0]), int(parts[1])
        group_assets = group_map[group]
        first_asset = group_assets[0]

        thumb_filename = Path(first_asset.thumb_path).name
        thumb_url = f"/thumbnails/{thumb_filename}"

        year_map[year].append(
            MonthGroup(
                group=group,
                year=year,
                month=month,
                count=len(group_assets),
                thumb_url=thumb_url,
            )
        )

    years = [
        YearGroup(year=y, months=year_map[y])
        for y in sorted(year_map.keys())
    ]

    return DateViewResponse(years=years)


@router.get("/api/dates/{date_group}/items", response_model=DateItemsResponse)
def date_group_items(date_group: str) -> DateItemsResponse:
    """
    Return the first-level contents of a date group:
    - Direct image files in media/<date_group>/  → type="image"
    - Top-level sub-directories (albums)          → type="album", represented
      by the first image in that sub-directory tree.

    Only one level of sub-directory nesting is surfaced (groupByDate behaviour).
    """
    with get_session() as session:
        assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group == date_group)  # noqa: E711
            .order_by(ImageAsset.id)
        ).all()

    if not assets:
        raise HTTPException(status_code=404, detail=f"No assets for {date_group}")

    media_base = MEDIA_DIR / date_group

    direct_items: list[DateItem] = []
    album_rep: dict[str, ImageAsset] = {}   # subdir → first asset
    album_count: dict[str, int] = {}         # subdir → image count

    for asset in assets:
        if not asset.media_path:
            continue
        media_path = Path(asset.media_path)
        try:
            rel = media_path.relative_to(media_base)
        except ValueError:
            # media_path not under expected base — skip
            continue

        parts = rel.parts
        if len(parts) == 1:
            # Direct image
            thumb_filename = Path(asset.thumb_path).name
            direct_items.append(
                DateItem(
                    type="image",
                    name=parts[0],
                    thumb_url=f"/thumbnails/{thumb_filename}",
                )
            )
        else:
            # Inside a sub-directory — record representative and count
            top_subdir = parts[0]
            if top_subdir not in album_rep:
                album_rep[top_subdir] = asset
                album_count[top_subdir] = 0
            album_count[top_subdir] += 1

    album_items: list[DateItem] = [
        DateItem(
            type="album",
            name=subdir,
            thumb_url=f"/thumbnails/{Path(asset.thumb_path).name}",
            count=album_count[subdir],
        )
        for subdir, asset in album_rep.items()
    ]

    return DateItemsResponse(
        date_group=date_group,
        items=direct_items + album_items,
    )
