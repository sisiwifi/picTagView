from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    CacheThumbSettingRequest,
    CacheThumbSettingResponse,
    MonthCoverSettingRequest,
    MonthCoverSettingResponse,
    PageConfigRequest,
    PageConfigResponse,
    TagMatchSettingRequest,
    TagMatchSettingResponse,
    ViewerPreferenceRequest,
)
from app.services.app_settings_service import (
    DEFAULT_CACHE_SHORT_SIDE_PX,
    DEFAULT_MONTH_COVER_SIZE_PX,
    DEFAULT_PAGE_BROWSE_MODE,
    DEFAULT_PAGE_SCROLL_WINDOW_SIZE,
    MAX_CACHE_SHORT_SIDE_PX,
    MAX_MONTH_COVER_SIZE_PX,
    MIN_CACHE_SHORT_SIDE_PX,
    MIN_MONTH_COVER_SIZE_PX,
    get_cache_thumb_short_side_px,
    get_month_cover_size_px,
    get_page_config,
    get_tag_match_setting,
    set_cache_thumb_short_side_px,
    set_month_cover_size_px,
    set_page_config,
    set_tag_match_setting,
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


@router.get("/api/system/page-config", response_model=PageConfigResponse)
def get_page_config_api() -> PageConfigResponse:
    data = get_page_config()
    return PageConfigResponse(
        browse_mode=data.get("browse_mode", DEFAULT_PAGE_BROWSE_MODE),
        scroll_window_size=data.get("scroll_window_size", DEFAULT_PAGE_SCROLL_WINDOW_SIZE),
        default_browse_mode=DEFAULT_PAGE_BROWSE_MODE,
        default_scroll_window_size=DEFAULT_PAGE_SCROLL_WINDOW_SIZE,
    )


@router.post("/api/system/page-config", response_model=PageConfigResponse)
def set_page_config_api(body: PageConfigRequest) -> PageConfigResponse:
    browse_mode = (body.browse_mode or DEFAULT_PAGE_BROWSE_MODE).strip()
    if browse_mode not in {"scroll", "paged"}:
        raise HTTPException(status_code=400, detail="browse_mode must be one of: scroll, paged")

    next_setting = set_page_config(body.model_dump())
    return PageConfigResponse(
        browse_mode=next_setting.get("browse_mode", DEFAULT_PAGE_BROWSE_MODE),
        scroll_window_size=next_setting.get("scroll_window_size", DEFAULT_PAGE_SCROLL_WINDOW_SIZE),
        default_browse_mode=DEFAULT_PAGE_BROWSE_MODE,
        default_scroll_window_size=DEFAULT_PAGE_SCROLL_WINDOW_SIZE,
    )


@router.get("/api/system/tag-match-setting", response_model=TagMatchSettingResponse)
def get_tag_match_setting_api() -> TagMatchSettingResponse:
    data = get_tag_match_setting()
    return TagMatchSettingResponse(
        enabled=data.get("enabled", True),
        noise_tokens=data.get("noise_tokens", []),
        min_token_length=data.get("min_token_length", 2),
        drop_numeric_only=data.get("drop_numeric_only", True),
        sort_mode=data.get("sort_mode", "name_asc"),
    )


@router.post("/api/system/tag-match-setting", response_model=TagMatchSettingResponse)
def set_tag_match_setting_api(body: TagMatchSettingRequest) -> TagMatchSettingResponse:
    next_setting = set_tag_match_setting(body.model_dump())
    return TagMatchSettingResponse(
        enabled=next_setting.get("enabled", True),
        noise_tokens=next_setting.get("noise_tokens", []),
        min_token_length=next_setting.get("min_token_length", 2),
        drop_numeric_only=next_setting.get("drop_numeric_only", True),
        sort_mode=next_setting.get("sort_mode", "name_asc"),
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