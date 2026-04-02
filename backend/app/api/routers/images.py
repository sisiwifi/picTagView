import os
import subprocess
import sys

from fastapi import APIRouter, HTTPException

from app.api.common import resolve_stored_path
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.viewer_service import (
    get_preferred_viewer_id,
    launch_with_preferred_viewer,
    resolve_viewer_candidate,
)

router = APIRouter()


@router.get("/api/images/{image_id}/open")
def open_image(image_id: int) -> dict:
    with get_session() as session:
        asset = session.get(ImageAsset, image_id)
    if not asset or not asset.media_path:
        raise HTTPException(status_code=404, detail="Image not found")
    path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
    if not path:
        raise HTTPException(status_code=404, detail="File path is invalid")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    if sys.platform == "win32":
        preferred_id = get_preferred_viewer_id()
        if preferred_id:
            preferred = resolve_viewer_candidate(preferred_id)
            if preferred and launch_with_preferred_viewer(preferred.get("command", ""), path):
                return {"status": "ok", "mode": "preferred", "viewer_id": preferred_id}
        os.startfile(str(path))
        return {"status": "ok", "mode": "system"}
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)

    return {"status": "ok", "mode": "system"}