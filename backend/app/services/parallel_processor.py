import hashlib
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.app_settings_service import get_month_cover_size_px
from app.services.image_frame_service import extract_preview_frame_from_bytes

_xxhash: Optional[Any] = None
try:
    import xxhash as _xxhash
except ImportError:
    pass

_THUMB_Q = 85

DEFAULT_WORKERS: int = min(os.cpu_count() or 1, 8)
IMPORT_BATCH_SIZE: int = 50
REFRESH_BATCH_SIZE: int = 200

ProcessResult = Tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[int],
    Optional[bool],
    Optional[int],
    Optional[str],
]


def _quick_hash(content: bytes) -> str:
    if _xxhash is not None:
        return _xxhash.xxh64(content).hexdigest()
    return hashlib.sha256(content).hexdigest()[:16]


def _square_crop(image, width: int, height: int):
    if width > height:
        start = (width - height) // 2
        return image[:, start:start + height]
    if height > width:
        start = (height - width) // 2
        return image[start:start + width, :]
    return image


# ── Top-level worker functions (must be picklable for ProcessPoolExecutor) ──────

def _process_from_path(
    args: Tuple[str, str, str, int],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    """
    Worker (ProcessPoolExecutor): read image from disk → SHA-256 hash → thumbnail.
    args = (key, file_path_str, temp_dir_str, thumb_size_px)
    returns (key, file_hash, thumb_path_str, error_str, quick_hash, width, height, is_animated, frame_count, animation_format)
    """
    key, file_path_str, temp_dir_str, thumb_size_px = args
    import cv2

    try:
        content = Path(file_path_str).read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        thumb_path = Path(temp_dir_str) / f"{file_hash}.webp"
        preview_frame = extract_preview_frame_from_bytes(content)
        img_w = preview_frame.width
        img_h = preview_frame.height

        if not thumb_path.exists():
            img = _square_crop(preview_frame.image, img_w, img_h)

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (thumb_size_px, thumb_size_px), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_WEBP_QUALITY), _THUMB_Q],
            )

        return (
            key,
            file_hash,
            str(thumb_path),
            None,
            qh,
            img_w,
            img_h,
            preview_frame.is_animated,
            preview_frame.frame_count,
            preview_frame.animation_format,
        )
    except Exception as exc:
        return key, None, None, str(exc), None, None, None, None, None, None


def _process_from_bytes(
    args: Tuple[str, bytes, str, int],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    """
    Worker (ThreadPoolExecutor): SHA-256 hash + thumbnail from in-memory bytes.
    Also returns quick_hash and image dimensions to avoid redundant decode.
    args = (key, content, temp_dir_str, thumb_size_px)
    returns (key, file_hash, thumb_path_str, error_str, quick_hash, width, height, is_animated, frame_count, animation_format)
    """
    key, content, temp_dir_str, thumb_size_px = args
    import cv2

    try:
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        thumb_path = Path(temp_dir_str) / f"{file_hash}.webp"
        preview_frame = extract_preview_frame_from_bytes(content)
        img_w = preview_frame.width
        img_h = preview_frame.height

        if not thumb_path.exists():
            img = _square_crop(preview_frame.image, img_w, img_h)

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (thumb_size_px, thumb_size_px), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_WEBP_QUALITY), _THUMB_Q],
            )

        return (
            key,
            file_hash,
            str(thumb_path),
            None,
            qh,
            img_w,
            img_h,
            preview_frame.is_animated,
            preview_frame.frame_count,
            preview_frame.animation_format,
        )
    except Exception as exc:
        return key, None, None, str(exc), None, None, None, None, None, None


def _compute_hash_only(
    args: Tuple[str, bytes],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    """
    Worker (ThreadPoolExecutor): SHA-256 + quick hash + image dimensions in parallel.
    Dimensions are computed here (cv2) to avoid serialising decode in the DB write loop.
    args = (key, content)
    returns (key, file_hash, error_str, quick_hash, width, height, is_animated, frame_count, animation_format)
    """
    key, content = args
    try:
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        preview_frame = extract_preview_frame_from_bytes(content)

        return (
            key,
            file_hash,
            None,
            qh,
            preview_frame.width,
            preview_frame.height,
            preview_frame.is_animated,
            preview_frame.frame_count,
            preview_frame.animation_format,
        )
    except Exception as exc:
        return key, None, str(exc), None, None, None, None, None, None


def _compute_hash_only_from_path(
    args: Tuple[str, str],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    """
    Worker (ProcessPoolExecutor): SHA-256 + quick hash + image dimensions from disk path.
    args = (key, file_path_str)
    returns (key, file_hash, error_str, quick_hash, width, height, is_animated, frame_count, animation_format)
    """
    key, file_path_str = args
    try:
        content = Path(file_path_str).read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        preview_frame = extract_preview_frame_from_bytes(content)

        return (
            key,
            file_hash,
            None,
            qh,
            preview_frame.width,
            preview_frame.height,
            preview_frame.is_animated,
            preview_frame.frame_count,
            preview_frame.animation_format,
        )
    except Exception as exc:
        return key, None, str(exc), None, None, None, None, None, None


# ── Public API ────────────────────────────────────────────────────────────────

def process_from_paths(
    entries: List[Tuple[str, str]],
    temp_dir: Path,
    max_workers: Optional[int] = None,
) -> Dict[str, ProcessResult]:
    """
    Process image files from disk paths using ProcessPoolExecutor.

    Parameters

    Returns
    -------
    {key: (file_hash, thumb_path_str, error_str, quick_hash, width, height, is_animated, frame_count, animation_format)}
    """
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    thumb_size_px = get_month_cover_size_px()
    temp_str = str(temp_dir)
    args_list = [(key, path, temp_str, thumb_size_px) for key, path in entries]
    results: Dict[str, ProcessResult] = {}

    with ProcessPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_process_from_path, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, file_hash, thumb_path, error, qh, w, h, is_animated, frame_count, animation_format = fut.result()
            results[key] = (file_hash, thumb_path, error, qh, w, h, is_animated, frame_count, animation_format)

    return results


def process_from_bytes(
    entries: List[Tuple[str, bytes]],
    temp_dir: Path,
    max_workers: Optional[int] = None,
) -> Dict[str, ProcessResult]:
    """Process image bytes using ThreadPoolExecutor."""
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    thumb_size_px = get_month_cover_size_px()
    temp_str = str(temp_dir)
    args_list = [(key, content, temp_str, thumb_size_px) for key, content in entries]
    results: Dict[str, ProcessResult] = {}

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_process_from_bytes, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, file_hash, thumb_path, error, qh, w, h, is_animated, frame_count, animation_format = fut.result()
            results[key] = (file_hash, thumb_path, error, qh, w, h, is_animated, frame_count, animation_format)

    return results


def process_hash_only_from_bytes(
    entries: List[Tuple[str, bytes]],
    max_workers: Optional[int] = None,
) -> Dict[str, ProcessResult]:
    """Compute SHA-256 + quick hash + dimensions using ThreadPoolExecutor."""
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    results: Dict[str, ProcessResult] = {}

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_compute_hash_only, (key, content)): key for key, content in entries}
        for fut in as_completed(futures):
            key, file_hash, error, qh, w, h, is_animated, frame_count, animation_format = fut.result()
            results[key] = (file_hash, None, error, qh, w, h, is_animated, frame_count, animation_format)

    return results


def process_hash_only_from_paths(
    entries: List[Tuple[str, str]],
    max_workers: Optional[int] = None,
) -> Dict[str, ProcessResult]:
    """Compute SHA-256 + quick hash + dimensions from disk paths using ProcessPoolExecutor."""
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    results: Dict[str, ProcessResult] = {}

    with ProcessPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_compute_hash_only_from_path, (key, path)): key for key, path in entries}
        for fut in as_completed(futures):
            key, file_hash, error, qh, w, h, is_animated, frame_count, animation_format = fut.result()
            results[key] = (file_hash, None, error, qh, w, h, is_animated, frame_count, animation_format)

    return results
