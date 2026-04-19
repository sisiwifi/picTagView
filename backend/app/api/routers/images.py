import os
import subprocess
import sys

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.common import cache_thumb_url, normalize_stored_path, resolve_stored_path, thumb_url
from app.api.schemas import ImageMetaItem, ImageMetaResponse
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.viewer_service import (
    get_preferred_viewer_id,
    launch_with_preferred_viewer,
    resolve_viewer_candidate,
)

router = APIRouter()


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