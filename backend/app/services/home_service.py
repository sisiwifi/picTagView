from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.api.common import AssetPreviewResolver, build_preview_availability_index, pick_asset_media_path
from app.models.image_asset import ImageAsset
from app.models.tag import Tag
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids
from app.services.visible_album_service import list_visible_assets

_DRAFT_CREATED_BY = "system:draft-reserve"


@dataclass(frozen=True)
class HomeTagAggregate:
    tag: Tag
    visible_usage_count: int


@dataclass(frozen=True)
class HomeCoverCandidate:
    asset_id: int
    cover: dict
    has_preview: bool


def _datetime_sort_value(value: datetime | None) -> int:
    if value is None:
        return 0
    return int(value.timestamp())


def _last_used_sort_value(value: object) -> int:
    text = str(value or "").strip()
    if not text.isdigit():
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _asset_sort_key(asset: ImageAsset) -> tuple[int, int]:
    return (
        _datetime_sort_value(asset.file_created_at or asset.imported_at or asset.created_at),
        int(asset.id or 0),
    )


def _tag_sort_key(aggregate: HomeTagAggregate) -> tuple[int, int, int, str, int]:
    label = str(aggregate.tag.display_name or aggregate.tag.name or "").casefold()
    return (
        -aggregate.visible_usage_count,
        -_last_used_sort_value(aggregate.tag.last_used_at),
        -_datetime_sort_value(aggregate.tag.updated_at),
        label,
        -(aggregate.tag.id or 0),
    )


def _serialize_tag(tag: Tag) -> dict:
    return {
        "id": tag.id,
        "public_id": tag.public_id,
        "name": tag.name,
        "display_name": tag.display_name,
        "type": tag.type,
        "description": tag.description,
        "usage_count": tag.usage_count,
        "last_used_at": tag.last_used_at,
        "metadata": dict(tag.metadata_ or {}),
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        "created_by": tag.created_by,
        "updated_at": tag.updated_at.isoformat() if tag.updated_at else None,
    }


def _build_cover_candidate(asset: ImageAsset, preview_resolver: AssetPreviewResolver) -> HomeCoverCandidate | None:
    if asset.id is None:
        return None

    media_index, media_rel_path = pick_asset_media_path(asset)
    if media_index is None or not media_rel_path:
        return None

    preview = preview_resolver.resolve(asset)
    return HomeCoverCandidate(
        asset_id=int(asset.id),
        cover={
            "type": "image",
            "id": int(asset.id),
            "name": asset.full_filename or "",
            "thumb_url": preview.thumb_url,
            "cache_thumb_url": preview.cache_thumb_url,
            "width": asset.width,
            "height": asset.height,
            "category_id": asset.category_id or DEFAULT_CATEGORY_ID,
            "media_index": media_index,
            "media_rel_path": media_rel_path,
            "tags": [tag_id for tag_id in (asset.tags or []) if isinstance(tag_id, int)],
            "imported_at": asset.imported_at.isoformat() if asset.imported_at else None,
            "file_created_at": asset.file_created_at.isoformat() if asset.file_created_at else None,
            "is_animated": bool(asset.is_animated),
            "animation_meta": asset.normalized_animation_meta if asset.is_animated else None,
        },
        has_preview=bool(preview.thumb_url or preview.cache_thumb_url),
    )


def _candidate_allowed(asset_id: int, selected_cover_ids: set[int], recent_excluded_ids: set[int], tier: int) -> bool:
    if tier == 0:
        return asset_id not in selected_cover_ids and asset_id not in recent_excluded_ids
    if tier == 1:
        return asset_id not in selected_cover_ids
    if tier == 2:
        return asset_id not in recent_excluded_ids
    return True


def _pick_cover_candidate(
    assets: tuple[ImageAsset, ...],
    preview_resolver: AssetPreviewResolver,
    *,
    selected_cover_ids: set[int],
    recent_excluded_ids: set[int],
) -> HomeCoverCandidate | None:
    candidates = [
        candidate
        for candidate in (_build_cover_candidate(asset, preview_resolver) for asset in assets)
        if candidate is not None
    ]
    if not candidates:
        return None

    preview_candidates = [candidate for candidate in candidates if candidate.has_preview]
    fallback_candidates = [candidate for candidate in candidates if not candidate.has_preview]

    for bucket in (preview_candidates, fallback_candidates):
        if not bucket:
            continue
        for tier in range(4):
            for candidate in bucket:
                if _candidate_allowed(candidate.asset_id, selected_cover_ids, recent_excluded_ids, tier):
                    return candidate
    return candidates[0]


def _normalize_recent_excluded_ids(values: Iterable[int] | None) -> set[int]:
    normalized: set[int] = set()
    for value in values or []:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            normalized.add(parsed)
    return normalized


def _build_tag_usage_counts(visible_assets: list[ImageAsset]) -> tuple[list[ImageAsset], dict[int, int]]:
    sorted_visible_assets = sorted(visible_assets, key=_asset_sort_key, reverse=True)
    counts_by_tag_id: dict[int, int] = {}
    for asset in sorted_visible_assets:
        for tag_id in (asset.tags or []):
            if not isinstance(tag_id, int):
                continue
            counts_by_tag_id[tag_id] = counts_by_tag_id.get(tag_id, 0) + 1

    return sorted_visible_assets, counts_by_tag_id


def _build_tag_aggregates(session: Session, counts_by_tag_id: dict[int, int]) -> list[HomeTagAggregate]:
    if not counts_by_tag_id:
        return []

    tags = session.exec(
        select(Tag)
        .where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]
        .where(col(Tag.id).in_(counts_by_tag_id.keys()))
    ).all()

    aggregates = [
        HomeTagAggregate(
            tag=tag,
            visible_usage_count=counts_by_tag_id[int(tag.id)],
        )
        for tag in tags
        if tag.id is not None and counts_by_tag_id.get(int(tag.id), 0) > 0
    ]
    return sorted(aggregates, key=_tag_sort_key)


def _collect_page_assets_by_tag(
    sorted_visible_assets: list[ImageAsset],
    page_tag_ids: set[int],
) -> dict[int, tuple[ImageAsset, ...]]:
    if not page_tag_ids:
        return {}

    assets_by_tag_id: dict[int, list[ImageAsset]] = {}
    for asset in sorted_visible_assets:
        for tag_id in (asset.tags or []):
            if not isinstance(tag_id, int) or tag_id not in page_tag_ids:
                continue
            assets_by_tag_id.setdefault(tag_id, []).append(asset)

    return {
        tag_id: tuple(items)
        for tag_id, items in assets_by_tag_id.items()
    }


def build_home_overview(
    session: Session,
    *,
    limit: int,
    offset: int,
    exclude_image_ids: Iterable[int] | None = None,
) -> dict:
    active_category_ids = get_active_category_ids(session)
    visible_assets = list_visible_assets(session, active_category_ids)
    visible_image_count = len(visible_assets)

    global_tag_count = int(session.exec(
        select(func.count())
        .select_from(Tag)
        .where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]
    ).one() or 0)

    recent_excluded_ids = _normalize_recent_excluded_ids(exclude_image_ids)
    sorted_visible_assets, counts_by_tag_id = _build_tag_usage_counts(visible_assets)
    tag_aggregates = _build_tag_aggregates(session, counts_by_tag_id)
    total_visible_tags = len(tag_aggregates)
    page_aggregates = tag_aggregates[offset:offset + limit]
    page_assets_by_tag_id = _collect_page_assets_by_tag(
        sorted_visible_assets,
        {
            int(aggregate.tag.id)
            for aggregate in page_aggregates
            if aggregate.tag.id is not None
        },
    )

    preview_resolver = AssetPreviewResolver(build_preview_availability_index())
    selected_cover_ids: set[int] = set()
    items: list[dict] = []
    for aggregate in page_aggregates:
        tag_id = int(aggregate.tag.id) if aggregate.tag.id is not None else 0
        cover_candidate = _pick_cover_candidate(
            page_assets_by_tag_id.get(tag_id, ()),
            preview_resolver,
            selected_cover_ids=selected_cover_ids,
            recent_excluded_ids=recent_excluded_ids,
        )
        if cover_candidate is not None:
            selected_cover_ids.add(cover_candidate.asset_id)
        items.append({
            "tag": _serialize_tag(aggregate.tag),
            "visible_usage_count": aggregate.visible_usage_count,
            "cover": cover_candidate.cover if cover_candidate is not None else None,
        })

    return {
        "stats": {
            "visible_image_count": visible_image_count,
            "global_tag_count": global_tag_count,
            "visible_tag_count": total_visible_tags,
        },
        "tag_wall": {
            "offset": offset,
            "limit": limit,
            "total": total_visible_tags,
            "has_more": offset + len(items) < total_visible_tags,
            "items": items,
        },
    }