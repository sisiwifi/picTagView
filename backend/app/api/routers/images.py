import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.common import cache_thumb_url, normalize_stored_path, resolve_stored_path, thumb_url
from app.api.schemas import (
    ImageMetaItem,
    ImageMetaResponse,
    ImageTagMatchItem,
    ImageTagMatchRequest,
    ImageTagMatchResponse,
    TagBriefItem,
)
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.models.tag import Tag
from app.services.category_service import DEFAULT_CATEGORY_ID
from app.services.app_settings_service import get_tag_match_setting
from app.services.tag_style_service import ensure_tag_style_scheme
from app.services.viewer_service import (
    get_preferred_viewer_id,
    launch_with_preferred_viewer,
    resolve_viewer_candidate,
)

router = APIRouter()


def _filename_stem(filename: str) -> str:
    name = (filename or "").strip()
    if not name:
        return ""
    return Path(name).stem


def _extract_tokens(
    stem: str,
    *,
    noise_tokens: set[str],
    min_token_length: int,
    drop_numeric_only: bool,
) -> list[str]:
    if not stem:
        return []

    tokens: list[str] = []
    seen: set[str] = set()
    for segment in stem.split(" "):
        token = segment.strip()
        if not token:
            continue
        if len(token) < min_token_length:
            continue
        if drop_numeric_only and token.isdigit():
            continue
        if token in noise_tokens:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _sanitize_tag_ids(raw_ids: object) -> list[int]:
    if not isinstance(raw_ids, list):
        return []
    result: list[int] = []
    seen: set[int] = set()
    for tag_id in raw_ids:
        if not isinstance(tag_id, int):
            continue
        if tag_id in seen:
            continue
        seen.add(tag_id)
        result.append(tag_id)
    return result


def _sort_tag_ids_by_name(tag_ids: list[int], tags_by_id: dict[int, Tag]) -> list[int]:
    def _sort_key(tag_id: int) -> tuple[str, int]:
        tag = tags_by_id.get(tag_id)
        if not tag:
            return ("~", tag_id)
        return (str(tag.name or "~"), tag_id)

    return sorted(tag_ids, key=_sort_key)


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


@router.get("/api/images/meta", response_model=ImageMetaResponse)
def image_meta(ids: str = Query(..., description="Comma-separated image ids")) -> ImageMetaResponse:
    raw_ids = [segment.strip() for segment in ids.split(",")]
    image_ids: list[int] = []
    for segment in raw_ids:
        if not segment:
            continue
        try:
            image_ids.append(int(segment))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid image id: {segment}") from exc

    if not image_ids:
        return ImageMetaResponse(items=[])

    with get_session() as session:
        assets = session.exec(
            select(ImageAsset).where(ImageAsset.id.in_(image_ids))  # type: ignore[arg-type]
        ).all()

    asset_by_id = {
        asset.id: asset
        for asset in assets
        if asset.id is not None
    }

    items: list[ImageMetaItem] = []
    for image_id in image_ids:
        asset = asset_by_id.get(image_id)
        if not asset:
            continue
        items.append(
            ImageMetaItem(
                id=image_id,
                name=asset.full_filename or "",
                category_id=asset.category_id or DEFAULT_CATEGORY_ID,
                width=asset.width,
                height=asset.height,
                file_size=asset.file_size,
                imported_at=asset.imported_at,
                file_created_at=asset.file_created_at,
                tags=asset.tags or [],
                thumb_url=thumb_url(asset),
                cache_thumb_url=cache_thumb_url(asset),
                media_paths=[path for path in (asset.media_path or []) if isinstance(path, str) and path],
            )
        )

    return ImageMetaResponse(items=items)


@router.get("/api/images/{image_id}/open")
def open_image(image_id: int, path: str | None = Query(default=None)) -> dict:
    with get_session() as session:
        asset = session.get(ImageAsset, image_id)
    if not asset or not asset.media_path:
        raise HTTPException(status_code=404, detail="Image not found")

    selected_path = None
    if path:
        normalized_query = normalize_stored_path(path)
        for stored in asset.media_path or []:
            if not isinstance(stored, str) or not stored:
                continue
            if normalize_stored_path(stored) == normalized_query:
                selected_path = stored
                break
        if selected_path is None:
            raise HTTPException(status_code=404, detail="Image path not found")
    else:
        selected_path = next(
            (stored for stored in (asset.media_path or []) if isinstance(stored, str) and stored),
            None,
        )

    path_obj = resolve_stored_path(selected_path)
    if not path_obj:
        raise HTTPException(status_code=404, detail="File path is invalid")
    if not path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    if sys.platform == "win32":
        preferred_id = get_preferred_viewer_id()
        if preferred_id:
            preferred = resolve_viewer_candidate(preferred_id)
            if preferred and launch_with_preferred_viewer(preferred.get("command", ""), path_obj):
                return {"status": "ok", "mode": "preferred", "viewer_id": preferred_id}
        os.startfile(str(path_obj))
        return {"status": "ok", "mode": "system"}
    if sys.platform == "darwin":
        subprocess.run(["open", str(path_obj)], check=False)
    else:
        subprocess.run(["xdg-open", str(path_obj)], check=False)

    return {"status": "ok", "mode": "system"}


@router.post("/api/images/tags/filename-match", response_model=ImageTagMatchResponse)
def filename_match_tags(body: ImageTagMatchRequest) -> ImageTagMatchResponse:
    if body.merge_mode not in {"append_unique", "replace"}:
        raise HTTPException(status_code=400, detail="merge_mode 必须为 append_unique 或 replace")

    unique_image_ids: list[int] = []
    seen_image_ids: set[int] = set()
    for image_id in body.image_ids:
        if not isinstance(image_id, int):
            continue
        if image_id in seen_image_ids:
            continue
        seen_image_ids.add(image_id)
        unique_image_ids.append(image_id)

    if not unique_image_ids:
        return ImageTagMatchResponse(items=[], common_tag_ids=[], common_tags=[], multi_display="empty", applied_count=0)

    setting = get_tag_match_setting()
    enabled = bool(setting.get("enabled", True))
    noise_tokens = set(setting.get("noise_tokens", [])) if enabled else set()
    min_token_length = int(setting.get("min_token_length", 2)) if enabled else 1
    drop_numeric_only = bool(setting.get("drop_numeric_only", True)) if enabled else False

    with get_session() as session:
        ensure_tag_style_scheme(session)
        assets = session.exec(
            select(ImageAsset).where(ImageAsset.id.in_(unique_image_ids))  # type: ignore[arg-type]
        ).all()
        tags = session.exec(select(Tag)).all()

        asset_by_id = {asset.id: asset for asset in assets if asset.id is not None}
        tags_by_name = {
            str(tag.name): tag
            for tag in tags
            if tag.id is not None and isinstance(tag.name, str) and tag.name
        }
        tags_by_id = {
            int(tag.id): tag
            for tag in tags
            if tag.id is not None
        }

        applied_count = 0
        items: list[ImageTagMatchItem] = []

        for image_id in unique_image_ids:
            asset = asset_by_id.get(image_id)
            if not asset:
                continue

            filename = asset.full_filename or ""
            tokens = _extract_tokens(
                _filename_stem(filename),
                noise_tokens=noise_tokens,
                min_token_length=min_token_length,
                drop_numeric_only=drop_numeric_only,
            )

            matched_tags_by_id: dict[int, Tag] = {}
            for token in tokens:
                tag = tags_by_name.get(token)
                if not tag or tag.id is None:
                    continue
                matched_tags_by_id[int(tag.id)] = tag

            matched_tag_ids = _sort_tag_ids_by_name(list(matched_tags_by_id.keys()), tags_by_id)
            before_tag_ids = _sanitize_tag_ids(asset.tags or [])

            if body.merge_mode == "replace":
                after_tag_ids = matched_tag_ids
            else:
                merged_ids: list[int] = []
                merged_seen: set[int] = set()
                for candidate_id in before_tag_ids + matched_tag_ids:
                    if candidate_id in merged_seen:
                        continue
                    merged_seen.add(candidate_id)
                    merged_ids.append(candidate_id)
                after_tag_ids = _sort_tag_ids_by_name(merged_ids, tags_by_id)

            changed = before_tag_ids != after_tag_ids
            if body.apply and changed:
                asset.tags = after_tag_ids
                session.add(asset)
                applied_count += 1

            items.append(
                ImageTagMatchItem(
                    image_id=image_id,
                    filename=filename,
                    tokens=tokens if body.include_tokens else [],
                    matched_tag_ids=matched_tag_ids,
                    matched_tags=[_to_tag_brief(matched_tags_by_id[tag_id]) for tag_id in matched_tag_ids],
                    before_tag_ids=before_tag_ids,
                    after_tag_ids=after_tag_ids,
                    changed=changed,
                )
            )

        if body.apply and applied_count:
            session.commit()

        common_tag_ids: list[int] = []
        if items:
            common_set = set(items[0].after_tag_ids)
            for row in items[1:]:
                common_set &= set(row.after_tag_ids)
            common_tag_ids = _sort_tag_ids_by_name(list(common_set), tags_by_id)

        if not items:
            multi_display = "empty"
        elif len(items) == 1:
            multi_display = "common" if items[0].after_tag_ids else "empty"
        elif common_tag_ids:
            multi_display = "common"
        elif any(row.after_tag_ids for row in items):
            multi_display = "various"
        else:
            multi_display = "empty"

        common_tags = [
            _to_tag_brief(tags_by_id[tag_id])
            for tag_id in common_tag_ids
            if tag_id in tags_by_id
        ]

        return ImageTagMatchResponse(
            items=items,
            common_tag_ids=common_tag_ids,
            common_tags=common_tags,
            multi_display=multi_display,
            applied_count=applied_count,
        )