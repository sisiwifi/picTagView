from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import select

from app.api.common import (
    AssetPreviewResolver,
    build_preview_availability_index,
    normalize_stored_path,
    pick_asset_media_path,
)
from app.api.schemas import SearchImageItem, SearchImageResponse, TagBriefItem
from app.db.session import get_session
from app.models.tag import Tag
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids
from app.services.visible_album_service import list_visible_assets

router = APIRouter(prefix="/api/search", tags=["search"])

_DRAFT_CREATED_BY = "system:draft-reserve"
_SUPPORTED_MODES = {"auto", "filename", "tag", "path"}
_IMAGE_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".avif",
)


def _to_tag_brief(tag: Tag) -> TagBriefItem:
    metadata = tag.metadata_ if isinstance(tag.metadata_, dict) else {}
    color = metadata.get("color") if isinstance(metadata.get("color"), str) else ""
    border_color = metadata.get("border_color") if isinstance(metadata.get("border_color"), str) else ""
    background_color = metadata.get("background_color") if isinstance(metadata.get("background_color"), str) else ""
    return TagBriefItem(
        id=int(tag.id or 0),
        name=tag.name or "",
        display_name=tag.display_name or tag.name or "",
        color=color,
        border_color=border_color,
        background_color=background_color,
    )


def _normalize_mode(mode: str) -> str:
    normalized = str(mode or "auto").strip().lower()
    return normalized if normalized in _SUPPORTED_MODES else "auto"


def _looks_like_path_query(raw_query: str) -> bool:
    normalized = normalize_stored_path(raw_query).casefold()
    if normalized.startswith("media/"):
        return True
    if "/media/" in normalized:
        return True
    return "/" in normalized and normalized.endswith(_IMAGE_SUFFIXES)


def _normalize_path_query(raw_query: str) -> str:
    normalized = normalize_stored_path(raw_query).strip()
    if not normalized:
        return ""

    lowered = normalized.casefold()
    marker = "/media/"
    if marker in lowered and not lowered.startswith("media/"):
        marker_index = lowered.index(marker)
        normalized = normalized[marker_index + 1:]
        lowered = normalized.casefold()

    normalized = normalized.lstrip("/")
    if lowered.startswith("media/"):
        return normalized
    return f"media/{normalized}"


def _filename_match_rank(name: str, query: str) -> int:
    lowered_name = name.casefold()
    if lowered_name == query:
        return 0
    if lowered_name.startswith(query):
        return 1
    return 2


def _tag_match_rank(tag_names: list[str], query: str) -> int:
    best = 2
    for name in tag_names:
        lowered_name = name.casefold()
        if lowered_name == query:
            return 0
        if lowered_name.startswith(query):
            best = min(best, 1)
    return best


def _build_search_item(asset, preview_resolver: AssetPreviewResolver, tags_by_id: dict[int, Tag], matched_by: list[str], matched_tag_ids: list[int] | None = None, media_rel_path: str | None = None) -> SearchImageItem | None:
    if asset.id is None:
        return None

    _media_index, fallback_media_path = pick_asset_media_path(asset)
    preview = preview_resolver.resolve(asset)
    return SearchImageItem(
        id=int(asset.id),
        name=asset.full_filename or "",
        category_id=asset.category_id or DEFAULT_CATEGORY_ID,
        width=asset.width,
        height=asset.height,
        tags=[tag_id for tag_id in (asset.tags or []) if isinstance(tag_id, int)],
        thumb_url=preview.thumb_url,
        cache_thumb_url=preview.cache_thumb_url,
        media_rel_path=media_rel_path or fallback_media_path,
        date_group=asset.date_group,
        quick_hash=asset.quick_hash,
        matched_by=matched_by,
        matched_tags=[
            _to_tag_brief(tags_by_id[tag_id])
            for tag_id in (matched_tag_ids or [])
            if tag_id in tags_by_id
        ],
    )


@router.get("/images", response_model=SearchImageResponse)
def search_images(
    q: str = Query(..., min_length=1, description="搜索关键字或图片路径"),
    mode: str = Query(default="auto", description="auto | filename | tag | path"),
    limit: int = Query(default=120, ge=1, le=400),
) -> SearchImageResponse:
    query = str(q or "").strip()
    requested_mode = _normalize_mode(mode)
    if not query:
        return SearchImageResponse(query="", requested_mode=requested_mode, resolved_mode=requested_mode, limit=limit)

    query_lower = query.casefold()

    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        assets = list_visible_assets(session, active_category_ids)
        tags = session.exec(
            select(Tag).where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]
        ).all()

    tags_by_id = {
        int(tag.id): tag
        for tag in tags
        if tag.id is not None
    }
    preview_resolver = AssetPreviewResolver(build_preview_availability_index())

    resolved_mode = requested_mode
    if requested_mode == "auto":
        resolved_mode = "path" if _looks_like_path_query(query) else "mixed"

    result_map: dict[int, dict] = {}
    source_media_rel_path: str | None = None
    source_quick_hash: str | None = None

    if resolved_mode == "path":
        normalized_path = _normalize_path_query(query)
        source_asset = None
        for asset in assets:
            for _media_index, asset_path in enumerate(asset.media_path or []):
                if not isinstance(asset_path, str) or not asset_path:
                    continue
                candidate = normalize_stored_path(asset_path)
                if candidate == normalized_path:
                    source_asset = asset
                    source_media_rel_path = candidate
                    source_quick_hash = asset.quick_hash
                    break
            if source_asset is not None:
                break

        if source_asset is not None:
            for asset in assets:
                if asset.id is None:
                    continue
                matched_by: list[str] = []
                if source_quick_hash and asset.quick_hash == source_quick_hash:
                    matched_by.append("quick_hash")
                if asset.id == source_asset.id:
                    matched_by.insert(0, "path")
                if not matched_by:
                    continue
                selected_path = source_media_rel_path if asset.id == source_asset.id else None
                item = _build_search_item(asset, preview_resolver, tags_by_id, matched_by, media_rel_path=selected_path)
                if item is None:
                    continue
                result_map[item.id] = {
                    "item": item,
                    "priority": 0 if asset.id == source_asset.id else 1,
                    "name": item.name.casefold(),
                }

    else:
        for asset in assets:
            if asset.id is None:
                continue

            matched_by: list[str] = []
            matched_tag_ids: list[int] = []
            filename_rank = 9
            tag_rank = 9

            filename = str(asset.full_filename or "")
            if resolved_mode in {"filename", "mixed"} and filename and query_lower in filename.casefold():
                matched_by.append("filename")
                filename_rank = _filename_match_rank(filename, query_lower)

            if resolved_mode in {"tag", "mixed"}:
                candidate_tag_ids = [tag_id for tag_id in (asset.tags or []) if isinstance(tag_id, int) and tag_id in tags_by_id]
                matched_tag_ids = [
                    tag_id
                    for tag_id in candidate_tag_ids
                    if query_lower in (tags_by_id[tag_id].name or "").casefold()
                    or query_lower in (tags_by_id[tag_id].display_name or "").casefold()
                ]
                if matched_tag_ids:
                    matched_by.append("tag")
                    tag_names = []
                    for tag_id in matched_tag_ids:
                        tag = tags_by_id[tag_id]
                        if tag.display_name:
                            tag_names.append(tag.display_name)
                        if tag.name:
                            tag_names.append(tag.name)
                    tag_rank = _tag_match_rank(tag_names, query_lower)

            if not matched_by:
                continue

            item = _build_search_item(asset, preview_resolver, tags_by_id, matched_by, matched_tag_ids=matched_tag_ids)
            if item is None:
                continue
            result_map[item.id] = {
                "item": item,
                "priority": min(filename_rank, tag_rank),
                "name": item.name.casefold(),
            }

    ordered_rows = sorted(
        result_map.values(),
        key=lambda row: (row["priority"], row["name"], row["item"].id),
    )
    items = [row["item"] for row in ordered_rows[:limit]]

    included_tag_ids = sorted(
        {
            tag_id
            for item in items
            for tag_id in item.tags
            if tag_id in tags_by_id
        },
        key=lambda tag_id: (tags_by_id[tag_id].name or "").casefold(),
    )

    return SearchImageResponse(
        query=query,
        requested_mode=requested_mode,
        resolved_mode=resolved_mode,
        limit=limit,
        total=len(result_map),
        source_media_rel_path=source_media_rel_path,
        quick_hash=source_quick_hash,
        included_tags=[_to_tag_brief(tags_by_id[tag_id]) for tag_id in included_tag_ids],
        items=items,
    )