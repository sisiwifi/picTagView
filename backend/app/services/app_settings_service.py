import json

from app.core.config import DATA_DIR

APP_SETTINGS_FILE = DATA_DIR / "app_settings.json"

DEFAULT_CACHE_SHORT_SIDE_PX = 600
MIN_CACHE_SHORT_SIDE_PX = 100
MAX_CACHE_SHORT_SIDE_PX = 4000

DEFAULT_MONTH_COVER_SIZE_PX = 400
MIN_MONTH_COVER_SIZE_PX = 100
MAX_MONTH_COVER_SIZE_PX = 2000

DEFAULT_TAG_MATCH_ENABLED = True
DEFAULT_TAG_MATCH_NOISE_TOKENS: list[str] = []
DEFAULT_TAG_MATCH_MIN_TOKEN_LENGTH = 2
MIN_TAG_MATCH_MIN_TOKEN_LENGTH = 1
MAX_TAG_MATCH_MIN_TOKEN_LENGTH = 32
DEFAULT_TAG_MATCH_DROP_NUMERIC_ONLY = True


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


def _sanitize_noise_tokens(raw_tokens: object) -> list[str]:
    if not isinstance(raw_tokens, list):
        return []

    seen: set[str] = set()
    result: list[str] = []
    for token in raw_tokens:
        if not isinstance(token, str):
            continue
        normalized = token.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def get_tag_match_setting() -> dict:
    data = load_app_settings()
    raw = data.get("tag_match_setting")
    if not isinstance(raw, dict):
        raw = {}

    min_token_length_raw = raw.get("min_token_length", DEFAULT_TAG_MATCH_MIN_TOKEN_LENGTH)
    try:
        min_token_length = int(min_token_length_raw)
    except Exception:
        min_token_length = DEFAULT_TAG_MATCH_MIN_TOKEN_LENGTH
    min_token_length = max(MIN_TAG_MATCH_MIN_TOKEN_LENGTH, min(MAX_TAG_MATCH_MIN_TOKEN_LENGTH, min_token_length))

    enabled = raw.get("enabled", DEFAULT_TAG_MATCH_ENABLED)
    drop_numeric_only = raw.get("drop_numeric_only", DEFAULT_TAG_MATCH_DROP_NUMERIC_ONLY)

    return {
        "enabled": bool(enabled),
        "noise_tokens": _sanitize_noise_tokens(raw.get("noise_tokens", DEFAULT_TAG_MATCH_NOISE_TOKENS)),
        "min_token_length": min_token_length,
        "drop_numeric_only": bool(drop_numeric_only),
        "sort_mode": "name_asc",
    }


def set_tag_match_setting(setting: dict) -> dict:
    if not isinstance(setting, dict):
        setting = {}

    current = get_tag_match_setting()

    if "enabled" in setting:
        current["enabled"] = bool(setting.get("enabled"))
    if "noise_tokens" in setting:
        current["noise_tokens"] = _sanitize_noise_tokens(setting.get("noise_tokens"))
    if "min_token_length" in setting:
        try:
            raw_length = int(setting.get("min_token_length"))
        except Exception:
            raw_length = DEFAULT_TAG_MATCH_MIN_TOKEN_LENGTH
        current["min_token_length"] = max(
            MIN_TAG_MATCH_MIN_TOKEN_LENGTH,
            min(MAX_TAG_MATCH_MIN_TOKEN_LENGTH, raw_length),
        )
    if "drop_numeric_only" in setting:
        current["drop_numeric_only"] = bool(setting.get("drop_numeric_only"))

    current["sort_mode"] = "name_asc"

    data = load_app_settings()
    data["tag_match_setting"] = {
        "enabled": current["enabled"],
        "noise_tokens": current["noise_tokens"],
        "min_token_length": current["min_token_length"],
        "drop_numeric_only": current["drop_numeric_only"],
        "sort_mode": "name_asc",
    }
    save_app_settings(data)
    return current
