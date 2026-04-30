from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, col, select

from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.services.category_service import is_category_visible
from app.services.cover_service import build_asset_cover_payload, extract_cover_photo_id


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
    preferred_cover_photo_ids = {
        album.public_id: extract_cover_photo_id(album.cover)
        for album in albums
        if album.public_id
    }
    preferred_cover_assets: dict[str, ImageAsset] = {}

    for asset in visible_assets:
        filename = asset.full_filename or ""
        asset_id = asset.id
        for chain in asset.album or []:
            if not isinstance(chain, list) or not chain:
                continue

            for public_id in chain:
                stats = stats_by_public_id.get(public_id)
                if stats is None:
                    continue
                stats.subtree_photo_count += 1
                if asset_id is not None and preferred_cover_photo_ids.get(public_id) == asset_id:
                    preferred_cover_assets[public_id] = asset
                cover_name = stats.cover_asset.full_filename or "" if stats.cover_asset else ""
                if stats.cover_asset is None or filename < cover_name:
                    stats.cover_asset = asset

            leaf_public_id = chain[-1]
            leaf_stats = stats_by_public_id.get(leaf_public_id)
            if leaf_stats is not None:
                leaf_stats.direct_photo_count += 1

    for public_id, asset in preferred_cover_assets.items():
        stats = stats_by_public_id.get(public_id)
        if stats is not None:
            stats.cover_asset = asset

    return stats_by_public_id


def album_has_visible_images(
    album: Album,
    stats_by_public_id: dict[str, VisibleAlbumStats],
) -> bool:
    if not album.public_id:
        return False
    stats = stats_by_public_id.get(album.public_id)
    return bool(stats and stats.subtree_photo_count > 0)


def set_album_cover(
    session: Session,
    *,
    album: Album,
    image_id: int,
) -> Album:
    if album.id is None:
        raise ValueError("album 未持久化")

    relation = session.exec(
        select(AlbumImage)
        .where(AlbumImage.album_id == album.id)
        .where(AlbumImage.image_id == image_id)
    ).first()
    if relation is None:
        raise ValueError("图片不在当前相册中")

    asset = session.get(ImageAsset, image_id)
    if asset is None:
        raise ValueError("图片不存在")

    album.cover = build_asset_cover_payload(asset, manual=True)
    album.updated_at = datetime.now()
    session.add(album)
    session.flush()
    return album