from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, col, select

from app.models.album import Album
from app.models.image_asset import ImageAsset
from app.services.category_service import is_category_visible


@dataclass
class VisibleAlbumStats:
    direct_photo_count: int = 0
    subtree_photo_count: int = 0
    cover_asset: ImageAsset | None = None


def list_visible_assets(
    session: Session,
    active_category_ids: set[int],
    date_group: str | None = None,
) -> list[ImageAsset]:
    stmt = select(ImageAsset).order_by(col(ImageAsset.id))
    if date_group is not None:
        stmt = stmt.where(ImageAsset.date_group == date_group)
    assets = session.exec(stmt).all()
    return [
        asset for asset in assets
        if is_category_visible(asset.category_id, active_category_ids)
    ]


def build_visible_album_stats(
    session: Session,
    visible_assets: list[ImageAsset],
    date_group: str | None = None,
) -> dict[str, VisibleAlbumStats]:
    stmt = select(Album)
    if date_group is not None:
        stmt = stmt.where(Album.date_group == date_group)
    albums = session.exec(stmt).all()
    stats_by_public_id = {
        album.public_id: VisibleAlbumStats()
        for album in albums
        if album.public_id
    }

    for asset in visible_assets:
        filename = asset.full_filename or ""
        for chain in asset.album or []:
            if not isinstance(chain, list) or not chain:
                continue

            for public_id in chain:
                stats = stats_by_public_id.get(public_id)
                if stats is None:
                    continue
                stats.subtree_photo_count += 1
                cover_name = stats.cover_asset.full_filename or "" if stats.cover_asset else ""
                if stats.cover_asset is None or filename < cover_name:
                    stats.cover_asset = asset

            leaf_public_id = chain[-1]
            leaf_stats = stats_by_public_id.get(leaf_public_id)
            if leaf_stats is not None:
                leaf_stats.direct_photo_count += 1

    return stats_by_public_id


def album_has_visible_images(
    album: Album,
    stats_by_public_id: dict[str, VisibleAlbumStats],
) -> bool:
    if not album.public_id:
        return False
    stats = stats_by_public_id.get(album.public_id)
    return bool(stats and stats.subtree_photo_count > 0)