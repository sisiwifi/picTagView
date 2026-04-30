from __future__ import annotations

from datetime import datetime

from app.models.image_asset import ImageAsset


def build_asset_cover_payload(
    asset: ImageAsset | None,
    *,
    manual: bool = False,
) -> dict | None:
    if not asset:
        return None

    thumb_path = ""
    for thumb in asset.thumbs or []:
        if isinstance(thumb, dict) and isinstance(thumb.get("path"), str) and thumb.get("path"):
            thumb_path = thumb["path"]
            break

    return {
        "photo_id": asset.id,
        "thumb_path": thumb_path,
        "filename": asset.full_filename or "",
        "manual": bool(manual),
        "updated_at": datetime.now().isoformat(),
    }


def extract_cover_photo_id(raw_cover: object) -> int | None:
    if not isinstance(raw_cover, dict):
        return None

    photo_id = raw_cover.get("photo_id")
    if isinstance(photo_id, int) and photo_id > 0:
        return photo_id
    if isinstance(photo_id, str) and photo_id.isdigit():
        return int(photo_id)
    return None


def cover_is_manual(raw_cover: object) -> bool:
    return bool(isinstance(raw_cover, dict) and raw_cover.get("manual"))