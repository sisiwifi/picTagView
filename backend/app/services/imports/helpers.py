import ctypes
import datetime
import hashlib
import mimetypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Optional

from app.core.config import MEDIA_DIR, PROJECT_ROOT
from app.services.app_settings_service import get_month_cover_size_px
from app.services.image_frame_service import extract_preview_frame_from_bytes, extract_preview_frame_from_path

IMAGE_EXTS = {".jpg", ".jpeg", ".tiff", ".tif", ".png", ".webp", ".gif", ".bmp"}


def is_image_ext(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTS


def date_group_from_ts(ts_ms: Optional[int]) -> str:
    if ts_ms is not None:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000.0)
    else:
        dt = datetime.datetime.now()
    return f"{dt.year}-{dt.month:02d}"


def to_project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def resolve_stored_path(stored_path: Optional[str]) -> Optional[Path]:
    if not stored_path:
        return None
    path = Path(stored_path)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def quick_hash_from_bytes(content: bytes) -> str:
    try:
        import xxhash

        return xxhash.xxh64(content).hexdigest()
    except Exception:
        return hashlib.sha256(content).hexdigest()[:16]


def mime_from_name(name: str) -> str:
    mime = mimetypes.guess_type(name)[0]
    if mime:
        return mime
    return "application/octet-stream"


def image_metadata_from_bytes(
    content: bytes,
) -> tuple[Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    try:
        frame = extract_preview_frame_from_bytes(content)
        return frame.width, frame.height, frame.is_animated, frame.frame_count, frame.animation_format
    except Exception:
        return None, None, None, None, None


def image_metadata_from_file(
    path: Path,
) -> tuple[Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    try:
        frame = extract_preview_frame_from_path(path)
        return frame.width, frame.height, frame.is_animated, frame.frame_count, frame.animation_format
    except Exception:
        return None, None, None, None, None


def image_dimensions_from_bytes(content: bytes) -> tuple[Optional[int], Optional[int]]:
    width, height, _is_animated, _frame_count, _animation_format = image_metadata_from_bytes(content)
    return width, height


def image_dimensions_from_file(path: Path) -> tuple[Optional[int], Optional[int]]:
    width, height, _is_animated, _frame_count, _animation_format = image_metadata_from_file(path)
    return width, height


def normalize_animation_meta(
    animation_meta: object,
    *,
    frame_count: Optional[int] = None,
    animation_format: Optional[str] = None,
) -> Optional[dict[str, object]]:
    raw_meta = animation_meta if isinstance(animation_meta, dict) else {}

    raw_frame_count = frame_count if frame_count is not None else raw_meta.get("frame_count")
    raw_animation_format = (
        animation_format
        if animation_format is not None
        else raw_meta.get("format") or raw_meta.get("animation_format")
    )

    normalized_format = str(raw_animation_format or "").strip().upper() or None
    has_frame_count = raw_frame_count is not None or normalized_format is not None
    if not has_frame_count:
        return None

    normalized_frame_count = max(int(raw_frame_count or 1), 1)
    return {
        "frame_count": normalized_frame_count,
        "format": normalized_format,
    }


def animation_meta_parts(source: object) -> tuple[Optional[dict[str, object]], int, Optional[str]]:
    normalized_meta = normalize_animation_meta(getattr(source, "animation_meta", None))
    if not normalized_meta:
        return None, 1, None
    normalized_frame_count = max(int(normalized_meta.get("frame_count") or 1), 1)
    normalized_format = str(normalized_meta.get("format") or "").strip().upper() or None
    return normalized_meta, normalized_frame_count, normalized_format


def apply_animation_metadata(
    target: object,
    is_animated: Optional[bool],
    frame_count: Optional[int],
    animation_format: Optional[str],
) -> bool:
    if is_animated is None and frame_count is None and not animation_format:
        return False

    normalized_meta = normalize_animation_meta(
        getattr(target, "animation_meta", None),
        frame_count=frame_count,
        animation_format=animation_format,
    )
    normalized_frame_count = max(int((normalized_meta or {}).get("frame_count") or 1), 1)
    normalized_animation_format = str((normalized_meta or {}).get("format") or "").strip().upper() or None
    normalized_is_animated = bool(is_animated) or normalized_meta is not None or normalized_frame_count > 1
    if not normalized_is_animated:
        normalized_meta = None

    changed = False
    if getattr(target, "is_animated", None) != normalized_is_animated:
        setattr(target, "is_animated", normalized_is_animated)
        changed = True
    if normalize_animation_meta(getattr(target, "animation_meta", None)) != normalized_meta:
        setattr(target, "animation_meta", normalized_meta)
        changed = True
    return changed


def required_thumb_entry(thumb_path_str: str, width: Optional[int] = None, height: Optional[int] = None) -> dict:
    month_cover_size = get_month_cover_size_px()
    final_width = int(width if width is not None else month_cover_size)
    final_height = int(height if height is not None else month_cover_size)
    return {
        "type": "webp",
        "path": thumb_path_str,
        "width": final_width,
        "height": final_height,
        "mime_type": "image/webp",
        "generated_at": datetime.datetime.now().isoformat(),
    }


def thumb_file_exists(entry: dict) -> bool:
    path = resolve_stored_path(entry.get("path"))
    return bool(path and path.exists())


def upsert_thumb(thumbs: Optional[list[dict]], new_thumb: dict) -> list[dict]:
    items: list[dict] = [thumb for thumb in (thumbs or []) if isinstance(thumb, dict)]
    out: list[dict] = []
    replaced = False
    for item in items:
        if (
            item.get("type") == new_thumb.get("type")
            and item.get("width") == new_thumb.get("width")
            and item.get("height") == new_thumb.get("height")
        ):
            out.append(new_thumb)
            replaced = True
        else:
            out.append(item)
    if not replaced:
        out.append(new_thumb)
    return out


def has_required_thumb(thumbs: Optional[list[dict]]) -> bool:
    month_cover_size = get_month_cover_size_px()
    for entry in thumbs or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "webp":
            continue
        if int(entry.get("width") or 0) != month_cover_size or int(entry.get("height") or 0) != month_cover_size:
            continue
        if thumb_file_exists(entry):
            return True
    return False


def parse_relative_path(relative_path: str) -> tuple[list[str], str]:
    normalized = relative_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]

    if len(parts) <= 1:
        return [], parts[0] if parts else relative_path
    if len(parts) == 2:
        return [], parts[1]
    return list(parts[1:-1]), parts[-1]


def unique_dest(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    base, ext = os.path.splitext(filename)
    index = 1
    while True:
        candidate = dest_dir / f"{base}_{index}{ext}"
        if not candidate.exists():
            return candidate
        index += 1


def unique_dir_dest(parent_dir: Path, dirname: str) -> Path:
    dest = parent_dir / dirname
    if not dest.exists():
        return dest

    index = 1
    while True:
        candidate = parent_dir / f"{dirname}_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def min_source_ts_ms(created_ts_ms: Optional[int], modified_ts_ms: Optional[int]) -> Optional[int]:
    values = [
        ts for ts in (created_ts_ms, modified_ts_ms)
        if isinstance(ts, int) and ts > 0
    ]
    return min(values) if values else None


def set_windows_creation_time(path: Path, ts_seconds: float) -> None:
    file_write_attributes = 0x0100
    open_existing = 3
    file_share_read = 0x1
    file_share_write = 0x2
    file_share_delete = 0x4
    invalid_handle_value = ctypes.c_void_p(-1).value

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(
        str(path),
        file_write_attributes,
        file_share_read | file_share_write | file_share_delete,
        None,
        open_existing,
        0,
        None,
    )
    if handle == invalid_handle_value:
        raise ctypes.WinError()

    try:
        filetime_value = int((ts_seconds + 11644473600) * 10_000_000)
        creation_time = wintypes.FILETIME(
            filetime_value & 0xFFFFFFFF,
            (filetime_value >> 32) & 0xFFFFFFFF,
        )
        if not kernel32.SetFileTime(handle, ctypes.byref(creation_time), None, None):
            raise ctypes.WinError()
    finally:
        kernel32.CloseHandle(handle)


def apply_file_times(path: Path, source_time_ms: Optional[int]) -> None:
    if source_time_ms is None:
        return

    ts_seconds = source_time_ms / 1000.0
    try:
        os.utime(path, (ts_seconds, ts_seconds))
    except Exception:
        pass

    if os.name == "nt":
        try:
            set_windows_creation_time(path, ts_seconds)
        except Exception:
            pass


def save_to_media(
    content: bytes,
    filename: str,
    date_group: str,
    subdir_chain: list[str],
    source_time_ms: Optional[int] = None,
) -> Path:
    dest_dir = MEDIA_DIR / date_group
    for subdir in subdir_chain:
        dest_dir = dest_dir / subdir

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique_dest(dest_dir, filename)
    dest.write_bytes(content)
    apply_file_times(dest, source_time_ms)
    return dest
