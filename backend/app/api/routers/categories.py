from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.db.session import get_session
from app.models.category import Category, default_usage_count
from app.services.category_service import (
    DEFAULT_CATEGORY_DESCRIPTION,
    DEFAULT_CATEGORY_DISPLAY_NAME,
    DEFAULT_CATEGORY_ID,
    DEFAULT_CATEGORY_NAME,
    category_to_dict,
    ensure_default_category,
    reassign_category_references,
    sync_category_usage_counts,
    validate_category_name,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str
    display_name: str
    description: str = ""
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryBulkAction(BaseModel):
    action: Literal["activate", "deactivate", "delete"]
    ids: list[int]


def _sorted_categories(categories: list[Category]) -> list[Category]:
    return sorted(
        categories,
        key=lambda item: (
            0 if (item.id or DEFAULT_CATEGORY_ID) == DEFAULT_CATEGORY_ID else 1,
            (item.display_name or item.name or "").casefold(),
            item.id or DEFAULT_CATEGORY_ID,
        ),
    )


@router.get("")
def list_categories() -> dict:
    with get_session() as session:
        ensure_default_category(session)
        if sync_category_usage_counts(session):
            session.commit()
        categories = session.exec(select(Category)).all()
        return {"items": [category_to_dict(category) for category in _sorted_categories(categories)]}


@router.post("", status_code=201)
def create_category(body: CategoryCreate) -> dict:
    try:
        name = validate_category_name(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    display_name = (body.display_name or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name 不能为空")

    description = (body.description or "").strip()

    with get_session() as session:
        ensure_default_category(session)
        existing = session.exec(select(Category).where(Category.name == name)).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"name '{name}' 已存在")

        category = Category(
            public_id="",
            name=name,
            display_name=display_name,
            description=description,
            usage_count=default_usage_count(),
            is_active=bool(body.is_active),
            created_at=datetime.utcnow(),
        )
        session.add(category)
        session.flush()
        if category.id is not None:
            category.public_id = f"category_{category.id}"
        session.add(category)
        session.commit()
        session.refresh(category)
        return category_to_dict(category)


@router.patch("/{category_id}")
def update_category(category_id: int, body: CategoryUpdate) -> dict:
    with get_session() as session:
        ensure_default_category(session)
        category = session.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail=f"Category {category_id} 不存在")
        if category_id == DEFAULT_CATEGORY_ID:
            raise HTTPException(status_code=400, detail="默认主分类不可编辑")

        if body.name is not None:
            try:
                next_name = validate_category_name(body.name)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            existing = session.exec(
                select(Category)
                .where(Category.name == next_name)
                .where(Category.id != category_id)
            ).first()
            if existing:
                raise HTTPException(status_code=409, detail=f"name '{next_name}' 已存在")
            category.name = next_name

        if body.display_name is not None:
            next_display_name = body.display_name.strip()
            if not next_display_name:
                raise HTTPException(status_code=400, detail="display_name 不能为空")
            category.display_name = next_display_name

        if body.description is not None:
            category.description = body.description.strip()

        if body.is_active is not None:
            category.is_active = bool(body.is_active)

        session.add(category)
        if sync_category_usage_counts(session):
            session.flush()
        session.commit()
        session.refresh(category)
        return category_to_dict(category)


@router.delete("/{category_id}")
def delete_category(category_id: int) -> dict:
    if category_id == DEFAULT_CATEGORY_ID:
        raise HTTPException(status_code=400, detail="默认主分类不可删除")

    with get_session() as session:
        ensure_default_category(session)
        category = session.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail=f"Category {category_id} 不存在")

        reassigned = reassign_category_references(session, category_id, DEFAULT_CATEGORY_ID)
        session.delete(category)
        sync_category_usage_counts(session)
        session.commit()
        return {"deleted": 1, "reassigned": reassigned}


@router.post("/bulk")
def bulk_update_categories(body: CategoryBulkAction) -> dict:
    ids = [category_id for category_id in body.ids if isinstance(category_id, int)]
    if not ids:
        return {"updated": 0, "deleted": 0, "reassigned": {"image": 0, "album": 0, "tag": 0, "trash": 0}, "skipped": []}

    skipped: list[int] = []
    updated = 0
    deleted = 0
    reassigned_total = {"image": 0, "album": 0, "tag": 0, "trash": 0}

    with get_session() as session:
        ensure_default_category(session)
        categories = session.exec(select(Category).where(Category.id.in_(ids))).all()  # type: ignore[arg-type]
        category_map = {category.id or DEFAULT_CATEGORY_ID: category for category in categories}

        for category_id in ids:
            if category_id == DEFAULT_CATEGORY_ID:
                skipped.append(category_id)
                continue
            category = category_map.get(category_id)
            if not category:
                skipped.append(category_id)
                continue

            if body.action == "activate":
                if not category.is_active:
                    category.is_active = True
                    session.add(category)
                    updated += 1
                continue

            if body.action == "deactivate":
                if category.is_active:
                    category.is_active = False
                    session.add(category)
                    updated += 1
                continue

            reassigned = reassign_category_references(session, category_id, DEFAULT_CATEGORY_ID)
            for key, value in reassigned.items():
                reassigned_total[key] += value
            session.delete(category)
            deleted += 1

        sync_category_usage_counts(session)
        session.commit()

    return {
        "updated": updated,
        "deleted": deleted,
        "reassigned": reassigned_total,
        "skipped": skipped,
        "default_category": {
            "id": DEFAULT_CATEGORY_ID,
            "name": DEFAULT_CATEGORY_NAME,
            "display_name": DEFAULT_CATEGORY_DISPLAY_NAME,
            "description": DEFAULT_CATEGORY_DESCRIPTION,
        },
    }