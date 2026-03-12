import hashlib
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_THUMB_W = 300
_THUMB_H = 200
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
        thumb_path = Path(temp_dir_str) / f"{file_hash}.jpg"

        if not thumb_path.exists():
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return key, file_hash, None, "decode_failed"

            h, w = img.shape[:2]
            r = _THUMB_W / _THUMB_H
            if w / h > r:
                nw = int(h * r)
                img = img[:, (w - nw) // 2 : (w - nw) // 2 + nw]
            else:
                nh = int(w / r)
                img = img[(h - nh) // 2 : (h - nh) // 2 + nh, :]

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (_THUMB_W, _THUMB_H), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_JPEG_QUALITY), _THUMB_Q],
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
        thumb_path = Path(temp_dir_str) / f"{file_hash}.jpg"

        if not thumb_path.exists():
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return key, file_hash, None, "decode_failed"

            h, w = img.shape[:2]
            r = _THUMB_W / _THUMB_H
            if w / h > r:
                nw = int(h * r)
                img = img[:, (w - nw) // 2 : (w - nw) // 2 + nw]
            else:
                nh = int(w / r)
                img = img[(h - nh) // 2 : (h - nh) // 2 + nh, :]

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (_THUMB_W, _THUMB_H), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_JPEG_QUALITY), _THUMB_Q],
            )

        return key, file_hash, str(thumb_path), None
    except Exception as exc:
        return key, None, None, str(exc)


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
