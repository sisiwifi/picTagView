"""
Import service — fully integrates groupByDate logic:

Rules (mirroring comp/groupByDate/groupByDate.py):
- Image files directly in the selected root folder are saved individually,
  each grouped by the file's own lastModified time (browser) → media/<YYYY-M>/file.ext
- Top-level sub-directories (and everything inside them) are treated as a UNIT.
  Their date group is the minimum lastModified time across all images in that
  sub-directory tree (proxy for the directory's creation time used by groupByDate).
  All files keep their relative path:  media/<YYYY-M>/<subdir>/<...>/file.ext

The frontend must send each file with file.webkitRelativePath as the multipart
filename (third arg to FormData.append) so the path structure is preserved.
"""

import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlmodel import select

from app.core.config import MEDIA_DIR
from app.db.session import get_session, init_db
from app.models.image_asset import ImageAsset
from app.services.hash_service import hash_bytes
from app.services.thumbnail_service import create_thumbnail_from_bytes


IMAGE_EXTS = {".jpg", ".jpeg", ".tiff", ".tif", ".png", ".webp", ".gif", ".bmp"}


def _is_image_ext(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTS


def _date_group_from_ts(ts_ms: Optional[int]) -> str:
    """
    Convert a JS lastModified timestamp (milliseconds) to non-padded 'YYYY-M'.
    Falls back to the current date when ts_ms is None.
    """
    if ts_ms is not None:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000.0)
    else:
        dt = datetime.datetime.now()
    return f"{dt.year}-{dt.month}"


def _parse_relative_path(relative_path: str) -> Tuple[bool, Optional[str], str]:
    """
    Parse the webkitRelativePath sent as the multipart filename.

    Examples
    --------
    "rootdir/image.jpg"                → (True,  None,     "image.jpg")
    "rootdir/subdir/image.jpg"         → (False, "subdir", "image.jpg")
    "rootdir/subdir/nested/image.jpg"  → (False, "subdir", "nested/image.jpg")

    Returns
    -------
    is_direct    : True when the file sits directly in the selected root folder.
    top_subdir   : Name of the first-level sub-directory (None for direct files).
    file_subpath : Relative path of the file *below* top_subdir (or just the
                   filename for direct files).
    """
    normalized = relative_path.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]

    if len(parts) <= 1:
        # Bare filename — no directory nesting
        return True, None, parts[0] if parts else relative_path
    elif len(parts) == 2:
        # rootdir/file.jpg — direct file
        return True, None, parts[1]
    else:
        # rootdir/subdir/[nested/...]file.jpg
        top_subdir = parts[1]
        file_subpath = "/".join(parts[2:])
        return False, top_subdir, file_subpath


def _unique_dest(dest_dir: Path, filename: str) -> Path:
    """Return a non-conflicting path inside dest_dir."""
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
    """
    Write content to:
      • Direct file  → media/<date_group>/<filename>
      • In subdir    → media/<date_group>/<top_subdir>/<file_subpath>

    Name conflicts are resolved by appending _1, _2, … to the stem.
    """
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
    groupByDate-aware import.

    Phase 1 – Read all uploaded files and classify them (direct / in sub-dir).
    Phase 2 – Derive per-subdir date groups (min lastModified of its images).
    Phase 3 – Process each file: dedup check → thumbnail → media save → DB.
    """
    init_db()
    imported: List[str] = []
    skipped: List[str] = []

    # ── Phase 1: collect ─────────────────────────────────────────────────────
    records = []
    for idx, upload in enumerate(files):
        raw_filename = upload.filename or ""
        ts_ms: Optional[int] = (
            last_modified_times[idx]
            if last_modified_times and idx < len(last_modified_times)
            else None
        )

        is_direct, top_subdir, file_subpath = _parse_relative_path(raw_filename)
        bare_name = Path(file_subpath).name

        if not _is_image_ext(bare_name):
            skipped.append(raw_filename or "unknown")
            continue

        content = await upload.read()
        if not content:
            skipped.append(raw_filename or "unknown")
            continue

        records.append(
            {
                "original": raw_filename,
                "content": content,
                "ts_ms": ts_ms,
                "is_direct": is_direct,
                "top_subdir": top_subdir,   # None for direct files
                "file_subpath": file_subpath,  # relative to top_subdir (or root)
            }
        )

    # ── Phase 2: compute per-subdir date (min ts_ms of all images in subdir) ─
    subdir_min_ts: Dict[str, int] = {}
    for rec in records:
        if not rec["is_direct"] and rec["top_subdir"]:
            subdir = rec["top_subdir"]
            ts = rec["ts_ms"] if rec["ts_ms"] is not None else int(
                datetime.datetime.now().timestamp() * 1000
            )
            if subdir not in subdir_min_ts or ts < subdir_min_ts[subdir]:
                subdir_min_ts[subdir] = ts

    # ── Phase 3: process ─────────────────────────────────────────────────────
    with get_session() as session:
        for rec in records:
            content = rec["content"]
            file_hash = hash_bytes(content)
            orig = rec["original"]

            # Determine date group
            if rec["is_direct"]:
                date_group = _date_group_from_ts(rec["ts_ms"])
            else:
                date_group = _date_group_from_ts(
                    subdir_min_ts.get(rec["top_subdir"])
                )

            existing = session.exec(
                select(ImageAsset).where(ImageAsset.file_hash == file_hash)
            ).first()

            if existing:
                thumb_ok = bool(existing.thumb_path) and Path(existing.thumb_path).exists()
                media_ok = bool(existing.media_path) and Path(existing.media_path).exists()

                if thumb_ok and media_ok:
                    # ── Case A: true duplicate ──
                    skipped.append(orig)
                    continue

                if thumb_ok and not media_ok:
                    # ── Case B: thumbnail exists but media missing → migrate ──
                    media_path = _save_to_media(
                        content, rec["file_subpath"], date_group, rec["top_subdir"]
                    )
                    existing.media_path = str(media_path)
                    existing.date_group = date_group
                    session.add(existing)
                    session.commit()
                    imported.append(orig)
                    continue

                # ── Fallback: record exists but inconsistent → treat as new ──

            # ── Case C: brand-new (or inconsistent) record ──
            try:
                thumb_path = create_thumbnail_from_bytes(content, file_hash)
            except ValueError:
                skipped.append(orig)
                continue

            media_path = _save_to_media(
                content, rec["file_subpath"], date_group, rec["top_subdir"]
            )

            if existing:
                existing.thumb_path = str(thumb_path)
                existing.media_path = str(media_path)
                existing.date_group = date_group
                session.add(existing)
            else:
                session.add(
                    ImageAsset(
                        original_path=orig,
                        file_hash=file_hash,
                        thumb_path=str(thumb_path),
                        media_path=str(media_path),
                        date_group=date_group,
                    )
                )

            session.commit()
            imported.append(orig)

    return {"imported": imported, "skipped": skipped}
