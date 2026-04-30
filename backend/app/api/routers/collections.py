from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import AssetPreviewResolver, build_preview_availability_index, pick_asset_media_path
from app.api.schemas import (
    AlbumItem,
    CollectionDetailResponse,
    CollectionApplyResponse,
    CollectionApplyRequest,
    CollectionInfo,
    CollectionOverviewItem,
    CollectionOverviewResponse,
    CollectionSearchRequest,
    CollectionSearchResponse,
    CoverSelectionRequest,
    CoverSelectionResponse,
)
from app.db.session import get_session
from app.models.collection import Collection
from app.services.category_service import DEFAULT_CATEGORY_ID, get_active_category_ids
from app.services.collection_service import (
    apply_collection_actions,
    build_collection_candidate_items,
    create_or_get_collection,
    list_collection_assets,
    resolve_collection_cover_asset,
    set_collection_cover,
)
from app.services.cover_service import extract_cover_photo_id

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _to_unix_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp())


@router.get("", response_model=CollectionOverviewResponse)
def list_collections() -> CollectionOverviewResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        preview_resolver = AssetPreviewResolver(build_preview_availability_index())
        collections = session.exec(
            select(Collection)
            .where(Collection.parent_id == None)  # noqa: E711
            .order_by(col(Collection.updated_at).desc(), col(Collection.title), col(Collection.id))
        ).all()

        items: list[CollectionOverviewItem] = []
        for collection in collections:
            if collection.id is None:
                continue
            visible_assets = list_collection_assets(
                session,
                collection_id=collection.id,
                active_category_ids=active_category_ids,
            )
            if not visible_assets:
                continue

            cover_asset = resolve_collection_cover_asset(collection, visible_assets)
            preview = preview_resolver.resolve(cover_asset) if cover_asset else None
            items.append(CollectionOverviewItem(
                id=int(collection.id),
                public_id=collection.public_id or "",
                title=collection.title,
                description=collection.description or "",
                photo_count=len(visible_assets),
                thumb_url=preview.thumb_url if preview else "",
                cache_thumb_url=preview.cache_thumb_url if preview else None,
                cover_photo_id=cover_asset.id if cover_asset else None,
                width=cover_asset.width if cover_asset else None,
                height=cover_asset.height if cover_asset else None,
                updated_at=collection.updated_at or collection.created_at,
            ))

        return CollectionOverviewResponse(items=items)


@router.get("/{collection_id}", response_model=CollectionDetailResponse)
def collection_detail(collection_id: str) -> CollectionDetailResponse:
    with get_session() as session:
        active_category_ids = get_active_category_ids(session)
        collection = session.exec(
            select(Collection).where(Collection.public_id == collection_id)
        ).first()
        if not collection or collection.id is None:
            raise HTTPException(status_code=404, detail="收藏不存在")

        visible_assets = list_collection_assets(
            session,
            collection_id=collection.id,
            active_category_ids=active_category_ids,
        )
        if not visible_assets:
            raise HTTPException(status_code=404, detail="收藏为空")

        preview_resolver = AssetPreviewResolver(build_preview_availability_index())
        cover_asset = resolve_collection_cover_asset(collection, visible_assets)
        cover_photo_id = cover_asset.id if cover_asset else None

        items: list[AlbumItem] = []
        for _, asset in visible_assets:
            media_index, media_rel_path = pick_asset_media_path(asset)
            if media_index is None or not media_rel_path:
                continue
            preview = preview_resolver.resolve(asset)
            items.append(AlbumItem(
                type="image",
                name=asset.full_filename or "",
                thumb_url=preview.thumb_url,
                id=asset.id,
                category_id=asset.category_id or DEFAULT_CATEGORY_ID,
                cache_thumb_url=preview.cache_thumb_url,
                width=asset.width,
                height=asset.height,
                sort_ts=_to_unix_ts(asset.file_created_at or asset.imported_at or asset.created_at),
                tags=asset.tags or [],
                file_size=asset.file_size,
                imported_at=asset.imported_at,
                file_created_at=asset.file_created_at,
                media_index=media_index,
                media_rel_path=media_rel_path,
                is_cover=bool(cover_photo_id is not None and asset.id == cover_photo_id),
            ))

        if not items:
            raise HTTPException(status_code=404, detail="收藏为空")

        return CollectionDetailResponse(
            collection=CollectionInfo(
                public_id=collection.public_id or "",
                title=collection.title,
                description=collection.description,
                photo_count=len(items),
                subtree_photo_count=len(items),
                cover_photo_id=cover_photo_id,
            ),
            items=items,
        )


@router.post("/search", response_model=CollectionSearchResponse)
def search_collections(body: CollectionSearchRequest) -> CollectionSearchResponse:
    with get_session() as session:
        return CollectionSearchResponse(
            items=build_collection_candidate_items(
                session,
                image_ids=[image_id for image_id in body.image_ids if isinstance(image_id, int)],
                query=body.q,
                limit=body.limit,
            )
        )


@router.post("/apply", response_model=CollectionApplyResponse)
def apply_to_collection(body: CollectionApplyRequest) -> CollectionApplyResponse:
    with get_session() as session:
        collection = None
        if isinstance(body.collection_id, int) and body.collection_id > 0:
            collection = session.get(Collection, body.collection_id)
            if not collection:
                raise HTTPException(status_code=404, detail="收藏不存在")

        if collection is None:
            try:
                collection = create_or_get_collection(
                    session,
                    title=body.title,
                    description=body.description,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            collection, counters = apply_collection_actions(
                session,
                collection=collection,
                image_actions=[item.model_dump() for item in body.image_actions],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        session.commit()
        session.refresh(collection)
        return CollectionApplyResponse(
            id=int(collection.id or 0),
            public_id=collection.public_id or "",
            title=collection.title,
            collection_path=collection.collection_path,
            photo_count=int(collection.photo_count or 0),
            added_count=counters["added_count"],
            removed_count=counters["removed_count"],
            kept_count=counters["kept_count"],
        )


@router.post("/{collection_id}/cover", response_model=CoverSelectionResponse)
def update_collection_cover(collection_id: str, body: CoverSelectionRequest) -> CoverSelectionResponse:
    with get_session() as session:
        collection = session.exec(
            select(Collection).where(Collection.public_id == collection_id)
        ).first()
        if not collection:
            raise HTTPException(status_code=404, detail="收藏不存在")

        try:
            collection = set_collection_cover(session, collection=collection, image_id=body.image_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        session.commit()
        session.refresh(collection)
        return CoverSelectionResponse(
            public_id=collection.public_id or "",
            cover_photo_id=extract_cover_photo_id(collection.cover),
            updated_at=collection.updated_at or collection.created_at,
        )