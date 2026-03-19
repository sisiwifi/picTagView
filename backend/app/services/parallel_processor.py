import hashlib
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_THUMB_W = 400
_THUMB_H = 400
_THUMB_Q = 85

DEFAULT_WORKERS: int = min(os.cpu_count() or 1, 8)
IMPORT_BATCH_SIZE: int = 20
REFRESH_BATCH_SIZE: int = 200


# ── Top-level worker functions (must be picklable for ProcessPoolExecutor) ──────

def _process_from_path(
    args: Tuple[str, str, str],
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Worker (ProcessPoolExecutor): read image from disk → SHA-256 hash → thumbnail.
    args = (key, file_path_str, temp_dir_str)
    returns (key, file_hash, thumb_path_str, error_str)
    """
    key, file_path_str, temp_dir_str = args
    import cv2
    import numpy as np

    try:
        content = Path(file_path_str).read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        thumb_path = Path(temp_dir_str) / f"{file_hash}.webp"

        if not thumb_path.exists():
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return key, file_hash, None, "decode_failed"

            h, w = img.shape[:2]
            # 1:1 square crop
            if w > h:
                img = img[:, (w - h) // 2 : (w - h) // 2 + h]
            elif h > w:
                img = img[(h - w) // 2 : (h - w) // 2 + w, :]

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (_THUMB_W, _THUMB_H), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_WEBP_QUALITY), _THUMB_Q],
            )

        return key, file_hash, str(thumb_path), None
    except Exception as exc:
        return key, None, None, str(exc)


def _process_from_bytes(
    args: Tuple[str, bytes, str],
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Worker (ThreadPoolExecutor): SHA-256 hash + thumbnail from in-memory bytes.
    OpenCV and hashlib release the GIL during heavy operations, enabling real concurrency.
    args = (key, content, temp_dir_str)
    returns (key, file_hash, thumb_path_str, error_str)
    """
    key, content, temp_dir_str = args
    import cv2
    import numpy as np

    try:
        file_hash = hashlib.sha256(content).hexdigest()
        thumb_path = Path(temp_dir_str) / f"{file_hash}.webp"

        if not thumb_path.exists():
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return key, file_hash, None, "decode_failed"

            h, w = img.shape[:2]
            # 1:1 square crop
            if w > h:
                img = img[:, (w - h) // 2 : (w - h) // 2 + h]
            elif h > w:
                img = img[(h - w) // 2 : (h - w) // 2 + w, :]

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (_THUMB_W, _THUMB_H), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_WEBP_QUALITY), _THUMB_Q],
            )

        return key, file_hash, str(thumb_path), None
    except Exception as exc:
        return key, None, None, str(exc)


def _compute_hash_only(
    args: Tuple[str, bytes],
) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Worker (ThreadPoolExecutor): SHA-256 hash only, no thumbnail.
    args = (key, content)
    returns (key, file_hash, error_str)
    """
    key, content = args
    try:
        file_hash = hashlib.sha256(content).hexdigest()
        return key, file_hash, None
    except Exception as exc:
        return key, None, str(exc)


# ── Public API ────────────────────────────────────────────────────────────────

def process_from_paths(
    entries: List[Tuple[str, str]],
    temp_dir: Path,
    max_workers: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]]:
    """
    Process image files from disk paths using ProcessPoolExecutor.
    Workers read files independently — no large-byte IPC overhead.

    Parameters
    ----------
    entries     : list of (key, file_path_str)
    temp_dir    : directory for thumbnail output
    max_workers : worker process count; defaults to DEFAULT_WORKERS

    Returns
    -------
    {key: (file_hash, thumb_path_str, error_str)}
    """
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    temp_str = str(temp_dir)
    args_list = [(key, path, temp_str) for key, path in entries]
    results: Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]] = {}

    with ProcessPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_process_from_path, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, file_hash, thumb_path, error = fut.result()
            results[key] = (file_hash, thumb_path, error)

    return results


def process_from_bytes(
    entries: List[Tuple[str, bytes]],
    temp_dir: Path,
    max_workers: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]]:
    """
    Process image bytes using ThreadPoolExecutor.
    Avoids subprocess IPC pickling overhead while still achieving parallel CPU
    throughput because OpenCV and hashlib release the GIL.

    Parameters
    ----------
    entries     : list of (key, content_bytes)
    temp_dir    : directory for thumbnail output
    max_workers : thread count; defaults to DEFAULT_WORKERS

    Returns
    -------
    {key: (file_hash, thumb_path_str, error_str)}
    """
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    temp_str = str(temp_dir)
    args_list = [(key, content, temp_str) for key, content in entries]
    results: Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]] = {}

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_process_from_bytes, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, file_hash, thumb_path, error = fut.result()
            results[key] = (file_hash, thumb_path, error)

    return results


def process_hash_only_from_bytes(
    entries: List[Tuple[str, bytes]],
    max_workers: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]]:
    """
    Compute SHA-256 hashes only (no thumbnail generation) using ThreadPoolExecutor.

    Parameters
    ----------
    entries     : list of (key, content_bytes)
    max_workers : thread count; defaults to DEFAULT_WORKERS

    Returns
    -------
    {key: (file_hash, None, error_str)}
    """
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    results: Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]] = {}

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_compute_hash_only, (key, content)): key for key, content in entries}
        for fut in as_completed(futures):
            key, file_hash, error = fut.result()
            results[key] = (file_hash, None, error)

    return results
