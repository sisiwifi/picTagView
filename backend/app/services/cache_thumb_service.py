import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

_CACHE_SHORT_SIDE = 600
_CACHE_QUALITY = 85


def _generate_cache_thumb_worker(
    args: Tuple[str, str, str],
) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Worker (ThreadPoolExecutor): read image from disk → scale to 600px short-side → WebP.
    args = (key, file_path_str, cache_dir_str)
    returns (key, cache_path_str, error_str)
    """
    key, file_path_str, cache_dir_str = args
    import cv2
    import numpy as np

    try:
        content = Path(file_path_str).read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        cache_path = Path(cache_dir_str) / f"{file_hash}_cache.webp"

        if cache_path.exists():
            return key, str(cache_path), None

        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return key, None, "decode_failed"

        h, w = img.shape[:2]
        short_side = min(h, w)
        if short_side > _CACHE_SHORT_SIDE:
            scale = _CACHE_SHORT_SIDE / short_side
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        cv2.imwrite(
            str(cache_path),
            img,
            [int(cv2.IMWRITE_WEBP_QUALITY), _CACHE_QUALITY],
        )
        return key, str(cache_path), None
    except Exception as exc:
        return key, None, str(exc)


def generate_cache_thumbs_from_paths(
    entries: List[Tuple[str, str]],
    cache_dir: Path,
    max_workers: int = 4,
) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """
    Generate cache thumbnails (600px short-side, original ratio, WebP) in parallel.

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

    cache_str = str(cache_dir)
    args_list = [(key, path, cache_str) for key, path in entries]
    results: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_generate_cache_thumb_worker, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, cache_path, error = fut.result()
            results[key] = (cache_path, error)

    return results


def generate_cache_thumbs_progressively(
    entries: List[Tuple[str, str]],
    cache_dir: Path,
    on_complete: Callable[[str, Optional[str], Optional[str]], None],
    max_workers: int = 8,
) -> None:
    """
    Generate cache thumbs and call on_complete(key, cache_path, error) as each finishes.
    Allows progressive result streaming instead of waiting for the full batch.
    """
    if not entries:
        return
    cache_str = str(cache_dir)
    args_list = [(key, path, cache_str) for key, path in entries]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_generate_cache_thumb_worker, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, cache_path, error = fut.result()
            on_complete(key, cache_path, error)
