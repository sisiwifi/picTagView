import json

from app.core.config import DATA_DIR

APP_SETTINGS_FILE = DATA_DIR / "app_settings.json"

DEFAULT_CACHE_SHORT_SIDE_PX = 600
MIN_CACHE_SHORT_SIDE_PX = 100
MAX_CACHE_SHORT_SIDE_PX = 4000

DEFAULT_MONTH_COVER_SIZE_PX = 400
MIN_MONTH_COVER_SIZE_PX = 100
MAX_MONTH_COVER_SIZE_PX = 2000

DEFAULT_PAGE_BROWSE_MODE = "scroll"
PAGE_BROWSE_MODE_OPTIONS = {"scroll", "paged"}
DEFAULT_PAGE_SCROLL_WINDOW_SIZE = 100
PAGE_SCROLL_WINDOW_OPTIONS = tuple(range(40, 201, 20))


def _normalize_page_scroll_window_size(value: object) -> int:
    try:
        normalized = int(value)
    except Exception:
        return DEFAULT_PAGE_SCROLL_WINDOW_SIZE
    if normalized in PAGE_SCROLL_WINDOW_OPTIONS:
        return normalized
    return DEFAULT_PAGE_SCROLL_WINDOW_SIZE


def load_app_settings() -> dict:
    if not APP_SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_app_settings(data: dict) -> None:
    try:
        APP_SETTINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_cache_thumb_short_side_px() -> int:
    data = load_app_settings()
    value = data.get("cache_thumb_short_side_px")
    if isinstance(value, int):
        if value < MIN_CACHE_SHORT_SIDE_PX:
            return MIN_CACHE_SHORT_SIDE_PX
        if value > MAX_CACHE_SHORT_SIDE_PX:
            return MAX_CACHE_SHORT_SIDE_PX
        return value
    return DEFAULT_CACHE_SHORT_SIDE_PX


def set_cache_thumb_short_side_px(value: int) -> int:
    clamped = max(MIN_CACHE_SHORT_SIDE_PX, min(MAX_CACHE_SHORT_SIDE_PX, int(value)))
    data = load_app_settings()
    data["cache_thumb_short_side_px"] = clamped
    save_app_settings(data)
    return clamped


def get_month_cover_size_px() -> int:
    data = load_app_settings()
    value = data.get("month_cover_size_px")
    if isinstance(value, int):
        if value < MIN_MONTH_COVER_SIZE_PX:
            return MIN_MONTH_COVER_SIZE_PX
        if value > MAX_MONTH_COVER_SIZE_PX:
            return MAX_MONTH_COVER_SIZE_PX
        return value
    return DEFAULT_MONTH_COVER_SIZE_PX


def set_month_cover_size_px(value: int) -> int:
    clamped = max(MIN_MONTH_COVER_SIZE_PX, min(MAX_MONTH_COVER_SIZE_PX, int(value)))
    data = load_app_settings()
    data["month_cover_size_px"] = clamped
    save_app_settings(data)
    return clamped


def get_page_config() -> dict:
    data = load_app_settings()
    raw = data.get("page_config")
    if not isinstance(raw, dict):
        raw = {}

    browse_mode = str(raw.get("browse_mode", DEFAULT_PAGE_BROWSE_MODE) or DEFAULT_PAGE_BROWSE_MODE).strip()
    if browse_mode not in PAGE_BROWSE_MODE_OPTIONS:
        browse_mode = DEFAULT_PAGE_BROWSE_MODE
    scroll_window_size = _normalize_page_scroll_window_size(
        raw.get("scroll_window_size", DEFAULT_PAGE_SCROLL_WINDOW_SIZE),
    )

    return {
        "browse_mode": browse_mode,
        "scroll_window_size": scroll_window_size,
    }


def set_page_config(setting: dict) -> dict:
    if not isinstance(setting, dict):
        setting = {}

    current = get_page_config()

    if "browse_mode" in setting:
        browse_mode = str(setting.get("browse_mode") or DEFAULT_PAGE_BROWSE_MODE).strip()
        if browse_mode not in PAGE_BROWSE_MODE_OPTIONS:
            browse_mode = DEFAULT_PAGE_BROWSE_MODE
        current["browse_mode"] = browse_mode

    if "scroll_window_size" in setting:
        current["scroll_window_size"] = _normalize_page_scroll_window_size(
            setting.get("scroll_window_size"),
        )

    data = load_app_settings()
    data["page_config"] = {
        "browse_mode": current["browse_mode"],
        "scroll_window_size": current["scroll_window_size"],
    }
    save_app_settings(data)
    return current
