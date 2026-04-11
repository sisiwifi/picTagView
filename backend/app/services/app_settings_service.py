import json

from app.core.config import DATA_DIR

APP_SETTINGS_FILE = DATA_DIR / "app_settings.json"

DEFAULT_CACHE_SHORT_SIDE_PX = 600
MIN_CACHE_SHORT_SIDE_PX = 100
MAX_CACHE_SHORT_SIDE_PX = 4000

DEFAULT_MONTH_COVER_SIZE_PX = 400
MIN_MONTH_COVER_SIZE_PX = 100
MAX_MONTH_COVER_SIZE_PX = 2000


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
