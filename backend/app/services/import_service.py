import datetime
import hashlib
import json
import mimetypes
import os
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlmodel import col, select

from app.core.config import CACHE_DIR, MEDIA_DIR, PROJECT_ROOT, TEMP_DIR
from app.db.session import get_session, init_db
from app.models.album import Album
from app.models.image_asset import ImageAsset
from app.models.soft_delete import PathSoftDelete
from sqlalchemy import not_, exists
from app.services.parallel_processor import (
    IMPORT_BATCH_SIZE,
    process_from_bytes,
    process_from_paths,
    process_hash_only_from_bytes,
)


IMAGE_EXTS = {".jpg", ".jpeg", ".tiff", ".tif", ".png", ".webp", ".gif", ".bmp"}

# ── Hash index cache ─────────────────────────────────────────────────────────
_HASH_INDEX_PATH = MEDIA_DIR / ".hash_index.json"
_hash_index: Optional[Dict[str, int]] = None
_quick_hash_index: Optional[Dict[str, str]] = None  # quick_hash -> file_hash
# ── Album chain cache (per-import) ────────────────────────────────
_album_chain_cache: Dict[str, List[str]] = {}

def _load_hash_index() -> None:
    global _hash_index, _quick_hash_index
    if _hash_index is not None:
        return
    if _HASH_INDEX_PATH.exists():
        try:
            raw = json.loads(_HASH_INDEX_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "hash_to_id" in raw:
                _hash_index = raw["hash_to_id"]
                _quick_hash_index = raw.get("quick_to_hash", {})
            else:
                _hash_index = raw if isinstance(raw, dict) else {}
                _quick_hash_index = {}
        except Exception:
            _hash_index = {}
            _quick_hash_index = {}
    else:
        _hash_index = {}
        _quick_hash_index = {}


def _save_hash_index() -> None:
    if _hash_index is None:
        return
    try:
        data = {
            "hash_to_id": _hash_index,
            "quick_to_hash": _quick_hash_index or {},
        }
        _HASH_INDEX_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def _add_to_hash_index(file_hash: str, image_id: int, quick_hash: Optional[str] = None) -> None:
    global _hash_index, _quick_hash_index
    if _hash_index is None:
        _hash_index = {}
    _hash_index[file_hash] = image_id
    if quick_hash:
        if _quick_hash_index is None:
            _quick_hash_index = {}
        _quick_hash_index[quick_hash] = file_hash


def _lookup_hash_index(file_hash: str) -> Optional[int]:
    if _hash_index is None:
        return None
    return _hash_index.get(file_hash)


def _lookup_quick_hash(quick_hash: str) -> Optional[str]:
    """Return file_hash if quick_hash is known, else None."""
    if _quick_hash_index is None:
        return None
    return _quick_hash_index.get(quick_hash)


def _clear_hash_index_memory() -> None:
    global _hash_index, _quick_hash_index
    _hash_index = None
    _quick_hash_index = None


def rebuild_hash_index() -> None:
    global _hash_index, _quick_hash_index
    _hash_index = {}
    _quick_hash_index = {}
    with get_session() as session:
        for asset in session.exec(select(ImageAsset)).all():
            if asset.file_hash and asset.id is not None:
                _hash_index[asset.file_hash] = asset.id
                if asset.quick_hash:
                    _quick_hash_index[asset.quick_hash] = asset.file_hash
    _save_hash_index()


def _is_image_ext(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTS


def _date_group_from_ts(ts_ms: Optional[int]) -> str:
    if ts_ms is not None:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000.0)
    else:
        dt = datetime.datetime.now()
    return f"{dt.year}-{dt.month:02d}"


def _to_project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _resolve_stored_path(stored_path: Optional[str]) -> Optional[Path]:
    if not stored_path:
        return None
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def _quick_hash_from_bytes(content: bytes) -> str:
    try:
        import xxhash  # type: ignore

        return xxhash.xxh64(content).hexdigest()
    except Exception:
        # Fallback keeps the field populated even if xxhash is temporarily unavailable.
        return hashlib.sha256(content).hexdigest()[:16]


def _mime_from_name(name: str) -> str:
    mime = mimetypes.guess_type(name)[0]
    if mime:
        return mime
    return "application/octet-stream"


def _image_dimensions_from_bytes(content: bytes) -> Tuple[Optional[int], Optional[int]]:
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None, None
        h, w = img.shape[:2]
        return int(w), int(h)
    except Exception:
        return None, None


def _image_dimensions_from_file(path: Path) -> Tuple[Optional[int], Optional[int]]:
    try:
        return _image_dimensions_from_bytes(path.read_bytes())
    except Exception:
        return None, None


def _required_thumb_entry(thumb_path_str: str, width: int = 400, height: int = 400) -> dict:
    return {
        "type": "webp",
        "path": thumb_path_str,
        "width": width,
        "height": height,
        "mime_type": "image/webp",
        "generated_at": datetime.datetime.now().isoformat(),
    }


def _thumb_file_exists(entry: dict) -> bool:
    p = _resolve_stored_path(entry.get("path"))
    return bool(p and p.exists())


def _upsert_thumb(thumbs: Optional[list[dict]], new_thumb: dict) -> list[dict]:
    items: list[dict] = [t for t in (thumbs or []) if isinstance(t, dict)]
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


def _has_required_thumb(thumbs: Optional[list[dict]]) -> bool:
    for entry in thumbs or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "webp":
            continue
        if int(entry.get("width") or 0) != 400 or int(entry.get("height") or 0) != 400:
            continue
        if _thumb_file_exists(entry):
            return True
    return False


def _parse_relative_path(relative_path: str) -> Tuple[List[str], str]:
    """
    Parse webkitRelativePath into (subdir_chain, filename).

    "rootdir/image.jpg"               → ([], "image.jpg")
    "rootdir/subdir/image.jpg"        → (["subdir"], "image.jpg")
    "rootdir/subdir/nested/image.jpg" → (["subdir", "nested"], "image.jpg")
    """
    normalized = relative_path.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]

    if len(parts) <= 1:
        return [], parts[0] if parts else relative_path
    elif len(parts) == 2:
        return [], parts[1]
    else:
        return list(parts[1:-1]), parts[-1]


def _unique_dest(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    base, ext = os.path.splitext(filename)
    i = 1
    while True:
        candidate = dest_dir / f"{base}_{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def _min_source_ts_ms(
    created_ts_ms: Optional[int],
    modified_ts_ms: Optional[int],
) -> Optional[int]:
    values = [
        ts for ts in (created_ts_ms, modified_ts_ms)
        if isinstance(ts, int) and ts > 0
    ]
    return min(values) if values else None


def _set_windows_creation_time(path: Path, ts_seconds: float) -> None:
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


def _apply_file_times(path: Path, source_time_ms: Optional[int]) -> None:
    if source_time_ms is None:
        return

    ts_seconds = source_time_ms / 1000.0
    try:
        os.utime(path, (ts_seconds, ts_seconds))
    except Exception:
        pass

    if os.name == "nt":
        try:
            _set_windows_creation_time(path, ts_seconds)
        except Exception:
            pass


def _save_to_media(
    content: bytes,
    filename: str,
    date_group: str,
    subdir_chain: List[str],
    source_time_ms: Optional[int] = None,
) -> Path:
    dest_dir = MEDIA_DIR / date_group
    for sub in subdir_chain:
        dest_dir = dest_dir / sub

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_dest(dest_dir, filename)
    dest.write_bytes(content)
    _apply_file_times(dest, source_time_ms)
    return dest


# ── Album helpers ─────────────────────────────────────────────────────────────

def _ensure_album_chain(session, subdir_chain: List[str], date_group: str) -> List[str]:
    """
    Create or find the Album chain for subdirectory path.
    Returns list of public_ids forming the full path from root to leaf.
    """
    if not subdir_chain:
        return []

    public_ids: List[str] = []
    parent_id: Optional[int] = None
    path_parts = [date_group]

    for i, subdir_name in enumerate(subdir_chain):
        path_parts.append(subdir_name)
        album_path = "/".join(path_parts)
        is_last = i == len(subdir_chain) - 1

        existing = session.exec(
            select(Album).where(Album.path == album_path)
        ).first()

        if existing:
            if not is_last and existing.is_leaf:
                existing.is_leaf = False
                session.add(existing)
            public_ids.append(existing.public_id)
            parent_id = existing.id
        else:
            album = Album(
                public_id="",
                title=subdir_name,
                path=album_path,
                is_leaf=is_last,
                parent_id=parent_id,
                date_group=date_group,
            )
            session.add(album)
            session.flush()
            album.public_id = f"album_{album.id}"
            session.add(album)
            public_ids.append(album.public_id)
            parent_id = album.id

    return public_ids


def _ensure_album_chain_cached(session, subdir_chain: List[str], date_group: str) -> List[str]:
    """Cached wrapper: avoids repeated DB queries for the same album path."""
    cache_key = date_group + "/" + "/".join(subdir_chain)
    cached = _album_chain_cache.get(cache_key)
    if cached is not None:
        return cached
    result = _ensure_album_chain(session, subdir_chain, date_group)
    _album_chain_cache[cache_key] = result
    return result


def _update_album_photo_counts(session, public_ids: List[str]) -> None:
    """Increment photo_count for leaf album and subtree_photo_count for all ancestors."""
    if not public_ids:
        return
    for i, pid in enumerate(public_ids):
        album = session.exec(select(Album).where(Album.public_id == pid)).first()
        if not album:
            continue
        album.subtree_photo_count = (album.subtree_photo_count or 0) + 1
        if i == len(public_ids) - 1:
            album.photo_count = (album.photo_count or 0) + 1
        session.add(album)


def _set_album_cover_if_needed(session, public_ids: List[str], asset: ImageAsset) -> None:
    """Set album cover to alphabetically first filename (for each album in chain)."""
    if not public_ids:
        return
    new_filename = asset.full_filename or ""
    for pid in public_ids:
        album = session.exec(select(Album).where(Album.public_id == pid)).first()
        if not album:
            continue
        current_cover = album.cover or {}
        current_filename = current_cover.get("filename", "")
        if not current_filename or new_filename < current_filename:
            thumb_path = ""
            for t in (asset.thumbs or []):
                if isinstance(t, dict) and t.get("path"):
                    thumb_path = t["path"]
                    break
            album.cover = {
                "photo_id": asset.id,
                "thumb_path": thumb_path,
                "filename": new_filename,
                "updated_at": datetime.datetime.now().isoformat(),
            }
            session.add(album)


async def import_files(
    files: List[UploadFile],
    last_modified_times: Optional[List[Optional[int]]] = None,
    created_times: Optional[List[Optional[int]]] = None,
) -> Dict[str, List[str]]:
    """
    groupByDate-aware import with parallel hash and thumbnail generation.

    Phase 1 – Collect metadata (no file content reads).
    Phase 2 – Derive per-subdir date groups + determine which files need thumbnails.
              Only the earliest-timestamp file per NEW date_group gets a thumbnail.
    Phase 3 – Process in batches: parallel CPU work → sequential DB writes.
    """
    init_db()
    _load_hash_index()
    _album_chain_cache.clear()
    imported: List[str] = []
    skipped: List[str] = []

    # ── Phase 1: Collect metadata ─────────────────────────────────────────
    metadata = []
    for idx, upload in enumerate(files):
        raw_filename = upload.filename or ""
        ts_ms: Optional[int] = (
            last_modified_times[idx]
            if last_modified_times and idx < len(last_modified_times)
            else None
        )
        created_ts_ms: Optional[int] = (
            created_times[idx]
            if created_times and idx < len(created_times)
            else None
        )
        subdir_chain, filename = _parse_relative_path(raw_filename)
        if not _is_image_ext(filename):
            skipped.append(raw_filename or "unknown")
            continue

        metadata.append({
            "upload": upload,
            "original": raw_filename,
            "ts_ms": ts_ms,
            "created_ts_ms": created_ts_ms,
            "source_time_ms": _min_source_ts_ms(created_ts_ms, ts_ms),
            "subdir_chain": subdir_chain,
            "filename": filename,
        })

    # ── Phase 2: Per-subdir minimum timestamp ─────────────────────────────
    subdir_min_ts: Dict[str, int] = {}
    for meta in metadata:
        if meta["subdir_chain"]:
            top_subdir = meta["subdir_chain"][0]
            ts = meta["ts_ms"] if meta["ts_ms"] is not None else int(
                datetime.datetime.now().timestamp() * 1000
            )
            if top_subdir not in subdir_min_ts or ts < subdir_min_ts[top_subdir]:
                subdir_min_ts[top_subdir] = ts

    # ── Phase 2.5: Determine which files need thumbnails ──────────────────
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    for meta in metadata:
        is_direct = not meta["subdir_chain"]
        top_subdir = meta["subdir_chain"][0] if meta["subdir_chain"] else None
        effective_ts = (
            meta["ts_ms"]
            if is_direct
            else subdir_min_ts.get(top_subdir)
        )
        meta["effective_ts"] = effective_ts if effective_ts is not None else now_ms
        meta["date_group_computed"] = _date_group_from_ts(
            meta["ts_ms"] if is_direct else subdir_min_ts.get(top_subdir)
        )

    # Which date_groups already have a valid thumbnail in the DB?
    all_groups = {meta["date_group_computed"] for meta in metadata}
    with get_session() as session:
        groups_with_thumb: set = set()
        candidates = session.exec(
            select(ImageAsset)
            .where(col(ImageAsset.date_group).in_(list(all_groups)))
            .where(col(ImageAsset.thumbs).isnot(None))
        ).all()
        for _a in candidates:
            if _has_required_thumb(_a.thumbs):
                groups_with_thumb.add(_a.date_group)

    # Find the earliest file per NEW date_group
    new_group_first_idx: Dict[str, int] = {}
    for idx, meta in enumerate(metadata):
        dg = meta["date_group_computed"]
        if dg in groups_with_thumb:
            continue
        if dg not in new_group_first_idx or (
            meta["effective_ts"] < metadata[new_group_first_idx[dg]]["effective_ts"]
        ):
            new_group_first_idx[dg] = idx

    thumb_needed_indices = set(new_group_first_idx.values())
    for idx, meta in enumerate(metadata):
        meta["needs_thumb"] = idx in thumb_needed_indices

    # ── Phase 3: Batch parallel processing ───────────────────────────────
    for batch_start in range(0, len(metadata), IMPORT_BATCH_SIZE):
        batch_meta = metadata[batch_start : batch_start + IMPORT_BATCH_SIZE]

        # Read file content (async) for this batch only
        batch_ready = []
        for meta in batch_meta:
            content = await meta["upload"].read()
            if not content:
                skipped.append(meta["original"])
                continue
            batch_ready.append((meta, content))

        if not batch_ready:
            continue

        # ── Pre-dedup: xxhash inline (~1ms/file) to skip known duplicates ─
        pre_resolved: Dict[int, Tuple] = {}
        for i, (meta, content) in enumerate(batch_ready):
            qh = _quick_hash_from_bytes(content)
            meta["_quick_hash"] = qh
            known_fh = _lookup_quick_hash(qh)
            if known_fh is not None and _lookup_hash_index(known_fh) is not None:
                pre_resolved[i] = (known_fh, None, None, qh, None, None)

        # Split remaining (non-pre-resolved) by thumbnail requirement
        thumb_entries = [
            (str(i), content)
            for i, (meta, content) in enumerate(batch_ready)
            if i not in pre_resolved and meta["needs_thumb"]
        ]
        hash_entries = [
            (str(i), content)
            for i, (meta, content) in enumerate(batch_ready)
            if i not in pre_resolved and not meta["needs_thumb"]
        ]

        proc_thumb = process_from_bytes(thumb_entries, TEMP_DIR) if thumb_entries else {}
        proc_hash = process_hash_only_from_bytes(hash_entries) if hash_entries else {}
        proc = {**proc_thumb, **proc_hash}
        for i, v in pre_resolved.items():
            proc[str(i)] = v

        # Sequential: DB lookup, dedup, file save, DB write
        with get_session() as session:
            for i, (meta, content) in enumerate(batch_ready):
                result = proc.get(str(i), (None, None, "no result", None, None, None))
                file_hash, thumb_path_str, _error = result[0], result[1], result[2]
                quick_hash = result[3]
                px_w = result[4]
                px_h = result[5]
                orig = meta["original"]
                file_size = len(content)
                mime_type = _mime_from_name(meta["filename"])
                file_created_at = None
                if isinstance(meta.get("source_time_ms"), int) and meta["source_time_ms"] > 0:
                    file_created_at = datetime.datetime.fromtimestamp(meta["source_time_ms"] / 1000.0)

                if not file_hash:
                    skipped.append(orig)
                    continue

                subdir_chain = meta["subdir_chain"]
                is_direct = not subdir_chain
                top_subdir = subdir_chain[0] if subdir_chain else None

                rel_thumb_path = (
                    _to_project_relative(Path(thumb_path_str)) if thumb_path_str else None
                )
                new_thumb = _required_thumb_entry(rel_thumb_path) if rel_thumb_path else None

                date_group = (
                    _date_group_from_ts(meta["ts_ms"])
                    if is_direct
                    else _date_group_from_ts(subdir_min_ts.get(top_subdir))
                )

                # ── Dedup: check hash cache first, then DB ────────────────
                cached_id = _lookup_hash_index(file_hash)
                existing = None
                if cached_id is not None:
                    existing = session.get(ImageAsset, cached_id)
                if existing is None:
                    existing = session.exec(
                        select(ImageAsset).where(ImageAsset.file_hash == file_hash)
                    ).first()

                if existing:
                    # Duplicate found
                    if subdir_chain:
                        # Album import: save file, add album membership
                        album_public_ids = _ensure_album_chain_cached(session, subdir_chain, date_group)
                        media_path = _save_to_media(
                            content, meta["filename"], date_group,
                            subdir_chain, meta["source_time_ms"],
                        )
                        new_media_rel = _to_project_relative(media_path)

                        existing_media = existing.media_path or []
                        existing_media.append(new_media_rel)
                        existing.media_path = existing_media

                        existing_album = existing.album or []
                        existing_album.append(album_public_ids)
                        existing.album = existing_album

                        if new_thumb:
                            existing.thumbs = _upsert_thumb(existing.thumbs, new_thumb)

                        session.add(existing)

                        _update_album_photo_counts(session, album_public_ids)
                        _set_album_cover_if_needed(session, album_public_ids, existing)
                        _add_to_hash_index(file_hash, existing.id, quick_hash)
                        imported.append(orig)
                    else:
                        # Direct duplicate: repair if media missing, else skip
                        thumb_ok = _has_required_thumb(existing.thumbs)
                        media_resolved = _resolve_stored_path(
                            existing.media_path[0] if existing.media_path else None
                        )
                        media_ok = bool(media_resolved and media_resolved.exists())

                        needs_update = False
                        if not media_ok:
                            media_path = _save_to_media(
                                content, meta["filename"], date_group,
                                subdir_chain, meta["source_time_ms"],
                            )
                            existing.media_path = [_to_project_relative(media_path)]
                            existing.date_group = date_group
                            needs_update = True
                        if not thumb_ok and meta["needs_thumb"] and new_thumb:
                            existing.thumbs = _upsert_thumb(existing.thumbs, new_thumb)
                            needs_update = True
                        if not existing.quick_hash:
                            existing.quick_hash = quick_hash
                            needs_update = True
                        if not existing.file_created_at and file_created_at is not None:
                            existing.file_created_at = file_created_at
                            needs_update = True
                        if not existing.width and px_w is not None:
                            existing.width = px_w
                            needs_update = True
                        if not existing.height and px_h is not None:
                            existing.height = px_h
                            needs_update = True
                        if not existing.file_size:
                            existing.file_size = file_size
                            needs_update = True
                        if not existing.mime_type:
                            existing.mime_type = mime_type
                            needs_update = True
                        if not existing.full_filename:
                            existing.full_filename = Path(meta["filename"]).name
                            needs_update = True
                        if existing.tags is None:
                            existing.tags = []
                            needs_update = True
                        if existing.category is None:
                            existing.category = ""
                            needs_update = True
                        if existing.imported_at is None:
                            existing.imported_at = datetime.datetime.now()
                            needs_update = True

                        if needs_update:
                            session.add(existing)
                            _add_to_hash_index(file_hash, existing.id, quick_hash)
                            imported.append(orig)
                        else:
                            skipped.append(orig)
                    continue

                # ── New record ─────────────────────────────────────────────
                # Dimensions come from the parallel phase (cv2 ran in ThreadPoolExecutor).
                # Fallback only if the worker failed to decode (e.g. corrupted file).
                if px_w is None or px_h is None:
                    px_w, px_h = _image_dimensions_from_bytes(content)

                album_public_ids = _ensure_album_chain_cached(session, subdir_chain, date_group) if subdir_chain else []
                media_path = _save_to_media(
                    content, meta["filename"], date_group,
                    subdir_chain, meta["source_time_ms"],
                )
                asset = ImageAsset(
                    original_path=orig,
                    full_filename=Path(meta["filename"]).name,
                    file_hash=file_hash,
                    quick_hash=quick_hash,
                    thumbs=[new_thumb] if new_thumb else [],
                    media_path=[_to_project_relative(media_path)],
                    date_group=date_group,
                    file_created_at=file_created_at,
                    imported_at=datetime.datetime.now(),
                    width=px_w,
                    height=px_h,
                    file_size=file_size,
                    mime_type=mime_type,
                    category="",
                    tags=[],
                    album=[album_public_ids] if album_public_ids else [],
                    collection=[],
                )
                session.add(asset)
                session.flush()  # get asset.id for hash index

                if album_public_ids:
                    _update_album_photo_counts(session, album_public_ids)
                    _set_album_cover_if_needed(session, album_public_ids, asset)

                _add_to_hash_index(file_hash, asset.id, quick_hash)
                imported.append(orig)

            session.commit()  # batch commit

        del batch_ready  # release batch content from memory

    _save_hash_index()
    return {"imported": imported, "skipped": skipped}


def refresh_library() -> Dict[str, int]:
    """
    Refresh / repair the media library.

    Step 0 – Prune orphaned cache thumbnails.
    Step 1 – Prune DB records whose media file is missing.
    Step 2 – Ensure each date_group representative has a valid 400x400 temp thumbnail.
    Step 3 – Maintain essential metadata fields.

    Returns { pruned, total_images, cache_deleted, regenerated }.
    """
    init_db()
    pruned = 0
    regenerated = 0

    # ── Step 0: Prune orphaned cache thumbnails ───────────────────────────
    with get_session() as session:
        live_hashes: set = set()
        for a in session.exec(select(ImageAsset)).all():
            media_path = _resolve_stored_path(a.media_path[0] if a.media_path else None)
            if a.file_hash and media_path and media_path.exists():
                live_hashes.add(a.file_hash)

    cache_deleted = 0
    for cache_file in CACHE_DIR.iterdir():
        if not cache_file.is_file():
            continue
        stem = cache_file.stem
        if not stem.endswith("_cache"):
            continue
        file_hash = stem[:-6]
        if file_hash not in live_hashes:
            try:
                cache_file.unlink()
                cache_deleted += 1
            except Exception:
                pass

    # ── Step 1: Prune orphaned records ────────────────────────────────────
    with get_session() as session:
        all_assets = session.exec(select(ImageAsset)).all()
        for asset in all_assets:
            media_path = _resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if asset.media_path and not (media_path and media_path.exists()):
                for entry in asset.thumbs or []:
                    if not isinstance(entry, dict):
                        continue
                    p = _resolve_stored_path(entry.get("path"))
                    if p and p.exists():
                        try:
                            p.unlink()
                        except Exception:
                            pass

                session.delete(asset)
                pruned += 1
        session.commit()

    # ── Step 2: Keep one required temp-thumb per date_group ───────────────
    with get_session() as session:
        remaining = session.exec(
            select(ImageAsset).order_by(col(ImageAsset.id))
        ).all()

        total_images = len(remaining)

        group_rep: Dict[str, ImageAsset] = {}
        for asset in remaining:
            if asset.date_group and asset.date_group not in group_rep:
                group_rep[asset.date_group] = asset

        needs_thumb: List[ImageAsset] = []
        for asset in group_rep.values():
            media_path = _resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if not media_path or not media_path.exists():
                continue
            if not _has_required_thumb(asset.thumbs):
                needs_thumb.append(asset)

    if needs_thumb:
        entries = [(str(a.id), str(_resolve_stored_path(a.media_path[0] if a.media_path else None))) for a in needs_thumb if _resolve_stored_path(a.media_path[0] if a.media_path else None)]
        proc = process_from_paths(entries, TEMP_DIR)
    else:
        proc = {}

    # ── Step 3: DB writes + metadata maintenance ──────────────────────────
    with get_session() as session:
        for asset in remaining:
            media_path = _resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if not media_path or not media_path.exists():
                continue

            db_asset = session.exec(
                select(ImageAsset).where(ImageAsset.id == asset.id)
            ).first()
            if not db_asset:
                continue

            result = proc.get(str(asset.id))
            if result:
                _file_hash, thumb_path_str, _error = result[0], result[1], result[2]
                proc_qh = result[3]
                proc_w = result[4]
                proc_h = result[5]
            else:
                _file_hash, thumb_path_str, _error = None, None, "not processed"
                proc_qh, proc_w, proc_h = None, None, None

            if not db_asset.quick_hash:
                if proc_qh:
                    db_asset.quick_hash = proc_qh
                else:
                    content = media_path.read_bytes()
                    db_asset.quick_hash = _quick_hash_from_bytes(content)
            if not db_asset.width or not db_asset.height:
                if proc_w is not None and proc_h is not None:
                    db_asset.width, db_asset.height = proc_w, proc_h
                else:
                    db_asset.width, db_asset.height = _image_dimensions_from_file(media_path)
            if not db_asset.file_size:
                db_asset.file_size = media_path.stat().st_size
            if not db_asset.mime_type:
                db_asset.mime_type = _mime_from_name(media_path.name)
            if not db_asset.full_filename:
                db_asset.full_filename = media_path.name
            if db_asset.tags is None:
                db_asset.tags = []
            if db_asset.category is None:
                db_asset.category = ""
            # Prune stale thumbs entries whose files no longer exist
            if db_asset.thumbs:
                live: list[dict] = []
                for t in db_asset.thumbs:
                    if not isinstance(t, dict):
                        continue
                    p = _resolve_stored_path(t.get("path"))
                    if p and p.exists():
                        live.append(t)
                db_asset.thumbs = live

            if thumb_path_str:
                rel_thumb = _to_project_relative(Path(thumb_path_str))
                db_asset.thumbs = _upsert_thumb(db_asset.thumbs, _required_thumb_entry(rel_thumb))
                regenerated += 1

            session.add(db_asset)
        session.commit()

    rebuild_hash_index()
    recalculate_album_counts()

    return {
        "pruned": pruned,
        "total_images": total_images,
        "cache_deleted": cache_deleted,
        "regenerated": regenerated,
    }


def _ia_not_deleted_for_refresh():
    return not_(
        exists(
            select(PathSoftDelete.id)
            .where(PathSoftDelete.entity_type == "image")
            .where(PathSoftDelete.owner_id == ImageAsset.id)
        )
    )

def recalculate_album_counts() -> None:
    """Recalculate photo_count, subtree_photo_count, and covers for all albums."""
    with get_session() as session:
        albums = session.exec(select(Album).order_by(col(Album.id))).all()
        album_map = {a.public_id: a for a in albums}

        # Reset all counts
        for a in albums:
            a.photo_count = 0
            a.subtree_photo_count = 0

        # Track best cover candidate per album (alphabetically first filename among all images in subtree)
        cover_candidates: Dict[str, ImageAsset] = {}

        # Count images per leaf album
        all_assets = session.exec(select(ImageAsset).where(_ia_not_deleted_for_refresh())).all()
        for asset in all_assets:
            for path in (asset.album or []):
                if not isinstance(path, list) or not path:
                    continue
                for pid in path:
                    if pid in album_map:
                        album_map[pid].subtree_photo_count += 1
                    # Track cover candidate: strictly alphabetically first filename
                    fname = asset.full_filename or ""
                    current_fname = (cover_candidates[pid].full_filename or "") if pid in cover_candidates else ""
                    # Always replace if alphabetically first
                    if pid not in cover_candidates or (fname < current_fname):
                        cover_candidates[pid] = asset
                leaf_pid = path[-1]
                if leaf_pid in album_map:
                    album_map[leaf_pid].photo_count += 1

        # Update covers
        for pid, candidate in cover_candidates.items():
            if pid not in album_map:
                continue
            album = album_map[pid]
            thumb_path = ""
            for t in (candidate.thumbs or []):
                if isinstance(t, dict) and t.get("path"):
                    resolved = _resolve_stored_path(t["path"])
                    if resolved and resolved.exists():
                        thumb_path = t["path"]
                        break
            album.cover = {
                "photo_id": candidate.id,
                "thumb_path": thumb_path,
                "filename": candidate.full_filename or "",
                "updated_at": datetime.datetime.now().isoformat(),
            }

        for a in albums:
            session.add(a)
        session.commit()
