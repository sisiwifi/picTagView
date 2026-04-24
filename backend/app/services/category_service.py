from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import text
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.category import Category, default_usage_count

DEFAULT_CATEGORY_ID = 1
DEFAULT_CATEGORY_NAME = "default"
DEFAULT_CATEGORY_DISPLAY_NAME = "默认"
DEFAULT_CATEGORY_DESCRIPTION = "系统默认主分类，不可删除。"

_CATEGORY_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def normalize_category_name(value: object) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip().lower())


def sanitize_legacy_category_name(value: object) -> str:
    normalized = normalize_category_name(value)
    normalized = re.sub(r"[^a-z0-9_]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def validate_category_name(value: object) -> str:
    normalized = normalize_category_name(value)
    if not normalized:
        raise ValueError("name 不能为空")
    if not _CATEGORY_NAME_RE.fullmatch(normalized):
        raise ValueError("name 只能包含小写英文、数字与下划线")
    return normalized


def clean_usage_count(value: object) -> dict[str, int]:
    cleaned = default_usage_count()
    if not isinstance(value, dict):
        return cleaned
    for key in cleaned.keys():
        raw = value.get(key)
        if isinstance(raw, int) and raw >= 0:
            cleaned[key] = raw
    return cleaned


def _write_public_id(category: Category) -> None:
    if category.id is not None:
        category.public_id = f"category_{category.id}"


def ensure_default_category(session: Session) -> Category:
    category = session.get(Category, DEFAULT_CATEGORY_ID)
    if not category:
        category = Category(
            id=DEFAULT_CATEGORY_ID,
            public_id=f"category_{DEFAULT_CATEGORY_ID}",
            name=DEFAULT_CATEGORY_NAME,
            display_name=DEFAULT_CATEGORY_DISPLAY_NAME,
            description=DEFAULT_CATEGORY_DESCRIPTION,
            usage_count=default_usage_count(),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(category)
        session.flush()
        return category

    changed = False
    if category.public_id != f"category_{DEFAULT_CATEGORY_ID}":
        category.public_id = f"category_{DEFAULT_CATEGORY_ID}"
        changed = True
    if category.name != DEFAULT_CATEGORY_NAME:
        category.name = DEFAULT_CATEGORY_NAME
        changed = True
    if category.display_name != DEFAULT_CATEGORY_DISPLAY_NAME:
        category.display_name = DEFAULT_CATEGORY_DISPLAY_NAME
        changed = True
    if category.description != DEFAULT_CATEGORY_DESCRIPTION:
        category.description = DEFAULT_CATEGORY_DESCRIPTION
        changed = True
    cleaned_usage = clean_usage_count(category.usage_count)
    if cleaned_usage != category.usage_count:
        category.usage_count = cleaned_usage
        changed = True
    if not category.is_active:
        category.is_active = True
        changed = True
    if changed:
        session.add(category)
        session.flush()
    return category


def ensure_default_category_exists() -> None:
    with get_session() as session:
        ensure_default_category(session)
        session.commit()


def category_to_dict(category: Category) -> dict:
    usage_count = clean_usage_count(category.usage_count)
    category_id = category.id or DEFAULT_CATEGORY_ID
    return {
        "id": category_id,
        "public_id": category.public_id,
        "name": category.name,
        "display_name": category.display_name,
        "description": category.description,
        "usage_count": usage_count,
        "usage_total": sum(usage_count.values()),
        "is_active": bool(category.is_active),
        "created_at": category.created_at.isoformat() if category.created_at else None,
        "editable": category_id != DEFAULT_CATEGORY_ID,
        "removable": category_id != DEFAULT_CATEGORY_ID,
        "builtin": category_id == DEFAULT_CATEGORY_ID,
    }


def get_category_display_map(session: Session) -> dict[int, str]:
    ensure_default_category(session)
    categories = session.exec(select(Category)).all()
    return {
        category.id or DEFAULT_CATEGORY_ID: category.display_name or category.name
        for category in categories
    }


def get_active_category_ids(session: Session) -> set[int]:
    ensure_default_category(session)
    active_ids = {
        category.id or DEFAULT_CATEGORY_ID
        for category in session.exec(select(Category).where(Category.is_active == True)).all()  # noqa: E712
        if category is not None
    }
    active_ids.add(DEFAULT_CATEGORY_ID)
    return active_ids


def is_category_visible(category_id: object, active_category_ids: set[int]) -> bool:
    if isinstance(category_id, int) and category_id in active_category_ids:
        return True
    return DEFAULT_CATEGORY_ID in active_category_ids and (category_id is None or category_id == DEFAULT_CATEGORY_ID)


def require_category(session: Session, category_id: int | None) -> Category:
    ensure_default_category(session)
    target_id = category_id or DEFAULT_CATEGORY_ID
    category = session.get(Category, target_id)
    if not category:
        raise ValueError(f"Category {target_id} 不存在")
    return category


def resolve_category_id(session: Session, category_id: object = None, category_name: object = None) -> int:
    ensure_default_category(session)
    if isinstance(category_id, int):
        category = session.get(Category, category_id)
        if category:
            return category.id or DEFAULT_CATEGORY_ID

    normalized_name = sanitize_legacy_category_name(category_name)
    if normalized_name:
        category = session.exec(select(Category).where(Category.name == normalized_name)).first()
        if category:
            return category.id or DEFAULT_CATEGORY_ID

    return DEFAULT_CATEGORY_ID


def sync_category_usage_counts(session: Session) -> bool:
    ensure_default_category(session)

    from app.models.image_asset import ImageAsset

    categories = session.exec(select(Category).order_by(Category.id)).all()
    counts = {
        (category.id or DEFAULT_CATEGORY_ID): default_usage_count()
        for category in categories
    }
    counts.setdefault(DEFAULT_CATEGORY_ID, default_usage_count())

    def bump(category_id: object, key: str) -> None:
        if isinstance(category_id, int) and category_id in counts:
            counts[category_id][key] += 1
        else:
            counts[DEFAULT_CATEGORY_ID][key] += 1

    for image_category_id in session.exec(select(ImageAsset.category_id)).all():
        bump(image_category_id, "image")

    changed = False
    for category in categories:
        category_id = category.id or DEFAULT_CATEGORY_ID
        next_usage = counts.get(category_id, default_usage_count())
        if clean_usage_count(category.usage_count) != next_usage:
            category.usage_count = next_usage
            session.add(category)
            changed = True
    return changed


def reassign_category_references(session: Session, source_category_id: int, target_category_id: int = DEFAULT_CATEGORY_ID) -> dict[str, int]:
    reassigned = {"image": 0, "trash": 0}
    if source_category_id == target_category_id:
        return reassigned

    from app.models.image_asset import ImageAsset
    from app.models.trash_entry import TrashEntry

    images = session.exec(select(ImageAsset).where(ImageAsset.category_id == source_category_id)).all()
    for asset in images:
        asset.category_id = target_category_id
        session.add(asset)
    reassigned["image"] = len(images)

    trash_entries = session.exec(
        select(TrashEntry)
        .where(TrashEntry.entity_type == "image")
        .where(TrashEntry.category_id == source_category_id)
    ).all()
    for entry in trash_entries:
        entry.category_id = target_category_id
        session.add(entry)
    reassigned["trash"] = len(trash_entries)

    return reassigned


def _load_legacy_category_rows(session: Session, table_name: str) -> list[tuple[int, int | None, str | None]]:
    try:
        result = session.exec(text(f"SELECT id, category_id, category FROM {table_name}"))
        rows = result.fetchall()
        return [(int(row[0]), row[1], row[2]) for row in rows]
    except Exception:
        try:
            result = session.exec(text(f"SELECT id, category_id FROM {table_name}"))
            rows = result.fetchall()
            return [(int(row[0]), row[1], None) for row in rows]
        except Exception:
            return []


def _create_category_from_legacy(session: Session, name: str, display_name: str) -> Category:
    category = Category(
        public_id="",
        name=name,
        display_name=display_name or name,
        description="",
        usage_count=default_usage_count(),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    session.add(category)
    session.flush()
    _write_public_id(category)
    session.add(category)
    session.flush()
    return category


def backfill_category_ids_from_legacy() -> None:
    with get_session() as session:
        ensure_default_category(session)
        categories = session.exec(select(Category).order_by(Category.id)).all()
        categories_by_name = {category.name: category for category in categories}
        categories_by_id = {category.id or DEFAULT_CATEGORY_ID: category for category in categories}
        changed = False

        def resolve_from_legacy(legacy_value: str | None) -> int:
            normalized = sanitize_legacy_category_name(legacy_value)
            if not normalized:
                return DEFAULT_CATEGORY_ID
            existing = categories_by_name.get(normalized)
            if existing:
                return existing.id or DEFAULT_CATEGORY_ID
            created = _create_category_from_legacy(session, normalized, str(legacy_value or "").strip() or normalized)
            categories_by_name[created.name] = created
            categories_by_id[created.id or DEFAULT_CATEGORY_ID] = created
            return created.id or DEFAULT_CATEGORY_ID

        for table_name in ("imageasset", "trash_entry"):
            rows = _load_legacy_category_rows(session, table_name)
            for row_id, category_id, legacy_value in rows:
                next_category_id = category_id if isinstance(category_id, int) and category_id in categories_by_id else None
                if next_category_id is None:
                    next_category_id = resolve_from_legacy(legacy_value)
                if category_id != next_category_id:
                    session.execute(
                        text(f"UPDATE {table_name} SET category_id = :category_id WHERE id = :row_id"),
                        {"category_id": next_category_id, "row_id": row_id},
                    )
                    changed = True

        changed = sync_category_usage_counts(session) or changed
        if changed:
            session.commit()
