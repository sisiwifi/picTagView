import hashlib
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import xxhash as _xxhash  # type: ignore
except ImportError:
    _xxhash = None

_THUMB_W = 400
_THUMB_H = 400
_THUMB_Q = 85

DEFAULT_WORKERS: int = min(os.cpu_count() or 1, 8)
IMPORT_BATCH_SIZE: int = 20
REFRESH_BATCH_SIZE: int = 200


def _quick_hash(content: bytes) -> str:
    if _xxhash is not None:
        return _xxhash.xxh64(content).hexdigest()
    return hashlib.sha256(content).hexdigest()[:16]


# ── Top-level worker functions (must be picklable for ProcessPoolExecutor) ──────

def _process_from_path(
    args: Tuple[str, str, str],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]:
    """
    Worker (ProcessPoolExecutor): read image from disk → SHA-256 hash → thumbnail.
    args = (key, file_path_str, temp_dir_str)
    returns (key, file_hash, thumb_path_str, error_str, quick_hash, width, height)
    """
    key, file_path_str, temp_dir_str = args
    import cv2
    import numpy as np

    try:
        content = Path(file_path_str).read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        thumb_path = Path(temp_dir_str) / f"{file_hash}.webp"

        img_w, img_h = None, None
        if not thumb_path.exists():
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return key, file_hash, None, "decode_failed", qh, None, None

            img_h, img_w = img.shape[:2]
            # 1:1 square crop
            if img_w > img_h:
                img = img[:, (img_w - img_h) // 2 : (img_w - img_h) // 2 + img_h]
            elif img_h > img_w:
                img = img[(img_h - img_w) // 2 : (img_h - img_w) // 2 + img_w, :]

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (_THUMB_W, _THUMB_H), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_WEBP_QUALITY), _THUMB_Q],
            )
        else:
            # Thumb already exists, still need dimensions
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                img_h, img_w = img.shape[:2]

        return key, file_hash, str(thumb_path), None, qh, img_w, img_h
    except Exception as exc:
        return key, None, None, str(exc), None, None, None


def _process_from_bytes(
    args: Tuple[str, bytes, str],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]:
    """
    Worker (ThreadPoolExecutor): SHA-256 hash + thumbnail from in-memory bytes.
    Also returns quick_hash and image dimensions to avoid redundant decode.
    args = (key, content, temp_dir_str)
    returns (key, file_hash, thumb_path_str, error_str, quick_hash, width, height)
    """
    key, content, temp_dir_str = args
    import cv2
    import numpy as np

    try:
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        thumb_path = Path(temp_dir_str) / f"{file_hash}.webp"

        img_w, img_h = None, None
        if not thumb_path.exists():
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return key, file_hash, None, "decode_failed", qh, None, None

            img_h, img_w = img.shape[:2]
            # 1:1 square crop
            if img_w > img_h:
                img = img[:, (img_w - img_h) // 2 : (img_w - img_h) // 2 + img_h]
            elif img_h > img_w:
                img = img[(img_h - img_w) // 2 : (img_h - img_w) // 2 + img_w, :]

            cv2.imwrite(
                str(thumb_path),
                cv2.resize(img, (_THUMB_W, _THUMB_H), interpolation=cv2.INTER_AREA),
                [int(cv2.IMWRITE_WEBP_QUALITY), _THUMB_Q],
            )
        else:
            # Thumb already exists, still need dimensions
            arr = np.frombuffer(content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                img_h, img_w = img.shape[:2]

        return key, file_hash, str(thumb_path), None, qh, img_w, img_h
    except Exception as exc:
        return key, None, None, str(exc), None, None, None


def _compute_hash_only(
    args: Tuple[str, bytes],
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]:
    """
    Worker (ThreadPoolExecutor): SHA-256 + quick hash + image dimensions (no thumbnail).
    args = (key, content)
    returns (key, file_hash, error_str, quick_hash, width, height)
    """
    key, content = args
    import cv2
    import numpy as np

    try:
        file_hash = hashlib.sha256(content).hexdigest()
        qh = _quick_hash(content)
        img_w, img_h = None, None
        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            img_h, img_w = img.shape[:2]
        return key, file_hash, None, qh, img_w, img_h
    except Exception as exc:
        return key, None, str(exc), None, None, None


# ── Public API ────────────────────────────────────────────────────────────────

def process_from_paths(
    entries: List[Tuple[str, str]],
    temp_dir: Path,
    max_workers: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]]:
    """
    Process image files from disk paths using ProcessPoolExecutor.

    Parameters

    Returns
    -------
    {key: (file_hash, thumb_path_str, error_str, quick_hash, width, height)}
    """
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    temp_str = str(temp_dir)
    args_list = [(key, path, temp_str) for key, path in entries]
    results: Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]] = {}

    with ProcessPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_process_from_path, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, file_hash, thumb_path, error, qh, w, h = fut.result()
            results[key] = (file_hash, thumb_path, error, qh, w, h)

    return results


def process_from_bytes(
    entries: List[Tuple[str, bytes]],
    temp_dir: Path,
    max_workers: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]]:
    """Process image bytes using ThreadPoolExecutor."""
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    temp_str = str(temp_dir)
    args_list = [(key, content, temp_str) for key, content in entries]
    results: Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]] = {}

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_process_from_bytes, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            key, file_hash, thumb_path, error, qh, w, h = fut.result()
            results[key] = (file_hash, thumb_path, error, qh, w, h)

    return results


def process_hash_only_from_bytes(
    entries: List[Tuple[str, bytes]],
    max_workers: Optional[int] = None,
) -> Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]]:
    """Compute SHA-256 + quick hash + dimensions using ThreadPoolExecutor."""
    if not entries:
        return {}

    n = max_workers or DEFAULT_WORKERS
    results: Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[int]]] = {}

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_compute_hash_only, (key, content)): key for key, content in entries}
        for fut in as_completed(futures):
            key, file_hash, error, qh, w, h = fut.result()
            results[key] = (file_hash, None, error, qh, w, h)

    return results
