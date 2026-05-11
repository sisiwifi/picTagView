from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.session import get_session
from app.services.home_service import build_home_overview

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/overview")
def home_overview(
    limit: int = Query(default=30, ge=1, le=60),
    offset: int = Query(default=0, ge=0),
    exclude_image_ids: list[int] | None = Query(default=None),
) -> dict:
    with get_session() as session:
        return build_home_overview(
            session,
            limit=limit,
            offset=offset,
            exclude_image_ids=exclude_image_ids or [],
        )