from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    CacheThumbSettingRequest,
    CacheThumbSettingResponse,
    MonthCoverSettingRequest,
    MonthCoverSettingResponse,
    ViewerPreferenceRequest,
)
from app.services.app_settings_service import (
    DEFAULT_CACHE_SHORT_SIDE_PX,
    DEFAULT_MONTH_COVER_SIZE_PX,
    MAX_CACHE_SHORT_SIDE_PX,
    MAX_MONTH_COVER_SIZE_PX,
    MIN_CACHE_SHORT_SIDE_PX,
    MIN_MONTH_COVER_SIZE_PX,
    get_cache_thumb_short_side_px,
    get_month_cover_size_px,
    set_cache_thumb_short_side_px,
    set_month_cover_size_px,
)
from app.services.viewer_service import (
    IMAGE_EXTENSIONS,
    clear_preferred_viewer_id,
    collect_image_viewers,
    ensure_viewer_icon,
    get_default_image_viewer,
    get_preferred_viewer_id,
    get_viewer_name_by_id,
    set_preferred_viewer_id,
)

router = APIRouter()


@router.get("/api/system/cache-thumb-setting", response_model=CacheThumbSettingResponse)
def get_cache_thumb_setting() -> CacheThumbSettingResponse:
    return CacheThumbSettingResponse(
        short_side_px=get_cache_thumb_short_side_px(),
        default_short_side_px=DEFAULT_CACHE_SHORT_SIDE_PX,
        min_short_side_px=MIN_CACHE_SHORT_SIDE_PX,
        max_short_side_px=MAX_CACHE_SHORT_SIDE_PX,
    )


@router.post("/api/system/cache-thumb-setting", response_model=CacheThumbSettingResponse)
def set_cache_thumb_setting(body: CacheThumbSettingRequest) -> CacheThumbSettingResponse:
    if body.short_side_px < MIN_CACHE_SHORT_SIDE_PX or body.short_side_px > MAX_CACHE_SHORT_SIDE_PX:
        raise HTTPException(
            status_code=400,
            detail=(
                f"short_side_px must be between {MIN_CACHE_SHORT_SIDE_PX} "
                f"and {MAX_CACHE_SHORT_SIDE_PX}"
            ),
        )

    value = set_cache_thumb_short_side_px(body.short_side_px)
    return CacheThumbSettingResponse(
        short_side_px=value,
        default_short_side_px=DEFAULT_CACHE_SHORT_SIDE_PX,
        min_short_side_px=MIN_CACHE_SHORT_SIDE_PX,
        max_short_side_px=MAX_CACHE_SHORT_SIDE_PX,
    )


@router.get("/api/system/month-cover-setting", response_model=MonthCoverSettingResponse)
def get_month_cover_setting() -> MonthCoverSettingResponse:
    return MonthCoverSettingResponse(
        size_px=get_month_cover_size_px(),
        default_size_px=DEFAULT_MONTH_COVER_SIZE_PX,
        min_size_px=MIN_MONTH_COVER_SIZE_PX,
        max_size_px=MAX_MONTH_COVER_SIZE_PX,
    )


@router.post("/api/system/month-cover-setting", response_model=MonthCoverSettingResponse)
def set_month_cover_setting(body: MonthCoverSettingRequest) -> MonthCoverSettingResponse:
    if body.size_px < MIN_MONTH_COVER_SIZE_PX or body.size_px > MAX_MONTH_COVER_SIZE_PX:
        raise HTTPException(
            status_code=400,
            detail=(
                f"size_px must be between {MIN_MONTH_COVER_SIZE_PX} "
                f"and {MAX_MONTH_COVER_SIZE_PX}"
            ),
        )

    value = set_month_cover_size_px(body.size_px)
    return MonthCoverSettingResponse(
        size_px=value,
        default_size_px=DEFAULT_MONTH_COVER_SIZE_PX,
        min_size_px=MIN_MONTH_COVER_SIZE_PX,
        max_size_px=MAX_MONTH_COVER_SIZE_PX,
    )


@router.get("/api/system/viewer-info")
def viewer_info() -> dict:
    preferred_id = get_preferred_viewer_id()
    preferred_name = get_viewer_name_by_id(preferred_id)
    system_name = get_default_image_viewer()
    return {
        "viewer": preferred_name or system_name,
        "preferred_viewer_id": preferred_id,
        "system_viewer": system_name,
    }


@router.get("/api/system/image-viewers")
def image_viewers() -> dict:
    viewers, ext_defaults = collect_image_viewers(IMAGE_EXTENSIONS)
    preferred_id = get_preferred_viewer_id()

    default_ids = set(ext_defaults.values())
    items = []
    for viewer in viewers:
        icon_url = ensure_viewer_icon(viewer)
        items.append({
            "id": viewer["id"],
            "display_name": viewer["display_name"],
            "icon_text": viewer.get("icon_text", "?"),
            "icon_url": icon_url,
            "source_type": viewer.get("source_type", "win32"),
            "is_system_default": viewer["id"] in default_ids,
            "is_selected": viewer["id"] == preferred_id,
        })

    return {
        "extensions": IMAGE_EXTENSIONS,
        "selected_viewer_id": preferred_id,
        "system_default": get_default_image_viewer(),
        "viewers": items,
    }


@router.get("/api/system/viewer-preference")
def viewer_preference() -> dict:
    viewer_id = get_preferred_viewer_id()
    return {
        "viewer_id": viewer_id,
        "viewer_name": get_viewer_name_by_id(viewer_id),
    }


@router.post("/api/system/viewer-preference")
def set_viewer_preference(body: ViewerPreferenceRequest) -> dict:
    viewer_id = (body.viewer_id or "").strip()
    if not viewer_id:
        clear_preferred_viewer_id()
        return {"ok": True, "viewer_id": "", "viewer_name": get_default_image_viewer()}

    viewers, _ = collect_image_viewers(IMAGE_EXTENSIONS)
    valid_ids = {v["id"] for v in viewers}

    if viewer_id not in valid_ids:
        raise HTTPException(status_code=400, detail="viewer_id is not in filtered image viewer list")

    set_preferred_viewer_id(viewer_id)
    return {
        "ok": True,
        "viewer_id": viewer_id,
        "viewer_name": get_viewer_name_by_id(viewer_id),
    }