import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlmodel import select

from app.core.config import MEDIA_DIR, TEMP_DIR
from app.db.session import get_session, init_db
from app.models.image_asset import ImageAsset
from app.services.parallel_processor import (
    IMPORT_BATCH_SIZE,
    process_from_bytes,
    process_from_paths,
)


IMAGE_EXTS = {".jpg", ".jpeg", ".tiff", ".tif", ".png", ".webp", ".gif", ".bmp"}


def _is_image_ext(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTS


def _date_group_from_ts(ts_ms: Optional[int]) -> str:
    if ts_ms is not None:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000.0)
    else:
        dt = datetime.datetime.now()
    return f"{dt.year}-{dt.month}"


def _parse_relative_path(relative_path: str) -> Tuple[bool, Optional[str], str]:
    """
    Parse webkitRelativePath into (is_direct, top_subdir, file_subpath).

    "rootdir/image.jpg"               → (True,  None,     "image.jpg")
    "rootdir/subdir/image.jpg"        → (False, "subdir", "image.jpg")
    "rootdir/subdir/nested/image.jpg" → (False, "subdir", "nested/image.jpg")
    """
    normalized = relative_path.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]

    if len(parts) <= 1:
        return True, None, parts[0] if parts else relative_path
    elif len(parts) == 2:
        return True, None, parts[1]
    else:
        return False, parts[1], "/".join(parts[2:])


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


def _save_to_media(
    content: bytes,
    file_subpath: str,
    date_group: str,
    top_subdir: Optional[str],
) -> Path:
    if top_subdir:
        dest_dir = MEDIA_DIR / date_group / top_subdir / Path(file_subpath).parent
    else:
        dest_dir = MEDIA_DIR / date_group

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_dest(dest_dir, Path(file_subpath).name)
    dest.write_bytes(content)
    return dest


async def import_files(
    files: List[UploadFile],
    last_modified_times: Optional[List[Optional[int]]] = None,
) -> Dict[str, List[str]]:
    """
    groupByDate-aware import with parallel hash and thumbnail generation.

    Phase 1 – Collect metadata (no file content reads).
    Phase 2 – Derive per-subdir date groups.
    Phase 3 – Process in batches: parallel CPU work (ThreadPoolExecutor) → sequential DB writes.
              Each batch keeps at most IMPORT_BATCH_SIZE files in memory.
    """
    init_db()
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
        is_direct, top_subdir, file_subpath = _parse_relative_path(raw_filename)
        if not _is_image_ext(Path(file_subpath).name):
            skipped.append(raw_filename or "unknown")
            continue

        metadata.append({
            "upload": upload,
            "original": raw_filename,
            "ts_ms": ts_ms,
            "is_direct": is_direct,
            "top_subdir": top_subdir,
            "file_subpath": file_subpath,
        })

    # ── Phase 2: Per-subdir minimum timestamp ─────────────────────────────
    subdir_min_ts: Dict[str, int] = {}
    for meta in metadata:
        if not meta["is_direct"] and meta["top_subdir"]:
            subdir = meta["top_subdir"]
            ts = meta["ts_ms"] if meta["ts_ms"] is not None else int(
                datetime.datetime.now().timestamp() * 1000
            )
            if subdir not in subdir_min_ts or ts < subdir_min_ts[subdir]:
                subdir_min_ts[subdir] = ts

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

        # Parallel: hash + thumbnail via ThreadPoolExecutor
        byte_entries = [(str(i), content) for i, (_, content) in enumerate(batch_ready)]
        proc = process_from_bytes(byte_entries, TEMP_DIR)

        # Sequential: DB lookup, dedup, file save, DB write
        with get_session() as session:
            for i, (meta, content) in enumerate(batch_ready):
                file_hash, thumb_path_str, error = proc.get(str(i), (None, None, "no result"))
                orig = meta["original"]

                if not file_hash:
                    skipped.append(orig)
                    continue

                date_group = (
                    _date_group_from_ts(meta["ts_ms"])
                    if meta["is_direct"]
                    else _date_group_from_ts(subdir_min_ts.get(meta["top_subdir"]))
                )

                existing = session.exec(
                    select(ImageAsset).where(ImageAsset.file_hash == file_hash)
                ).first()

                if existing:
                    thumb_ok = bool(existing.thumb_path) and Path(existing.thumb_path).exists()
                    media_ok = bool(existing.media_path) and Path(existing.media_path).exists()

                    if thumb_ok and media_ok:
                        # Case A: true duplicate
                        skipped.append(orig)
                        continue

                    if thumb_ok and not media_ok:
                        # Case B: thumbnail exists but media missing
                        media_path = _save_to_media(
                            content, meta["file_subpath"], date_group, meta["top_subdir"]
                        )
                        existing.media_path = str(media_path)
                        existing.date_group = date_group
                        session.add(existing)
                        session.commit()
                        imported.append(orig)
                        continue

                # Case C: new or inconsistent record
                if error and not thumb_path_str:
                    skipped.append(orig)
                    continue

                media_path = _save_to_media(
                    content, meta["file_subpath"], date_group, meta["top_subdir"]
                )

                if existing:
                    existing.thumb_path = thumb_path_str
                    existing.media_path = str(media_path)
                    existing.date_group = date_group
                    session.add(existing)
                else:
                    session.add(
                        ImageAsset(
                            original_path=orig,
                            file_hash=file_hash,
                            thumb_path=thumb_path_str,
                            media_path=str(media_path),
                            date_group=date_group,
                        )
                    )
                session.commit()
                imported.append(orig)

        del batch_ready  # release batch content from memory

    return {"imported": imported, "skipped": skipped}


def refresh_library() -> Dict[str, int]:
    """
    Refresh / repair the media library with parallel processing.

    Step 1 – Prune orphaned DB records and their thumbnail files.
    Step 2 – Build in-memory lookup maps; skip already-healthy files.
    Step 3 – Parallel hash + thumbnail (ProcessPoolExecutor) for new/broken files.
    Step 4 – Sequential DB writes for repaired / new assets.
    """
    init_db()
    pruned = repaired = errors = 0

    # ── Step 1: Prune orphaned records ────────────────────────────────────
    with get_session() as session:
        all_assets = session.exec(select(ImageAsset)).all()
        for asset in all_assets:
            if asset.media_path and not Path(asset.media_path).exists():
                if asset.thumb_path:
                    try:
                        p = Path(asset.thumb_path)
                        if p.exists():
                            p.unlink()
                    except Exception:
                        pass
                session.delete(asset)
                pruned += 1
        session.commit()

        # Build in-memory lookup maps (one DB round-trip)
        remaining = session.exec(select(ImageAsset)).all()

        # Paths of files fully healthy (media + thumbnail both present)
        known_healthy: set = {
            a.media_path
            for a in remaining
            if (
                a.media_path
                and Path(a.media_path).exists()
                and a.thumb_path
                and Path(a.thumb_path).exists()
            )
        }

        # hash → (thumb_path, thumb_exists) for files that need repair check
        hash_map: Dict[str, Tuple[Optional[str], bool]] = {
            a.file_hash: (
                a.thumb_path,
                bool(a.thumb_path) and Path(a.thumb_path).exists(),
            )
            for a in remaining
        }

    # ── Step 2: Collect files that need processing ────────────────────────
    all_files = [
        fp for fp in MEDIA_DIR.rglob("*")
        if fp.is_file() and _is_image_ext(fp.name)
    ]

    # Skip files already confirmed healthy by path
    to_process = [fp for fp in all_files if str(fp) not in known_healthy]

    if not to_process:
        return {"pruned": pruned, "repaired": repaired, "errors": errors}

    # ── Step 3: Parallel hash + thumbnail ─────────────────────────────────
    entries = [(str(fp), str(fp)) for fp in to_process]
    proc = process_from_paths(entries, TEMP_DIR)

    # ── Step 4: Sequential DB writes ──────────────────────────────────────
    with get_session() as session:
        for fp in to_process:
            key = str(fp)
            file_hash, thumb_path_str, error = proc.get(key, (None, None, "not processed"))

            if not file_hash:
                errors += 1
                continue

            try:
                date_group = fp.relative_to(MEDIA_DIR).parts[0]
            except (ValueError, IndexError):
                continue

            existing_thumb, thumb_ok = hash_map.get(file_hash, (None, False))

            if existing_thumb:
                # Record exists in DB
                if thumb_ok:
                    continue  # healthy (path-based skip missed it) — no-op
                if error:
                    errors += 1
                    continue
                # Repair: thumbnail was missing, now regenerated
                db_asset = session.exec(
                    select(ImageAsset).where(ImageAsset.file_hash == file_hash)
                ).first()
                if db_asset:
                    db_asset.thumb_path = thumb_path_str
                    db_asset.media_path = str(fp)
                    db_asset.date_group = date_group
                    session.add(db_asset)
                    session.commit()
                    repaired += 1
            else:
                # Brand-new file
                if error:
                    errors += 1
                    continue
                session.add(
                    ImageAsset(
                        original_path=str(fp),
                        file_hash=file_hash,
                        thumb_path=thumb_path_str,
                        media_path=str(fp),
                        date_group=date_group,
                    )
                )
                session.commit()
                repaired += 1

    return {"pruned": pruned, "repaired": repaired, "errors": errors}
