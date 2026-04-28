import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete
from sqlmodel import select

from app.api.common import cache_thumb_url, normalize_stored_path, resolve_stored_path, thumb_url
from app.api.schemas import (
    ImageMetaItem,
    ImageMetaResponse,
    ImageMetadataUpdateItem,
    ImageMetadataUpdateRequest,
    ImageMetadataUpdateResponse,
    ImageTagApplyItem,
    ImageTagApplyRequest,
    ImageTagApplyResponse,
    ImageTagMatchItem,
    ImageTagMatchRequest,
    ImageTagMatchResponse,
    TagBriefItem,
)
from app.db.session import get_session
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.models.tag import Tag
from app.services.category_service import DEFAULT_CATEGORY_ID, require_category
from app.services.app_settings_service import get_tag_match_setting
from app.services.imports.helpers import apply_file_times, to_project_relative
from app.services.imports.maintenance import _ensure_album_chain, recalculate_album_counts
from app.services.viewer_service import (
    get_preferred_viewer_id,
    launch_with_preferred_viewer,
    resolve_viewer_candidate,
)

router = APIRouter()
_DRAFT_CREATED_BY = "system:draft-reserve"


def _now_tag_timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


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


def _parse_media_rel_path(media_rel_path: str) -> tuple[str, list[str], str] | None:
    parts = [part for part in normalize_stored_path(media_rel_path).split("/") if part]
    if len(parts) < 3:
        return None
    if parts[0] != "media":
        return None
    return parts[1], parts[2:-1], parts[-1]


def _datetime_to_source_time_ms(value: datetime) -> int:
    return int(round(value.timestamp() * 1000.0))


def _normalize_requested_filename(requested_name: str, current_filename: str) -> str:
    normalized = str(requested_name or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if "/" in normalized or "\\" in normalized:
        raise HTTPException(status_code=400, detail="文件名不能包含路径分隔符")
    if normalized in {".", ".."}:
        raise HTTPException(status_code=400, detail="文件名不合法")

    current_suffix = Path(current_filename or "").suffix
    if not current_suffix:
        return normalized
    if normalized.lower().endswith(current_suffix.lower()):
        return normalized
    if Path(normalized).suffix:
        raise HTTPException(status_code=400, detail="暂不支持修改文件扩展名")
    return f"{normalized}{current_suffix}"


def _reserve_unique_target_path(dest_dir: Path, filename: str, reserved: set[str]) -> Path:
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    index = 0
    while True:
        candidate_name = filename if index == 0 else f"{base_name}_{index}{suffix}"
        candidate = dest_dir / candidate_name
        candidate_key = str(candidate.resolve()).casefold()
        if candidate_key not in reserved and not candidate.exists():
            reserved.add(candidate_key)
            return candidate
        index += 1


def _rebuild_asset_path_metadata(session, asset: ImageAsset) -> None:
    unique_paths: list[str] = []
    for stored_path in asset.media_path or []:
        if not isinstance(stored_path, str) or not stored_path:
            continue
        normalized = normalize_stored_path(stored_path)
        if normalized in unique_paths:
            continue
        unique_paths.append(normalized)

    album_chains: list[list[str]] = []
    date_candidates: list[str] = []
    for media_rel_path in unique_paths:
        parsed = _parse_media_rel_path(media_rel_path)
        if not parsed:
            continue
        date_group, subdir_chain, _filename = parsed
        date_candidates.append(date_group)
        if not subdir_chain:
            continue
        public_ids, _album_paths = _ensure_album_chain(session, subdir_chain, date_group)
        if public_ids and public_ids not in album_chains:
            album_chains.append(public_ids)

    asset.media_path = unique_paths
    asset.album = album_chains
    if date_candidates:
        asset.date_group = sorted(date_candidates)[0]


def _rollback_metadata_operations(plans: list[dict]) -> None:
    for plan in reversed(plans):
        current_path = plan.get("current_path")
        original_path = plan.get("original_path")
        original_time_ms = plan.get("original_time_ms")

        if isinstance(current_path, Path) and isinstance(original_path, Path) and current_path != original_path:
            try:
                original_path.parent.mkdir(parents=True, exist_ok=True)
                if current_path.exists():
                    shutil.move(str(current_path), str(original_path))
                current_path = original_path
            except Exception:
                current_path = original_path if original_path.exists() else current_path

        if isinstance(current_path, Path) and isinstance(original_time_ms, int) and current_path.exists():
            try:
                apply_file_times(current_path, original_time_ms)
            except Exception:
                pass


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


def _build_common_tag_payload(
    rows_after_tag_ids: list[list[int]],
    tags_by_id: dict[int, Tag],
) -> tuple[list[int], list[TagBriefItem], str]:
    common_tag_ids: list[int] = []
    if rows_after_tag_ids:
        common_set = set(rows_after_tag_ids[0])
        for row in rows_after_tag_ids[1:]:
            common_set &= set(row)
        common_tag_ids = _sort_tag_ids_by_name(list(common_set), tags_by_id)

    if not rows_after_tag_ids:
        multi_display = "empty"
    elif len(rows_after_tag_ids) == 1:
        multi_display = "common" if rows_after_tag_ids[0] else "empty"
    elif common_tag_ids:
        multi_display = "common"
    elif any(row for row in rows_after_tag_ids):
        multi_display = "various"
    else:
        multi_display = "empty"

    common_tags = [
        _to_tag_brief(tags_by_id[tag_id])
        for tag_id in common_tag_ids
        if tag_id in tags_by_id
    ]
    return common_tag_ids, common_tags, multi_display


def _touch_tag_last_used(tags_by_id: dict[int, Tag], tag_ids: set[int], last_used_at: str) -> bool:
    changed = False
    for tag_id in tag_ids:
        tag = tags_by_id.get(tag_id)
        if not tag:
            continue
        if tag.last_used_at == last_used_at:
            continue
        tag.last_used_at = last_used_at
        tag.updated_at = datetime.utcnow()
        changed = True
    return changed


def _sync_tag_usage_count(session, tags_by_id: dict[int, Tag], affected_tag_ids: set[int]) -> bool:
    if not affected_tag_ids:
        return False

    usage_map = {tag_id: 0 for tag_id in affected_tag_ids}
    assets = session.exec(select(ImageAsset)).all()
    for asset in assets:
        tag_ids = _sanitize_tag_ids(asset.tags or [])
        for tag_id in tag_ids:
            if tag_id in usage_map:
                usage_map[tag_id] += 1

    changed = False
    for tag_id, usage_count in usage_map.items():
        tag = tags_by_id.get(tag_id)
        if not tag:
            continue
        if tag.usage_count == usage_count:
            continue
        tag.usage_count = usage_count
        tag.updated_at = datetime.utcnow()
        changed = True
    return changed


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


@router.patch("/api/images/metadata", response_model=ImageMetadataUpdateResponse)
def update_image_metadata(body: ImageMetadataUpdateRequest) -> ImageMetadataUpdateResponse:
    wants_name_update = body.name is not None
    wants_category_update = body.category_id is not None
    wants_created_update = body.file_created_at is not None
    if not any((wants_name_update, wants_category_update, wants_created_update)):
        raise HTTPException(status_code=400, detail="至少提供一个可更新字段")

    targets: list[tuple[int, str | None]] = []
    seen_targets: set[tuple[int, str | None]] = set()
    for item in body.items:
        image_id = int(item.image_id)
        normalized_path = normalize_stored_path(item.media_rel_path) if item.media_rel_path else None
        key = (image_id, normalized_path)
        if key in seen_targets:
            continue
        seen_targets.add(key)
        targets.append(key)

    if not targets:
        return ImageMetadataUpdateResponse(items=[], updated_count=0, renamed_count=0, moved_count=0)

    if wants_name_update and len(targets) != 1:
        raise HTTPException(status_code=400, detail="多选时不支持修改文件名")

    requested_time_ms = _datetime_to_source_time_ms(body.file_created_at) if wants_created_update else None
    selected_category_id = None
    if wants_category_update:
        selected_category_id = int(body.category_id or DEFAULT_CATEGORY_ID)

    with get_session() as session:
        if selected_category_id is not None:
            require_category(session, selected_category_id)

        image_ids = sorted({image_id for image_id, _media_rel_path in targets})
        assets = session.exec(
            select(ImageAsset).where(ImageAsset.id.in_(image_ids))  # type: ignore[arg-type]
        ).all()
        assets_by_id = {
            int(asset.id): asset
            for asset in assets
            if asset.id is not None
        }

        planned_operations: list[dict] = []
        reserved_targets: set[str] = set()

        for image_id, requested_media_rel_path in targets:
            asset = assets_by_id.get(image_id)
            if not asset:
                raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")

            known_paths = [
                normalize_stored_path(path)
                for path in (asset.media_path or [])
                if isinstance(path, str) and path
            ]
            source_media_rel_path = requested_media_rel_path or (known_paths[0] if known_paths else None)
            if not source_media_rel_path:
                raise HTTPException(status_code=404, detail=f"Image path not found: {image_id}")
            if source_media_rel_path not in known_paths:
                raise HTTPException(status_code=404, detail=f"Image path not found: {source_media_rel_path}")

            parsed = _parse_media_rel_path(source_media_rel_path)
            if not parsed:
                raise HTTPException(status_code=400, detail=f"Unsupported media path: {source_media_rel_path}")
            current_date_group, subdir_chain, current_filename = parsed

            source_path = resolve_stored_path(source_media_rel_path)
            if not source_path or not source_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found on disk: {source_media_rel_path}")

            target_filename = current_filename
            if wants_name_update:
                target_filename = _normalize_requested_filename(body.name or "", current_filename)

            target_date_group = current_date_group
            if body.file_created_at is not None:
                target_date_group = body.file_created_at.strftime("%Y-%m")

            target_dir = source_path.parent
            if target_date_group != current_date_group:
                target_dir = Path("media") / target_date_group
                for segment in subdir_chain:
                    target_dir = target_dir / segment
                target_dir = resolve_stored_path(str(target_dir)) or source_path.parent

            final_target_path = source_path
            if target_dir != source_path.parent or target_filename != current_filename:
                final_target_path = _reserve_unique_target_path(target_dir, target_filename, reserved_targets)

            planned_operations.append(
                {
                    "asset": asset,
                    "source_media_rel_path": source_media_rel_path,
                    "source_path": source_path,
                    "current_filename": current_filename,
                    "target_filename": final_target_path.name,
                    "target_path": final_target_path,
                    "target_media_rel_path": normalize_stored_path(to_project_relative(final_target_path)),
                    "renamed": final_target_path.name != current_filename,
                    "moved": final_target_path.parent != source_path.parent,
                }
            )

        applied_plans: list[dict] = []
        response_items: list[ImageMetadataUpdateItem] = []
        touched_asset_ids: set[int] = set()
        requires_album_recalc = False

        try:
            for plan in planned_operations:
                source_path = plan["source_path"]
                target_path = plan["target_path"]
                current_path = source_path

                original_stat = current_path.stat()
                original_time_ms = int(min(original_stat.st_ctime, original_stat.st_mtime) * 1000)

                if target_path != source_path:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
                    current_path = target_path
                    requires_album_recalc = True

                if requested_time_ms is not None:
                    apply_file_times(current_path, requested_time_ms)

                asset = plan["asset"]
                normalized_paths = [
                    normalize_stored_path(path)
                    for path in (asset.media_path or [])
                    if isinstance(path, str) and path
                ]
                updated_paths: list[str] = []
                replaced = False
                for media_rel_path in normalized_paths:
                    if not replaced and media_rel_path == plan["source_media_rel_path"]:
                        updated_paths.append(plan["target_media_rel_path"])
                        replaced = True
                    else:
                        updated_paths.append(media_rel_path)
                if not replaced:
                    raise HTTPException(status_code=404, detail=f"Image path not found: {plan['source_media_rel_path']}")

                asset.media_path = updated_paths
                if wants_name_update:
                    asset.full_filename = plan["target_filename"]
                if selected_category_id is not None:
                    asset.category_id = selected_category_id
                if body.file_created_at is not None:
                    asset.file_created_at = body.file_created_at
                _rebuild_asset_path_metadata(session, asset)
                session.add(asset)

                if asset.id is not None:
                    touched_asset_ids.add(int(asset.id))

                applied_plans.append(
                    {
                        "current_path": current_path,
                        "original_path": source_path,
                        "original_time_ms": original_time_ms,
                    }
                )

                response_items.append(
                    ImageMetadataUpdateItem(
                        image_id=int(asset.id or 0),
                        source_media_rel_path=plan["source_media_rel_path"],
                        media_rel_path=plan["target_media_rel_path"],
                        name=asset.full_filename or plan["target_filename"],
                        category_id=asset.category_id or DEFAULT_CATEGORY_ID,
                        file_created_at=asset.file_created_at,
                        renamed=bool(plan["renamed"]),
                        moved=bool(plan["moved"]),
                    )
                )

            if touched_asset_ids and requires_album_recalc:
                touched_album_asset_ids = sorted(touched_asset_ids)
                session.connection().execute(
                    delete(AlbumImage).where(AlbumImage.image_id.in_(touched_album_asset_ids))  # type: ignore[arg-type]
                )
            session.commit()
        except HTTPException:
            session.rollback()
            _rollback_metadata_operations(applied_plans)
            raise
        except Exception as exc:
            session.rollback()
            _rollback_metadata_operations(applied_plans)
            raise HTTPException(status_code=500, detail=f"更新图片元数据失败: {exc}") from exc

    if requires_album_recalc:
        recalculate_album_counts()

    return ImageMetadataUpdateResponse(
        items=response_items,
        updated_count=len({item.image_id for item in response_items}),
        renamed_count=sum(1 for item in response_items if item.renamed),
        moved_count=sum(1 for item in response_items if item.moved),
    )


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
        assets = session.exec(
            select(ImageAsset).where(ImageAsset.id.in_(unique_image_ids))  # type: ignore[arg-type]
        ).all()
        tags = session.exec(
            select(Tag).where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]
        ).all()

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
        touched_tag_ids: set[int] = set()
        affected_tag_ids: set[int] = set()

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
                affected_tag_ids.update(before_tag_ids)
                affected_tag_ids.update(after_tag_ids)
                touched_tag_ids.update(after_tag_ids)

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
            now_tag_ts = _now_tag_timestamp()
            _touch_tag_last_used(tags_by_id, touched_tag_ids, now_tag_ts)
            _sync_tag_usage_count(session, tags_by_id, affected_tag_ids)
            session.commit()

        common_tag_ids, common_tags, multi_display = _build_common_tag_payload(
            [row.after_tag_ids for row in items],
            tags_by_id,
        )

        return ImageTagMatchResponse(
            items=items,
            common_tag_ids=common_tag_ids,
            common_tags=common_tags,
            multi_display=multi_display,
            applied_count=applied_count,
        )


@router.post("/api/images/tags/apply", response_model=ImageTagApplyResponse)
def apply_tags(body: ImageTagApplyRequest) -> ImageTagApplyResponse:
    if body.merge_mode not in {"append_unique", "replace", "remove"}:
        raise HTTPException(status_code=400, detail="merge_mode 必须为 append_unique / replace / remove")

    unique_image_ids = _sanitize_tag_ids(body.image_ids)
    unique_tag_ids = _sanitize_tag_ids(body.tag_ids)

    if not unique_image_ids:
        return ImageTagApplyResponse(items=[], common_tag_ids=[], common_tags=[], multi_display="empty", applied_count=0)

    with get_session() as session:

        assets = session.exec(
            select(ImageAsset).where(ImageAsset.id.in_(unique_image_ids))  # type: ignore[arg-type]
        ).all()
        tags = session.exec(
            select(Tag).where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]
        ).all()
        tags_by_id = {
            int(tag.id): tag
            for tag in tags
            if tag.id is not None
        }

        valid_tag_ids = [
            tag_id
            for tag_id in unique_tag_ids
            if tag_id in tags_by_id
        ]
        valid_tag_ids = _sort_tag_ids_by_name(valid_tag_ids, tags_by_id)

        assets_by_id = {
            int(asset.id): asset
            for asset in assets
            if asset.id is not None
        }

        items: list[ImageTagApplyItem] = []
        applied_count = 0
        touched_tag_ids: set[int] = set()
        affected_tag_ids: set[int] = set()
        remove_tag_id_set = set(valid_tag_ids)

        for image_id in unique_image_ids:
            asset = assets_by_id.get(image_id)
            if not asset:
                continue

            before_tag_ids = _sanitize_tag_ids(asset.tags or [])
            if body.merge_mode == "replace":
                after_tag_ids = valid_tag_ids
            elif body.merge_mode == "remove":
                after_tag_ids = [
                    tag_id
                    for tag_id in before_tag_ids
                    if tag_id not in remove_tag_id_set
                ]
            else:
                merged: list[int] = []
                seen: set[int] = set()
                for candidate_id in before_tag_ids + valid_tag_ids:
                    if candidate_id in seen:
                        continue
                    seen.add(candidate_id)
                    merged.append(candidate_id)
                after_tag_ids = _sort_tag_ids_by_name(merged, tags_by_id)

            changed = before_tag_ids != after_tag_ids
            if changed:
                asset.tags = after_tag_ids
                session.add(asset)
                applied_count += 1
                affected_tag_ids.update(before_tag_ids)
                affected_tag_ids.update(after_tag_ids)
                if body.merge_mode == "append_unique":
                    touched_tag_ids.update(after_tag_ids)
                elif body.merge_mode == "replace":
                    touched_tag_ids.update(after_tag_ids)

            items.append(
                ImageTagApplyItem(
                    image_id=image_id,
                    before_tag_ids=before_tag_ids,
                    after_tag_ids=after_tag_ids,
                    changed=changed,
                )
            )

        if applied_count:
            if touched_tag_ids:
                now_tag_ts = _now_tag_timestamp()
                _touch_tag_last_used(tags_by_id, touched_tag_ids, now_tag_ts)
            _sync_tag_usage_count(session, tags_by_id, affected_tag_ids)
            session.commit()

        common_tag_ids, common_tags, multi_display = _build_common_tag_payload(
            [row.after_tag_ids for row in items],
            tags_by_id,
        )
        return ImageTagApplyResponse(
            items=items,
            common_tag_ids=common_tag_ids,
            common_tags=common_tags,
            multi_display=multi_display,
            applied_count=applied_count,
        )