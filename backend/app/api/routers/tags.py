"""Tag CRUD, batch-query, import and export endpoints."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlmodel import select

from app.db.session import get_session
from app.models.tag import Tag

router = APIRouter(prefix="/api/tags", tags=["tags"])

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_VALID_CREATED_VIA = {
    "manual", "auto:filename", "import", "merge", "split", "sync", "migration"
}

_VALID_TAG_TYPES = {"normal", "artist", "artwork", "series"}


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def _normalize_tag_type(tag_type: object) -> str:
    value = str(tag_type or "").strip().lower() or "normal"
    if value not in _VALID_TAG_TYPES:
        return "normal"
    return value


def _tag_to_dict(tag: Tag) -> dict:
    return {
        "id": tag.id,
        "public_id": tag.public_id,
        "name": tag.name,
        "display_name": tag.display_name,
        "type": tag.type,
        "description": tag.description,
        "category": tag.category,
        "usage_count": tag.usage_count,
        "last_used_at": tag.last_used_at,
        "metadata": tag.metadata_ or {},
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        "created_by": tag.created_by,
        "updated_at": tag.updated_at.isoformat() if tag.updated_at else None,
    }


def _write_public_id(tag: Tag, session) -> None:
    """Set public_id = 'tag_{id}' after the tag has been flushed to get its id."""
    tag.public_id = f"tag_{tag.id}"
    session.add(tag)
    session.commit()
    session.refresh(tag)


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class TagMetadata(BaseModel):
    schema_version: int = 1
    color: str = ""
    created_via: str = "manual"
    ui_hint: dict = Field(default_factory=dict)
    notes: str = ""


class TagCreate(BaseModel):
    name: str
    display_name: str = ""
    type: Literal["normal", "artist", "artwork", "series"] = "normal"
    description: str = ""
    category: str = ""
    created_by: str = "admin"
    metadata: TagMetadata = Field(default_factory=TagMetadata)


class TagUpdate(BaseModel):
    display_name: Optional[str] = None
    type: Optional[Literal["normal", "artist", "artwork", "series"]] = None
    description: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[TagMetadata] = None


# ─────────────────────────────────────────────────────────────────────────────
# CRUD endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("")
def list_tags(
    ids: Optional[str] = Query(default=None, description="逗号分隔的 Tag ID 列表，用于批量查询"),
    category: Optional[str] = Query(default=None),
    tag_type: Optional[str] = Query(default=None, alias="type"),
    q: Optional[str] = Query(default=None, description="按 name/display_name 模糊搜索"),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """列出所有 Tag；支持按 ID 列表批量查、分类过滤、类型过滤、名称模糊搜索。"""
    with get_session() as session:
        stmt = select(Tag)
        if ids:
            try:
                id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="ids 参数必须为整数列表")
            stmt = stmt.where(Tag.id.in_(id_list))  # type: ignore[attr-defined]
        if category:
            stmt = stmt.where(Tag.category == category)  # type: ignore[attr-defined]
        if tag_type:
            stmt = stmt.where(Tag.type == _normalize_tag_type(tag_type))  # type: ignore[attr-defined]
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                (Tag.name.like(pattern)) | (Tag.display_name.like(pattern))  # type: ignore[attr-defined]
            )
        total_stmt = stmt
        tags = session.exec(stmt.offset(offset).limit(limit)).all()
        total = len(session.exec(total_stmt).all())
        return {"total": total, "offset": offset, "limit": limit, "items": [_tag_to_dict(t) for t in tags]}


@router.get("/{tag_id}")
def get_tag(tag_id: int) -> dict:
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")
        return _tag_to_dict(tag)


@router.post("", status_code=201)
def create_tag(body: TagCreate) -> dict:
    norm_name = body.name.strip().lower()
    if not norm_name:
        raise HTTPException(status_code=400, detail="name 不能为空")

    meta = body.metadata.dict()
    if meta.get("created_via", "manual") not in _VALID_CREATED_VIA:
        raise HTTPException(status_code=400, detail=f"created_via 无效，合法值：{_VALID_CREATED_VIA}")

    with get_session() as session:
        existing = session.exec(select(Tag).where(Tag.name == norm_name)).first()  # type: ignore[attr-defined]
        if existing:
            raise HTTPException(status_code=409, detail=f"name '{norm_name}' 已存在")

        now = datetime.utcnow()
        tag = Tag(
            name=norm_name,
            display_name=body.display_name or norm_name,
            type=_normalize_tag_type(body.type),
            description=body.description,
            category=body.category,
            created_by=body.created_by,
            metadata_=meta,
            created_at=now,
            updated_at=now,
        )
        session.add(tag)
        session.commit()
        session.refresh(tag)
        _write_public_id(tag, session)
        return _tag_to_dict(tag)


@router.patch("/{tag_id}")
def update_tag(tag_id: int, body: TagUpdate) -> dict:
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")
        if body.display_name is not None:
            tag.display_name = body.display_name
        if body.type is not None:
            tag.type = _normalize_tag_type(body.type)
        if body.description is not None:
            tag.description = body.description
        if body.category is not None:
            tag.category = body.category
        if body.metadata is not None:
            meta = body.metadata.dict()
            if meta.get("created_via", "manual") not in _VALID_CREATED_VIA:
                raise HTTPException(status_code=400, detail=f"created_via 无效，合法值：{_VALID_CREATED_VIA}")
            tag.metadata_ = meta
        tag.updated_at = datetime.utcnow()
        session.add(tag)
        session.commit()
        session.refresh(tag)
        return _tag_to_dict(tag)


@router.delete("/{tag_id}")
def delete_tag(tag_id: int) -> Response:
    with get_session() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} 不存在")
        session.delete(tag)
        session.commit()
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# Import / Export
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/export/json")
def export_tags() -> JSONResponse:
    """将全库 Tag 导出为 JSON 数组，前端可保存为 .json 文件。"""
    with get_session() as session:
        tags = session.exec(select(Tag)).all()
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
    - on_conflict=overwrite：覆盖 display_name / type / description / category / metadata
    """
    if body.on_conflict not in ("skip", "overwrite"):
        raise HTTPException(status_code=400, detail="on_conflict 必须为 skip 或 overwrite")

    imported = 0
    skipped = 0
    updated = 0
    errors: list[str] = []

    with get_session() as session:
        for item in body.tags:
            raw_name = str(item.get("name", "")).strip().lower()
            if not raw_name:
                errors.append(f"跳过空 name 条目：{item}")
                continue

            meta_raw = item.get("metadata", {}) or {}
            # 确保 created_via 合法
            created_via = meta_raw.get("created_via", "import")
            if created_via not in _VALID_CREATED_VIA:
                meta_raw["created_via"] = "import"

            existing = session.exec(select(Tag).where(Tag.name == raw_name)).first()  # type: ignore[attr-defined]
            if existing:
                if body.on_conflict == "skip":
                    skipped += 1
                    continue
                # overwrite
                existing.display_name = item.get("display_name", existing.display_name)
                existing.type = _normalize_tag_type(item.get("type", existing.type))
                existing.description = item.get("description", existing.description)
                existing.category = item.get("category", existing.category)
                existing.metadata_ = meta_raw
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.commit()
                updated += 1
                continue

            now = datetime.utcnow()
            tag = Tag(
                name=raw_name,
                display_name=item.get("display_name", raw_name),
                type=_normalize_tag_type(item.get("type", "normal")),
                description=item.get("description", ""),
                category=item.get("category", ""),
                created_by=item.get("created_by", "import"),
                metadata_=meta_raw,
                created_at=now,
                updated_at=now,
            )
            session.add(tag)
            session.commit()
            session.refresh(tag)
            _write_public_id(tag, session)
            imported += 1

    return {"imported": imported, "updated": updated, "skipped": skipped, "errors": errors}
