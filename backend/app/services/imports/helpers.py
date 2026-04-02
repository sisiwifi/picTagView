import ctypes
import datetime
import hashlib
import mimetypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Optional

from app.core.config import MEDIA_DIR, PROJECT_ROOT

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


def image_dimensions_from_bytes(content: bytes) -> tuple[Optional[int], Optional[int]]:
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None, None
        height, width = img.shape[:2]
        return int(width), int(height)
    except Exception:
        return None, None


def image_dimensions_from_file(path: Path) -> tuple[Optional[int], Optional[int]]:
    try:
        return image_dimensions_from_bytes(path.read_bytes())
    except Exception:
        return None, None


def required_thumb_entry(thumb_path_str: str, width: int = 400, height: int = 400) -> dict:
    return {
        "type": "webp",
        "path": thumb_path_str,
        "width": width,
        "height": height,
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
    for entry in thumbs or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "webp":
            continue
        if int(entry.get("width") or 0) != 400 or int(entry.get("height") or 0) != 400:
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
