from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.collection import Collection
from app.models.collection_image import CollectionImage
from app.models.image_asset import ImageAsset
from app.services.category_service import is_category_visible
from app.services.cover_service import build_asset_cover_payload, cover_is_manual, extract_cover_photo_id


_PATH_SEP_PATTERN = re.compile(r"[\\/]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TRIM_DASH_PATTERN = re.compile(r"^-+|-+$")


def normalize_collection_title(raw_title: object) -> str:
    title = str(raw_title or "").strip()
    if not title:
        raise ValueError("收藏名称不能为空")
    if len(title) > 120:
        raise ValueError("收藏名称不能超过 120 个字符")
    return title


def build_collection_path_seed(title: str) -> str:
    normalized = _PATH_SEP_PATTERN.sub("-", title.strip())
    normalized = _WHITESPACE_PATTERN.sub("-", normalized)
    normalized = normalized.replace(".", "-")
    normalized = _TRIM_DASH_PATTERN.sub("", normalized)
    return normalized or "collection"


def ensure_unique_collection_path(
    session: Session,
    base_path: str,
    *,
    exclude_collection_id: int | None = None,
) -> str:
    index = 0
    while True:
        candidate = base_path if index == 0 else f"{base_path}-{index + 1}"
        stmt = select(Collection).where(Collection.collection_path == candidate)
        existing = session.exec(stmt).first()
        if not existing:
            return candidate
        if exclude_collection_id is not None and existing.id == exclude_collection_id:
            return candidate
        index += 1


def find_collection_by_title(session: Session, title: str) -> Collection | None:
    normalized_title = title.strip()
    if not normalized_title:
        return None
    stmt = select(Collection).where(func.lower(Collection.title) == normalized_title.casefold())
    return session.exec(stmt).first()


def create_or_get_collection(
    session: Session,
    *,
    title: str,
    description: str = "",
) -> Collection:
    normalized_title = normalize_collection_title(title)
    existing = find_collection_by_title(session, normalized_title)
    if existing:
        return existing

    collection = Collection(
        public_id="",
        title=normalized_title,
        description=str(description or "").strip() or None,
        collection_path=ensure_unique_collection_path(session, build_collection_path_seed(normalized_title)),
        is_leaf=True,
        parent_id=None,
        photo_count=0,
        subtree_photo_count=0,
        sort_mode="alpha",
        settings={},
        stats={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(collection)
    session.flush()
    collection.public_id = f"collection_{collection.id}"
    session.add(collection)
    session.flush()
    return collection


def list_collection_assets(
    session: Session,
    *,
    collection_id: int,
    active_category_ids: set[int] | None = None,
) -> list[tuple[CollectionImage, ImageAsset]]:
    relation_rows = session.exec(
        select(CollectionImage)
        .where(CollectionImage.collection_id == collection_id)
        .order_by(col(CollectionImage.created_at), col(CollectionImage.id), col(CollectionImage.image_id))
    ).all()
    if not relation_rows:
        return []

    image_ids = [row.image_id for row in relation_rows if isinstance(row.image_id, int)]
    if not image_ids:
        return []

    assets = session.exec(
        select(ImageAsset).where(ImageAsset.id.in_(image_ids))  # type: ignore[attr-defined]
    ).all()
    assets_by_id = {
        int(asset.id): asset
        for asset in assets
        if isinstance(asset.id, int)
    }

    ordered_assets: list[tuple[CollectionImage, ImageAsset]] = []
    for relation in relation_rows:
        asset = assets_by_id.get(relation.image_id)
        if asset is None:
            continue
        if active_category_ids is not None and not is_category_visible(asset.category_id, active_category_ids):
            continue
        ordered_assets.append((relation, asset))
    return ordered_assets


def resolve_collection_cover_asset(
    collection: Collection,
    ordered_assets: list[tuple[CollectionImage, ImageAsset]],
) -> ImageAsset | None:
    preferred_photo_id = extract_cover_photo_id(collection.cover)
    if preferred_photo_id is not None:
        for _, asset in ordered_assets:
            if asset.id == preferred_photo_id:
                return asset
    return ordered_assets[0][1] if ordered_assets else None


def set_collection_cover(
    session: Session,
    *,
    collection: Collection,
    image_id: int,
) -> Collection:
    if collection.id is None:
        raise ValueError("collection 未持久化")

    ordered_assets = list_collection_assets(session, collection_id=collection.id)
    target_asset = next((asset for _, asset in ordered_assets if asset.id == image_id), None)
    if target_asset is None:
        raise ValueError("图片不在当前收藏夹中")

    collection.cover = build_asset_cover_payload(target_asset, manual=True)
    collection.updated_at = datetime.now()
    session.add(collection)
    session.flush()
    return collection


def refresh_collection_stats(session: Session, collection: Collection) -> Collection:
    if collection.id is None:
        return collection

    ordered_assets = list_collection_assets(session, collection_id=collection.id)

    count = len(ordered_assets)
    collection.photo_count = count
    collection.subtree_photo_count = count
    preferred_photo_id = extract_cover_photo_id(collection.cover)
    cover_asset = resolve_collection_cover_asset(collection, ordered_assets)
    keep_manual_cover = (
        cover_is_manual(collection.cover)
        and cover_asset is not None
        and cover_asset.id == preferred_photo_id
    )
    collection.cover = build_asset_cover_payload(cover_asset, manual=keep_manual_cover)
    collection.updated_at = datetime.now()
    session.add(collection)
    session.flush()
    return collection


def build_collection_candidate_items(
    session: Session,
    *,
    image_ids: list[int],
    query: str,
    limit: int,
) -> list[dict]:
    normalized_query = str(query or "").strip()
    safe_limit = max(1, min(int(limit or 12), 40))

    stmt = select(Collection)
    if normalized_query:
        pattern = f"%{normalized_query}%"
        stmt = stmt.where(
            (Collection.title.like(pattern)) | (Collection.description.like(pattern))  # type: ignore[attr-defined]
        ).order_by(col(Collection.title), col(Collection.id))
    else:
        stmt = stmt.order_by(col(Collection.updated_at).desc(), col(Collection.id).desc())

    collections = session.exec(stmt.limit(safe_limit)).all()
    if not collections:
        return []

    image_id_set = {image_id for image_id in image_ids if isinstance(image_id, int)}
    matches_by_collection_id: dict[int, list[int]] = {}
    if image_id_set:
        rows = session.exec(
            select(CollectionImage.collection_id, CollectionImage.image_id)
            .where(CollectionImage.collection_id.in_([item.id for item in collections if item.id is not None]))
            .where(CollectionImage.image_id.in_(list(image_id_set)))
        ).all()
        for collection_id, image_id in rows:
            if not isinstance(collection_id, int) or not isinstance(image_id, int):
                continue
            matches_by_collection_id.setdefault(collection_id, []).append(image_id)

    selected_total = len(image_id_set)
    result: list[dict] = []
    for collection in collections:
        if collection.id is None:
            continue
        matched_image_ids = sorted(set(matches_by_collection_id.get(collection.id, [])))
        selected_match_count = len(matched_image_ids)
        result.append({
            "id": collection.id,
            "public_id": collection.public_id or "",
            "title": collection.title,
            "description": collection.description or "",
            "collection_path": collection.collection_path,
            "photo_count": int(collection.photo_count or 0),
            "matched_image_ids": matched_image_ids,
            "selected_match_count": selected_match_count,
            "contains_all_selected": bool(selected_total and selected_match_count == selected_total),
        })
    return result


def apply_collection_actions(
    session: Session,
    *,
    collection: Collection,
    image_actions: list[dict],
) -> tuple[Collection, dict[str, int]]:
    if collection.id is None:
        raise ValueError("collection 未持久化")

    image_ids = sorted({
        int(row.get("image_id"))
        for row in image_actions
        if isinstance(row.get("image_id"), int)
    })
    if not image_ids:
        raise ValueError("至少需要一张图片")

    existing_images = session.exec(
        select(ImageAsset.id).where(ImageAsset.id.in_(image_ids))  # type: ignore[attr-defined]
    ).all()
    existing_image_ids = {int(image_id) for image_id in existing_images if isinstance(image_id, int)}
    missing = [image_id for image_id in image_ids if image_id not in existing_image_ids]
    if missing:
        raise ValueError(f"图片不存在：{', '.join(str(item) for item in missing)}")

    existing_rows = session.exec(
        select(CollectionImage)
        .where(CollectionImage.collection_id == collection.id)
        .where(CollectionImage.image_id.in_(image_ids))
    ).all()
    existing_by_image_id = {
        row.image_id: row
        for row in existing_rows
        if isinstance(row.image_id, int)
    }

    counters = {
        "added_count": 0,
        "removed_count": 0,
        "kept_count": 0,
    }

    for row in image_actions:
        image_id = row.get("image_id")
        action = str(row.get("action") or "keep").strip().lower()
        if not isinstance(image_id, int):
            continue
        existing = existing_by_image_id.get(image_id)
        if action == "add":
            if existing is not None:
                counters["kept_count"] += 1
                continue
            session.add(CollectionImage(collection_id=collection.id, image_id=image_id))
            counters["added_count"] += 1
            continue
        if action == "remove":
            if existing is None:
                counters["kept_count"] += 1
                continue
            session.delete(existing)
            counters["removed_count"] += 1
            continue
        counters["kept_count"] += 1

    session.flush()
    refreshed = refresh_collection_stats(session, collection)
    return refreshed, counters