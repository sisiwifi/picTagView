import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlmodel import select

from app.api.schemas import AdminRefreshRequest, ImportResponse
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.category_service import require_category
from app.services.import_service import import_files, refresh_library

router = APIRouter()


@router.get("/")
def root() -> dict:
    return {"status": "ok"}


@router.post("/api/import", response_model=ImportResponse)
async def import_images(
    files: List[UploadFile] = File(...),
    last_modified_json: Optional[str] = Form(None),
    created_time_json: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
) -> ImportResponse:
    last_modified_times: Optional[List[Optional[int]]] = None
    created_times: Optional[List[Optional[int]]] = None
    resolved_category_id: Optional[int] = None

    if last_modified_json:
        try:
            last_modified_times = json.loads(last_modified_json)
        except Exception:
            last_modified_times = None

    if created_time_json:
        try:
            created_times = json.loads(created_time_json)
        except Exception:
            created_times = None

    if category_id is not None:
        try:
            with get_session() as session:
                category = require_category(session, category_id)
                resolved_category_id = category.id or category_id
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await import_files(files, last_modified_times, created_times, resolved_category_id)
    return ImportResponse(**result)


@router.get("/api/images/count")
def images_count() -> dict:
    with get_session() as session:
        assets = session.exec(select(ImageAsset)).all()
        count = len(assets)
    return {"count": count}


@router.post("/api/admin/refresh")
def refresh(mode: str = "quick", body: AdminRefreshRequest | None = None) -> dict:
    request_body = body or AdminRefreshRequest()
    return refresh_library(
        mode=mode,
        repair_cache_image_ids=request_body.image_ids if request_body.repair_cache else None,
        repair_cache_trash_entry_ids=request_body.trash_entry_ids if request_body.repair_cache else None,
    )