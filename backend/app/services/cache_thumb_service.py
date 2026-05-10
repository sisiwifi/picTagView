import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from app.services.app_settings_service import get_cache_thumb_short_side_px
from app.services.image_frame_service import extract_preview_frame_from_bytes

_CACHE_QUALITY = 85


def get_cache_thumb_worker_count(
    reserve_cores: int = 2,
    hard_cap: int = 8,
) -> int:
    cpu_count = os.cpu_count() or 4
    return max(1, min(hard_cap, cpu_count - reserve_cores))


def _resolve_max_workers(max_workers: Optional[int]) -> int:
    if isinstance(max_workers, int) and max_workers > 0:
        return max_workers
    return get_cache_thumb_worker_count()


def _generate_cache_thumb_worker(
    args: Tuple[str, str, str, int],
) -> Tuple[str, Optional[str], Optional[str], Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    """
    Worker (ThreadPoolExecutor): read image from disk → scale to 600px short-side → WebP.
    args = (key, file_path_str, cache_dir_str, short_side_px)
    returns (key, cache_path_str, error_str, actual_width, actual_height, is_animated, frame_count, animation_format)
    """
    key, file_path_str, cache_dir_str, short_side_px = args
    import cv2
    import numpy as np

    try:
        content = Path(file_path_str).read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        cache_path = Path(cache_dir_str) / f"{file_hash}_cache.webp"
        preview_frame = extract_preview_frame_from_bytes(content)

        if cache_path.exists():
            # Read actual dimensions from the existing file
            existing = cv2.imdecode(np.frombuffer(cache_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
            if existing is not None:
                eh, ew = existing.shape[:2]
                return (
                    key,
                    str(cache_path),
                    None,
                    int(ew),
                    int(eh),
                    preview_frame.is_animated,
                    preview_frame.frame_count,
                    preview_frame.animation_format,
                )
            try:
                cache_path.unlink(missing_ok=True)
            except Exception:
                pass

        img = preview_frame.image

        h, w = img.shape[:2]
        short_side = min(h, w)
        if short_side > short_side_px:
            scale = short_side_px / short_side
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        out_h, out_w = img.shape[:2]
        cv2.imwrite(
            str(cache_path),
            img,
            [int(cv2.IMWRITE_WEBP_QUALITY), _CACHE_QUALITY],
        )
        return (
            key,
            str(cache_path),
            None,
            int(out_w),
            int(out_h),
            preview_frame.is_animated,
            preview_frame.frame_count,
            preview_frame.animation_format,
        )
    except Exception as exc:
        return key, None, str(exc), None, None, None, None, None


def generate_cache_thumb_entry(
    key: str,
    file_path_str: str,
    cache_dir: Path,
    short_side_px: Optional[int] = None,
) -> Tuple[str, Optional[str], Optional[str], Optional[int], Optional[int], Optional[bool], Optional[int], Optional[str]]:
    short_side = short_side_px or get_cache_thumb_short_side_px()
    return _generate_cache_thumb_worker((key, file_path_str, str(cache_dir), short_side))


def generate_cache_thumbs_from_paths(
    entries: List[Tuple[str, str]],
    cache_dir: Path,
    max_workers: Optional[int] = None,
    short_side_px: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """
    Generate cache thumbnails (configurable short-side, original ratio, WebP) in parallel.

    Parameters
    ----------
    entries     : list of (key, file_path_str)
    cache_dir   : output directory
    max_workers : thread count

    Returns
    -------
    {key: (cache_path_str, error_str)}
    """
    if not entries:
        return {}

    short_side = short_side_px or get_cache_thumb_short_side_px()
    cache_str = str(cache_dir)
    args_list = [(key, path, cache_str, short_side) for key, path in entries]
    results: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    with ThreadPoolExecutor(max_workers=_resolve_max_workers(max_workers)) as pool:
        futures = {pool.submit(_generate_cache_thumb_worker, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, cache_path, error, _w, _h, _is_animated, _frame_count, _animation_format = fut.result()
            results[key] = (cache_path, error)

    return results


def generate_cache_thumbs_progressively(
    entries: List[Tuple[str, str]],
    cache_dir: Path,
    on_complete: Callable[[str, Optional[str], Optional[str], Optional[int], Optional[int]], None],
    max_workers: Optional[int] = None,
    short_side_px: Optional[int] = None,
) -> None:
    """
    Generate cache thumbs and call on_complete(key, cache_path, error, width, height) as each finishes.
    Allows progressive result streaming instead of waiting for the full batch.
    """
    if not entries:
        return
    short_side = short_side_px or get_cache_thumb_short_side_px()
    cache_str = str(cache_dir)
    args_list = [(key, path, cache_str, short_side) for key, path in entries]
    with ThreadPoolExecutor(max_workers=_resolve_max_workers(max_workers)) as pool:
        futures = {pool.submit(_generate_cache_thumb_worker, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, cache_path, error, w, h, _is_animated, _frame_count, _animation_format = fut.result()
            on_complete(key, cache_path, error, w, h)
