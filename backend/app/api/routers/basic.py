import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from sqlmodel import select

from app.api.common import ia_not_deleted
from app.api.schemas import ImportResponse
from app.db.session import get_session
from app.models.image_asset import ImageAsset
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
) -> ImportResponse:
    last_modified_times: Optional[List[Optional[int]]] = None
    created_times: Optional[List[Optional[int]]] = None

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

    result = await import_files(files, last_modified_times, created_times)
    return ImportResponse(**result)


@router.get("/api/images/count")
def images_count() -> dict:
    with get_session() as session:
        count = len(session.exec(select(ImageAsset).where(ia_not_deleted())).all())
    return {"count": count}


@router.post("/api/admin/refresh")
def refresh() -> dict:
    return refresh_library()