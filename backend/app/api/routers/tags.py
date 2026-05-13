"""Tag CRUD, batch-query, import and export endpoints."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from uuid import uuid4
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlmodel import select

from app.api.common import AssetPreviewResolver, build_preview_availability_index, pick_asset_media_path
from app.api.schemas import AlbumItem
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.models.tag import Tag
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids
from app.services.tag_match_service import sanitize_tag_ids
from app.services.visible_album_service import list_visible_assets

router = APIRouter(prefix="/api/tags", tags=["tags"])

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_VALID_CREATED_VIA = {
    "manual", "auto:filename", "import", "merge", "split", "sync", "migration"
}

_VALID_TAG_TYPES = {"normal", "artist", "copyright", "character", "series"}
_DRAFT_CREATED_BY = "system:draft-reserve"
_TAG_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
_IMPORT_COMPAT_TAG_NAME_PATTERN = re.compile(r"^[a-z0-9_!'\(\)\-\.@]+$")
_HEX_PATTERN = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGBA_PATTERN = re.compile(
    r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([0-9]*\.?[0-9]+))?\s*\)$",
    re.IGNORECASE,
)


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def _normalize_tag_type(tag_type: object) -> str:
    value = str(tag_type or "").strip().lower() or "normal"
    if value not in _VALID_TAG_TYPES:
        return "normal"
    return value


def _is_draft_tag(tag: Tag) -> bool:
    return str(tag.created_by or "") == _DRAFT_CREATED_BY


def _normalize_tag_name(name: object) -> str:
    normalized = str(name or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="name 不能为空")
    if not _TAG_NAME_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="name 仅支持小写字母、数字和下划线")
    return normalized


def _normalize_import_tag_name(name: object) -> str:
    normalized = str(name or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="name 不能为空")
    # Keep JSON import compatible with older exported tag names so round-trip
    # import/export does not silently drop legacy entries.
    if not _IMPORT_COMPAT_TAG_NAME_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="name 仅支持小写字母、数字、下划线及兼容导入字符 ! ' ( ) - . @",
        )
    return normalized


def _normalize_created_by(created_by: object, *, allow_draft: bool = False, fallback: str = "admin") -> str:
    value = str(created_by or "").strip() or fallback
    if value == _DRAFT_CREATED_BY and not allow_draft:
        return fallback
    return value


def _clamp_channel(value: object) -> int:
    try:
        channel = int(str(value).strip())
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="颜色通道值无效")
    return max(0, min(255, channel))


def _clamp_alpha_decimal(value: object) -> Decimal:
    try:
        alpha = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="透明度值无效")
    if alpha < 0:
        return Decimal("0")
    if alpha > 1:
        return Decimal("1")
    return alpha


def _alpha_to_hex(alpha: Decimal) -> str:
    alpha_int = int((alpha * Decimal(255)).quantize(Decimal("1")))
    alpha_int = max(0, min(255, alpha_int))
    return f"{alpha_int:02X}"


def _normalize_hex8(color_value: object, *, default_alpha: str = "FF") -> str:
    raw = str(color_value or "").strip()
    if not raw:
        return ""

    rgba_match = _RGBA_PATTERN.fullmatch(raw)
    if rgba_match:
        red = _clamp_channel(rgba_match.group(1))
        green = _clamp_channel(rgba_match.group(2))
        blue = _clamp_channel(rgba_match.group(3))
        alpha = _clamp_alpha_decimal(rgba_match.group(4) if rgba_match.group(4) is not None else "1")
        return f"#{red:02X}{green:02X}{blue:02X}{_alpha_to_hex(alpha)}"

    if not _HEX_PATTERN.fullmatch(raw):
        raise HTTPException(status_code=400, detail=f"颜色值 '{raw}' 无效，仅支持 HEX 或 rgba")

    hex_value = raw[1:] if raw.startswith("#") else raw
    if len(hex_value) == 3:
        red, green, blue = (component * 2 for component in hex_value)
        alpha = default_alpha
    elif len(hex_value) == 4:
        red, green, blue, alpha = (component * 2 for component in hex_value)
    elif len(hex_value) == 6:
        red = hex_value[0:2]
        green = hex_value[2:4]
        blue = hex_value[4:6]
        alpha = default_alpha
    else:
        red = hex_value[0:2]
        green = hex_value[2:4]
        blue = hex_value[4:6]
        alpha = hex_value[6:8]

    return f"#{red}{green}{blue}{alpha}".upper()


def _normalize_tag_metadata(metadata: object | None, *, fallback_created_via: str = "manual") -> dict:
    model = TagMetadata.model_validate(metadata or {})
    payload = model.model_dump()
    created_via = str(payload.get("created_via", fallback_created_via) or fallback_created_via).strip()
    if created_via not in _VALID_CREATED_VIA:
        created_via = fallback_created_via if fallback_created_via in _VALID_CREATED_VIA else "manual"
    payload["created_via"] = created_via
    payload["color"] = _normalize_hex8(payload.get("color", ""), default_alpha="FF")
    payload["border_color"] = _normalize_hex8(payload.get("border_color", ""), default_alpha="FF")
    payload["background_color"] = _normalize_hex8(payload.get("background_color", ""), default_alpha="FF")
    return payload


def _visible_tag_stmt():
    return select(Tag).where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]


def _tag_to_dict(tag: Tag) -> dict:
    metadata = _normalize_tag_metadata(tag.metadata_ or {}, fallback_created_via="manual")
    return {
        "id": tag.id,
        "public_id": tag.public_id,
        "name": tag.name,
        "display_name": tag.display_name,
        "type": tag.type,
        "description": tag.description,
        "usage_count": tag.usage_count,
        "last_used_at": tag.last_used_at,
        "metadata": metadata,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        "created_by": tag.created_by,
        "updated_at": tag.updated_at.isoformat() if tag.updated_at else None,
    }


def _write_public_id(tag: Tag) -> None:
    """Set public_id = 'tag_{id}' after the tag has been flushed to get its id."""
    tag.public_id = f"tag_{tag.id}"


def _tag_row_error(row_index: int, field: str, message: str) -> dict:
    return {
        "row_index": row_index,
        "row_number": row_index + 1,
        "field": field,
        "message": message,
    }


def _delete_tags_and_detach_assets(session, raw_tag_ids: object) -> dict:
    requested_tag_ids = sanitize_tag_ids(raw_tag_ids)
    if not requested_tag_ids:
        return {
            "requested_ids": [],
            "deleted_tag_ids": [],
            "deleted_public_ids": [],
            "deleted_names": [],
            "deleted_count": 0,
            "detached_image_count": 0,
            "detached_reference_count": 0,
            "missing_ids": [],
        }

    tags = session.exec(
        select(Tag).where(Tag.id.in_(requested_tag_ids))  # type: ignore[attr-defined]
    ).all()
    tags_by_id = {
        int(tag.id): tag
        for tag in tags
        if tag.id is not None
    }
    missing_ids = [tag_id for tag_id in requested_tag_ids if tag_id not in tags_by_id]
    deleted_tags = [tags_by_id[tag_id] for tag_id in requested_tag_ids if tag_id in tags_by_id]

    detached_image_count = 0
    detached_reference_count = 0
    if deleted_tags:
        remove_tag_id_set = {int(tag.id) for tag in deleted_tags if tag.id is not None}
        assets = session.exec(select(ImageAsset)).all()
        for asset in assets:
            before_tag_ids = sanitize_tag_ids(asset.tags or [])
            if not before_tag_ids:
                continue

            after_tag_ids = [tag_id for tag_id in before_tag_ids if tag_id not in remove_tag_id_set]
            if after_tag_ids == before_tag_ids:
                continue

            detached_image_count += 1
            detached_reference_count += len(before_tag_ids) - len(after_tag_ids)
            asset.tags = after_tag_ids
            session.add(asset)

        for tag in deleted_tags:
            session.delete(tag)

    return {
        "requested_ids": requested_tag_ids,
        "deleted_tag_ids": [int(tag.id) for tag in deleted_tags if tag.id is not None],
        "deleted_public_ids": [str(tag.public_id or "") for tag in deleted_tags if tag.id is not None],
        "deleted_names": [str(tag.name or "") for tag in deleted_tags],
        "deleted_count": len(deleted_tags),
        "detached_image_count": detached_image_count,
        "detached_reference_count": detached_reference_count,
        "missing_ids": missing_ids,
    }


def _to_unix_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp())


def _build_tag_image_item(asset: ImageAsset, preview_resolver: AssetPreviewResolver) -> AlbumItem | None:
    if asset.id is None:
        return None

    media_index, media_rel_path = pick_asset_media_path(asset)
    if media_index is None or not media_rel_path:
        return None

    preview = preview_resolver.resolve(asset)
    return AlbumItem(
        type="image",
        name=asset.full_filename or "",
        thumb_url=preview.thumb_url,
        id=int(asset.id),
        category_id=asset.category_id or DEFAULT_CATEGORY_ID,
        cache_thumb_url=preview.cache_thumb_url,
        width=asset.width,
        height=asset.height,
        sort_ts=_to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at),
        tags=[tag_id for tag_id in (asset.tags or []) if isinstance(tag_id, int)],
        file_size=asset.file_size,
        imported_at=asset.imported_at,
        file_created_at=asset.file_created_at,
        media_index=media_index,
        media_rel_path=media_rel_path,
        is_animated=bool(asset.is_animated),
        animation_meta=asset.normalized_animation_meta if asset.is_animated else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class TagMetadata(BaseModel):
    schema_version: int = 1
    color: str = ""
    border_color: str = ""
    background_color: str = ""
    created_via: str = "manual"
    ui_hint: dict = Field(default_factory=dict)
    notes: str = ""


class TagCreate(BaseModel):
    name: str
    display_name: str = ""
    type: Literal["normal", "artist", "copyright", "character", "series"] = "normal"
    description: str = ""
    created_by: str = "admin"
    metadata: TagMetadata = Field(default_factory=TagMetadata)


class TagUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[Literal["normal", "artist", "copyright", "character", "series"]] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    metadata: Optional[TagMetadata] = None


class TagDraftReserveBody(BaseModel):
    type: Literal["normal", "artist", "copyright", "character", "series"] = "normal"
    metadata: TagMetadata = Field(default_factory=TagMetadata)


class TagBulkDeleteBody(BaseModel):
    ids: list[int] = Field(default_factory=list)


class TagBulkCreateRow(BaseModel):
    name: str = ""
    display_name: str = ""
    description: str = ""
    type: str = "normal"
    metadata: TagMetadata = Field(default_factory=TagMetadata)


class TagBulkCreateBody(BaseModel):
    tags: list[TagBulkCreateRow] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# CRUD endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{tag_id}/images")
def list_tag_images(tag_id: int) -> dict:
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag or _is_draft_tag(tag):
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")

        active_category_ids = get_active_category_ids(session)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())
        visible_assets = list_visible_assets(session, active_category_ids)

        items: list[AlbumItem] = []
        for asset in visible_assets:
            asset_tag_ids = [candidate for candidate in (asset.tags or []) if isinstance(candidate, int)]
            if tag_id not in asset_tag_ids:
                continue
            item = _build_tag_image_item(asset, preview_resolver)
            if item is not None:
                items.append(item)

        return {
            "tag": _tag_to_dict(tag),
            "items": items,
        }

@router.get("")
def list_tags(
    ids: Optional[str] = Query(default=None, description="逗号分隔的 Tag ID 列表，用于批量查询"),
    category_id: Optional[int] = Query(default=None, description="已废弃；标签不再属于主分类"),
    category: Optional[str] = Query(default=None, description="已废弃；标签不再属于主分类"),
    tag_type: Optional[str] = Query(default=None, alias="type"),
    q: Optional[str] = Query(default=None, description="按 name/display_name 模糊搜索"),
    sort_by: str = Query(default="name_asc", description="排序：name_asc | last_used_desc"),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """列出所有 Tag；支持按 ID 列表批量查、类型过滤、名称模糊搜索。"""
    with get_session() as session:
        _ = category_id, category
        stmt = _visible_tag_stmt()
        if ids:
            try:
                id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="ids 参数必须为整数列表")
            stmt = stmt.where(Tag.id.in_(id_list))  # type: ignore[attr-defined]
        if tag_type:
            stmt = stmt.where(Tag.type == _normalize_tag_type(tag_type))  # type: ignore[attr-defined]
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                (Tag.name.like(pattern)) | (Tag.display_name.like(pattern))  # type: ignore[attr-defined]
            )
        if sort_by == "last_used_desc":
            stmt = stmt.order_by(
                case((Tag.last_used_at.is_(None), 1), else_=0),
                Tag.last_used_at.desc(),
                Tag.updated_at.desc(),
                Tag.id.desc(),
            )
        else:
            stmt = stmt.order_by(Tag.name.asc(), Tag.id.asc())
        tags = session.exec(stmt.offset(offset).limit(limit)).all()
        total = int(session.exec(select(func.count()).select_from(stmt.subquery())).one())
        return {"total": total, "offset": offset, "limit": limit, "items": [_tag_to_dict(t) for t in tags]}


@router.post("/draft", status_code=201)
def reserve_tag_draft(body: TagDraftReserveBody | None = None) -> dict:
    request_body = body or TagDraftReserveBody()
    meta = _normalize_tag_metadata(request_body.metadata, fallback_created_via="manual")
    temp_name = f"__draft_tag_{_now_str()}_{uuid4().hex[:10]}"
    now = datetime.utcnow()

    with get_session() as session:
        tag = Tag(
            name=temp_name,
            display_name="",
            type=_normalize_tag_type(request_body.type),
            description="",
            created_by=_DRAFT_CREATED_BY,
            metadata_=meta,
            created_at=now,
            updated_at=now,
        )
        session.add(tag)
        session.flush()
        _write_public_id(tag)
        session.add(tag)
        session.commit()
        session.refresh(tag)
        payload = _tag_to_dict(tag)
        payload["name"] = ""
        payload["display_name"] = ""
        payload["description"] = ""
        return payload


@router.post("/bulk-delete")
def bulk_delete_tags(body: TagBulkDeleteBody) -> dict:
    requested_tag_ids = sanitize_tag_ids(body.ids)
    if not requested_tag_ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")

    with get_session() as session:
        summary = _delete_tags_and_detach_assets(session, requested_tag_ids)
        if summary["deleted_count"]:
            session.commit()
        return summary


@router.post("/bulk-create", status_code=201)
def bulk_create_tags(body: TagBulkCreateBody):
    if not body.tags:
        raise HTTPException(status_code=400, detail="tags 不能为空")

    row_errors: list[dict] = []
    normalized_rows: list[dict] = []
    row_index_by_name: dict[str, int] = {}

    for row_index, row in enumerate(body.tags):
        row_has_error = False
        normalized_name = ""
        normalized_type = "normal"
        normalized_metadata: dict | None = None

        try:
            normalized_name = _normalize_tag_name(row.name)
        except HTTPException as exc:
            row_errors.append(_tag_row_error(row_index, "name", str(exc.detail)))
            row_has_error = True

        if normalized_name:
            duplicate_row_index = row_index_by_name.get(normalized_name)
            if duplicate_row_index is not None:
                row_errors.append(
                    _tag_row_error(
                        row_index,
                        "name",
                        f"name “{normalized_name}” 与第 {duplicate_row_index + 1} 行重复",
                    )
                )
                row_has_error = True
            else:
                row_index_by_name[normalized_name] = row_index

        try:
            normalized_metadata = _normalize_tag_metadata(row.metadata, fallback_created_via="manual")
        except HTTPException as exc:
            row_errors.append(_tag_row_error(row_index, "style", str(exc.detail)))
            row_has_error = True

        raw_type = str(row.type or "").strip().lower() or "normal"
        if raw_type not in _VALID_TAG_TYPES:
            row_errors.append(_tag_row_error(row_index, "type", f"type “{raw_type}” 无效"))
            row_has_error = True
        else:
            normalized_type = raw_type

        if row_has_error:
            continue

        normalized_rows.append({
            "row_index": row_index,
            "name": normalized_name,
            "display_name": str(row.display_name or "").strip() or normalized_name,
            "description": str(row.description or "").strip(),
            "type": normalized_type,
            "metadata": normalized_metadata or {},
        })

    with get_session() as session:
        if normalized_rows:
            candidate_names = [row["name"] for row in normalized_rows]
            existing_tags = session.exec(
                select(Tag).where(Tag.name.in_(candidate_names))  # type: ignore[attr-defined]
            ).all()
            existing_names = {
                str(tag.name or "")
                for tag in existing_tags
            }
            for row in normalized_rows:
                if row["name"] not in existing_names:
                    continue
                row_errors.append(
                    _tag_row_error(row["row_index"], "name", f"name “{row['name']}” 已存在")
                )

        if row_errors:
            row_errors.sort(key=lambda item: (item["row_index"], item["field"], item["message"]))
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "批量新增校验失败",
                    "row_errors": row_errors,
                },
            )

        created_tags: list[Tag] = []
        for row in normalized_rows:
            now = datetime.utcnow()
            tag = Tag(
                name=row["name"],
                display_name=row["display_name"],
                type=row["type"],
                description=row["description"],
                created_by="admin",
                metadata_=row["metadata"],
                created_at=now,
                updated_at=now,
            )
            session.add(tag)
            session.flush()
            _write_public_id(tag)
            session.add(tag)
            created_tags.append(tag)

        session.commit()
        for tag in created_tags:
            session.refresh(tag)

        return {
            "created": len(created_tags),
            "items": [_tag_to_dict(tag) for tag in created_tags],
        }


@router.get("/{tag_id}")
def get_tag(tag_id: int) -> dict:
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag or _is_draft_tag(tag):
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")
        return _tag_to_dict(tag)


@router.post("", status_code=201)
def create_tag(body: TagCreate) -> dict:
    norm_name = _normalize_tag_name(body.name)
    meta = _normalize_tag_metadata(body.metadata, fallback_created_via="manual")

    with get_session() as session:
        existing = session.exec(select(Tag).where(Tag.name == norm_name)).first()  # type: ignore[attr-defined]
        if existing:
            raise HTTPException(status_code=409, detail=f"name '{norm_name}' 已存在")

        now = datetime.utcnow()
        tag = Tag(
            name=norm_name,
            display_name=str(body.display_name or "").strip() or norm_name,
            type=_normalize_tag_type(body.type),
            description=str(body.description or "").strip(),
            created_by=_normalize_created_by(body.created_by, fallback="admin"),
            metadata_=meta,
            created_at=now,
            updated_at=now,
        )
        session.add(tag)
        session.flush()
        _write_public_id(tag)
        session.add(tag)
        session.commit()
        session.refresh(tag)
        return _tag_to_dict(tag)


@router.patch("/{tag_id}")
def update_tag(tag_id: int, body: TagUpdate) -> dict:
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")
        if body.name is not None:
            norm_name = _normalize_tag_name(body.name)
            existing = session.exec(select(Tag).where(Tag.name == norm_name)).first()  # type: ignore[attr-defined]
            if existing and existing.id != tag.id:
                raise HTTPException(status_code=409, detail=f"name '{norm_name}' 已存在")
            tag.name = norm_name
        if body.display_name is not None:
            tag.display_name = str(body.display_name or "").strip() or tag.name
        if body.type is not None:
            tag.type = _normalize_tag_type(body.type)
        if body.description is not None:
            tag.description = str(body.description or "").strip()
        if body.metadata is not None:
            tag.metadata_ = _normalize_tag_metadata(body.metadata, fallback_created_via="manual")
        if _is_draft_tag(tag):
            tag.created_by = _normalize_created_by(body.created_by, fallback="admin")
        tag.updated_at = datetime.utcnow()
        session.add(tag)
        session.commit()
        session.refresh(tag)
        return _tag_to_dict(tag)


@router.delete("/{tag_id}")
def delete_tag(tag_id: int) -> Response:
    with get_session() as session:
        summary = _delete_tags_and_detach_assets(session, [tag_id])
        if not summary["deleted_count"]:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")
        session.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# Import / Export
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/export/json")
def export_tags() -> JSONResponse:
    """将全库 Tag 导出为 JSON 数组，前端可保存为 .json 文件。"""
    with get_session() as session:
        tags = session.exec(_visible_tag_stmt()).all()
        data = [_tag_to_dict(t) for t in tags]
    return JSONResponse(
        content={"schema_version": 1, "exported_at": datetime.utcnow().isoformat(), "tags": data},
        headers={"Content-Disposition": 'attachment; filename="tags_export.json"'},
    )


class TagImportBody(BaseModel):
    tags: list[dict]
    on_conflict: str = "skip"   # skip | overwrite


@router.post("/import/json")
def import_tags(body: TagImportBody) -> dict:
    """批量导入 Tag 数据。

    - on_conflict=skip：跳过同名已存在的 tag（默认）
    - on_conflict=overwrite：覆盖 display_name / type / description / metadata
    """
    if body.on_conflict not in ("skip", "overwrite"):
        raise HTTPException(status_code=400, detail="on_conflict 必须为 skip 或 overwrite")

    imported = 0
    skipped = 0
    updated = 0
    errors: list[str] = []

    with get_session() as session:
        for item in body.tags:
            try:
                raw_name = _normalize_import_tag_name(item.get("name", ""))
            except HTTPException as exc:
                errors.append(f"跳过非法 name 条目：{exc.detail}；原始数据：{item}")
                continue

            try:
                meta_raw = _normalize_tag_metadata(item.get("metadata", {}) or {}, fallback_created_via="import")
            except HTTPException as exc:
                errors.append(f"跳过颜色非法条目：{exc.detail}；name={raw_name}")
                continue

            existing = session.exec(select(Tag).where(Tag.name == raw_name)).first()  # type: ignore[attr-defined]
            if existing:
                if body.on_conflict == "skip":
                    skipped += 1
                    continue
                # overwrite
                if _is_draft_tag(existing):
                    skipped += 1
                    continue
                existing.display_name = str(item.get("display_name", existing.display_name) or "").strip() or raw_name
                existing.type = _normalize_tag_type(item.get("type", existing.type))
                existing.description = str(item.get("description", existing.description) or "").strip()
                existing.metadata_ = meta_raw
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                updated += 1
                continue

            now = datetime.utcnow()
            tag = Tag(
                name=raw_name,
                display_name=str(item.get("display_name", raw_name) or "").strip() or raw_name,
                type=_normalize_tag_type(item.get("type", "normal")),
                description=str(item.get("description", "") or "").strip(),
                created_by=_normalize_created_by(item.get("created_by", "import"), fallback="import"),
                metadata_=meta_raw,
                created_at=now,
                updated_at=now,
            )
            session.add(tag)
            session.flush()
            _write_public_id(tag)
            session.add(tag)
            imported += 1

        session.commit()

    return {"imported": imported, "updated": updated, "skipped": skipped, "errors": errors}
