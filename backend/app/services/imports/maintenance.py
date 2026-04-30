import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import delete
from sqlmodel import col, select

from app.core.config import CACHE_DIR, MEDIA_DIR, TEMP_DIR
from app.db.session import get_session, init_db
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.models.trash_entry import TrashEntry
from app.services.cache_thumb_service import generate_cache_thumb_entry
from app.services.category_service import DEFAULT_CATEGORY_ID
from app.services.cover_service import build_asset_cover_payload, cover_is_manual, extract_cover_photo_id
from app.services.file_scanner import list_image_files
from app.services.parallel_processor import process_from_paths, process_hash_only_from_paths

from .hash_index import rebuild_hash_index
from .helpers import (
    has_required_thumb,
    image_dimensions_from_file,
    mime_from_name,
    quick_hash_from_bytes,
    required_thumb_entry,
    resolve_stored_path,
    to_project_relative,
    upsert_thumb,
)


def _normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _media_rel_parts(rel_path: str) -> Optional[tuple[str, list[str], str]]:
    parts = [part for part in _normalize_rel_path(rel_path).split("/") if part]
    if len(parts) < 3:
        return None
    if parts[0] != "media":
        return None
    date_group = parts[1]
    filename = parts[-1]
    subdir_chain = parts[2:-1]
    return date_group, subdir_chain, filename


def _is_album_media_path(rel_path: str) -> bool:
    parsed = _media_rel_parts(rel_path)
    if not parsed:
        return False
    _date_group, subdir_chain, _filename = parsed
    return len(subdir_chain) > 0


def _ensure_album_chain(session, subdir_chain: list[str], date_group: str) -> tuple[list[str], list[str]]:
    if not subdir_chain:
        return [], []

    public_ids: list[str] = []
    paths: list[str] = []
    parent_id: Optional[int] = None
    path_parts = [date_group]

    for index, subdir_name in enumerate(subdir_chain):
        path_parts.append(subdir_name)
        album_path = "/".join(path_parts)
        is_last = index == len(subdir_chain) - 1

        existing = session.exec(select(Album).where(Album.path == album_path)).first()
        if existing:
            if not is_last and existing.is_leaf:
                existing.is_leaf = False
            existing.updated_at = datetime.datetime.now()
            session.add(existing)
            public_ids.append(existing.public_id)
            paths.append(existing.path)
            parent_id = existing.id
            continue

        album = Album(
            public_id="",
            title=subdir_name,
            path=album_path,
            is_leaf=is_last,
            parent_id=parent_id,
            date_group=date_group,
            updated_at=datetime.datetime.now(),
        )
        session.add(album)
        session.flush()
        album.public_id = f"album_{album.id}"
        session.add(album)
        public_ids.append(album.public_id)
        paths.append(album.path)
        parent_id = album.id
    return public_ids, paths


def recalculate_album_counts() -> None:
    with get_session() as session:
        albums = session.exec(select(Album).order_by(col(Album.id))).all()
        album_map = {album.public_id: album for album in albums}
        album_id_by_pid: dict[str, int] = {
            album.public_id: album.id for album in albums if album.id is not None
        }
        manual_cover_photo_ids = {
            album.public_id: extract_cover_photo_id(album.cover)
            for album in albums
            if album.public_id and cover_is_manual(album.cover)
        }

        for album in albums:
            album.photo_count = 0
            album.subtree_photo_count = 0

        # Clear existing album_image rows and rebuild
        session.connection().execute(delete(AlbumImage))

        cover_candidates: dict[str, ImageAsset] = {}

        all_assets = session.exec(select(ImageAsset)).all()
        asset_by_id = {
            int(asset.id): asset
            for asset in all_assets
            if isinstance(asset.id, int)
        }
        for asset in all_assets:
            for path in (asset.album or []):
                if not isinstance(path, list) or not path:
                    continue
                for public_id in path:
                    if public_id in album_map:
                        album_map[public_id].subtree_photo_count += 1
                    filename = asset.full_filename or ""
                    current_filename = (
                        cover_candidates[public_id].full_filename or ""
                        if public_id in cover_candidates
                        else ""
                    )
                    if public_id not in cover_candidates or (filename < current_filename):
                        cover_candidates[public_id] = asset
                leaf_pid = path[-1]
                if leaf_pid in album_map:
                    album_map[leaf_pid].photo_count += 1
                # Write album_image row for the leaf album
                leaf_album_id = album_id_by_pid.get(leaf_pid)
                if leaf_album_id is not None and asset.id is not None:
                    session.add(AlbumImage(album_id=leaf_album_id, image_id=asset.id))

        def asset_belongs_to_album(asset: ImageAsset | None, public_id: str) -> bool:
            if asset is None:
                return False
            for chain in asset.album or []:
                if isinstance(chain, list) and public_id in chain:
                    return True
            return False

        for album in albums:
            public_id = album.public_id or ""
            manual_photo_id = manual_cover_photo_ids.get(public_id)
            manual_asset = asset_by_id.get(manual_photo_id) if manual_photo_id is not None else None
            if public_id and asset_belongs_to_album(manual_asset, public_id):
                album.cover = build_asset_cover_payload(manual_asset, manual=True)
                continue
            album.cover = build_asset_cover_payload(cover_candidates.get(public_id))

        for album in albums:
            session.add(album)
        session.commit()


def reconcile_library_paths() -> tuple[int, int, int, set[str]]:
    pruned = 0
    cleaned_paths = 0
    active_album_paths: set[str] = set()

    with get_session() as session:
        all_assets = session.exec(select(ImageAsset).order_by(col(ImageAsset.id))).all()
        for asset in all_assets:
            normalized_paths = [
                _normalize_rel_path(path)
                for path in (asset.media_path or [])
                if isinstance(path, str) and path
            ]

            live_paths: list[str] = []
            for rel_path in normalized_paths:
                media_path = resolve_stored_path(rel_path)
                if media_path and media_path.exists():
                    live_paths.append(rel_path)
                else:
                    cleaned_paths += 1

            if not live_paths:
                for entry in asset.thumbs or []:
                    if not isinstance(entry, dict):
                        continue
                    thumb_path = resolve_stored_path(entry.get("path"))
                    if thumb_path and thumb_path.exists():
                        try:
                            thumb_path.unlink()
                        except Exception:
                            pass
                session.delete(asset)
                pruned += 1
                continue

            unique_live: list[str] = []
            for rel_path in live_paths:
                if rel_path not in unique_live:
                    unique_live.append(rel_path)

            album_chains: list[list[str]] = []
            date_candidates: list[str] = []
            for rel_path in unique_live:
                parsed = _media_rel_parts(rel_path)
                if not parsed:
                    continue
                date_group, subdir_chain, _filename = parsed
                date_candidates.append(date_group)
                if subdir_chain:
                    public_ids, album_paths = _ensure_album_chain(session, subdir_chain, date_group)
                    for album_path in album_paths:
                        active_album_paths.add(album_path)
                    if public_ids and public_ids not in album_chains:
                        album_chains.append(public_ids)

            asset.media_path = unique_live
            asset.album = album_chains
            if date_candidates:
                asset.date_group = sorted(date_candidates)[0]
            session.add(asset)

        session.commit()

    with get_session() as session:
        all_albums = session.exec(select(Album)).all()
        for album in all_albums:
            if album.path not in active_album_paths:
                session.delete(album)
        session.commit()

    return pruned, 0, cleaned_paths, active_album_paths


def _first_live_media_path(asset: ImageAsset) -> Optional[Path]:
    for stored_path in asset.media_path or []:
        if not isinstance(stored_path, str) or not stored_path:
            continue
        resolved = resolve_stored_path(stored_path)
        if resolved and resolved.exists():
            return resolved
    return None


def _cache_hash_from_path(cache_path: str | Path | None) -> Optional[str]:
    if not cache_path:
        return None
    stem = Path(cache_path).stem
    if not stem.endswith("_cache"):
        return None
    file_hash = stem[:-6]
    return file_hash or None


def _repair_targeted_cache_entries(
    image_ids: list[int] | None = None,
    trash_entry_ids: list[int] | None = None,
) -> dict[str, int]:
    result = {
        "cache_images_repaired": 0,
        "cache_images_cleaned": 0,
        "cache_trash_repaired": 0,
        "cache_trash_cleaned": 0,
    }

    normalized_image_ids = sorted({int(value) for value in (image_ids or []) if int(value) > 0})
    normalized_trash_entry_ids = sorted({int(value) for value in (trash_entry_ids or []) if int(value) > 0})

    if normalized_image_ids:
        with get_session() as session:
            assets = session.exec(
                select(ImageAsset)
                .where(col(ImageAsset.id).in_(normalized_image_ids))
                .order_by(col(ImageAsset.id))
            ).all()

            changed = False
            for asset in assets:
                next_thumbs: list[dict] = []
                removed_missing_cache_refs = 0
                for thumb in asset.thumbs or []:
                    if not isinstance(thumb, dict):
                        continue
                    stored_path = thumb.get("path")
                    if not isinstance(stored_path, str) or not stored_path:
                        continue
                    resolved = resolve_stored_path(stored_path)
                    if resolved and resolved.exists():
                        next_thumbs.append(thumb)
                        continue
                    if stored_path.replace("\\", "/").startswith("data/cache/"):
                        removed_missing_cache_refs += 1
                        continue
                    next_thumbs.append(thumb)

                if removed_missing_cache_refs:
                    asset.thumbs = next_thumbs
                    changed = True
                    result["cache_images_cleaned"] += removed_missing_cache_refs

                media_path = _first_live_media_path(asset)
                if not media_path or asset.id is None:
                    session.add(asset)
                    continue

                _key, cache_path_str, error, width, height = generate_cache_thumb_entry(
                    str(asset.id),
                    str(media_path),
                    CACHE_DIR,
                )
                if error or not cache_path_str:
                    session.add(asset)
                    continue

                rel_cache_path = to_project_relative(Path(cache_path_str))
                next_hash = _cache_hash_from_path(cache_path_str)
                previous_hash = asset.file_hash
                previous_cache_exists = bool(
                    previous_hash and (CACHE_DIR / f"{previous_hash}_cache.webp").exists()
                )
                next_thumb_entry = required_thumb_entry(
                    rel_cache_path,
                    width=width or 0,
                    height=height or 0,
                )
                updated_thumbs = upsert_thumb(asset.thumbs, next_thumb_entry)
                if updated_thumbs != asset.thumbs:
                    asset.thumbs = updated_thumbs
                    changed = True
                if next_hash and asset.file_hash != next_hash:
                    asset.file_hash = next_hash
                    changed = True
                if not previous_cache_exists or removed_missing_cache_refs:
                    result["cache_images_repaired"] += 1

                session.add(asset)

            if changed:
                session.commit()

    if normalized_trash_entry_ids:
        with get_session() as session:
            entries = session.exec(
                select(TrashEntry)
                .where(col(TrashEntry.id).in_(normalized_trash_entry_ids))
                .order_by(col(TrashEntry.id))
            ).all()

            changed = False
            for entry in entries:
                resolved_cache_path = resolve_stored_path(entry.preview_cache_path)
                cache_missing = bool(
                    entry.preview_cache_path
                    and (resolved_cache_path is None or not resolved_cache_path.exists())
                )
                if cache_missing:
                    entry.preview_cache_path = None
                    changed = True
                    result["cache_trash_cleaned"] += 1

                preview_source = resolve_stored_path(entry.preview_path)
                if not preview_source or not preview_source.exists() or not preview_source.is_file():
                    session.add(entry)
                    continue

                _key, cache_path_str, error, _width, _height = generate_cache_thumb_entry(
                    str(entry.id or ""),
                    str(preview_source),
                    CACHE_DIR,
                )
                if error or not cache_path_str:
                    session.add(entry)
                    continue

                rel_cache_path = to_project_relative(Path(cache_path_str))
                next_hash = _cache_hash_from_path(cache_path_str)
                if entry.preview_cache_path != rel_cache_path:
                    entry.preview_cache_path = rel_cache_path
                    changed = True
                if next_hash and entry.file_hash != next_hash:
                    entry.file_hash = next_hash
                    changed = True
                if cache_missing or not entry.preview_cache_path:
                    result["cache_trash_repaired"] += 1

                session.add(entry)

            if changed:
                session.commit()

    return result


def ingest_media_entries(
    entries: list[tuple[str, Path]],
    generate_thumbs: bool = True,
) -> tuple[int, int, list[dict[str, str]]]:
    if not entries:
        return 0, 0, []

    created = 0
    hash_conflicts = 0
    outcomes: list[dict[str, str]] = []
    proc_entries = [(str(index), str(path)) for index, (_rel, path) in enumerate(entries)]
    proc = (
        process_from_paths(proc_entries, TEMP_DIR)
        if generate_thumbs
        else process_hash_only_from_paths(proc_entries)
    )

    with get_session() as session:
        for index, (rel_path, path) in enumerate(entries):
            result = proc.get(str(index), (None, None, "no result", None, None, None))
            file_hash, thumb_path_str, _error = result[0], result[1], result[2]
            quick_hash, px_w, px_h = result[3], result[4], result[5]
            if not file_hash:
                outcomes.append({"rel_path": rel_path, "status": "error"})
                continue

            parsed = _media_rel_parts(rel_path)
            if parsed:
                date_group, subdir_chain, _filename = parsed
            else:
                stat = path.stat()
                date_group = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m")
                subdir_chain = []

            existing = session.exec(select(ImageAsset).where(ImageAsset.file_hash == file_hash)).first()
            if existing:
                existing_paths = [
                    _normalize_rel_path(p)
                    for p in (existing.media_path or [])
                    if isinstance(p, str) and p
                ]

                if rel_path not in existing_paths:
                    is_non_album = not _is_album_media_path(rel_path)
                    existing_non_album = [p for p in existing_paths if not _is_album_media_path(p)]
                    if is_non_album and existing_non_album:
                        hash_conflicts += 1
                        outcomes.append({
                            "rel_path": rel_path,
                            "status": "skipped",
                            "reason": "direct-duplicate",
                        })
                        continue
                    existing_paths.append(rel_path)
                    existing.media_path = existing_paths

                if subdir_chain:
                    public_ids, _album_paths = _ensure_album_chain(session, subdir_chain, date_group)
                    existing_album = existing.album or []
                    if public_ids and public_ids not in existing_album:
                        existing_album.append(public_ids)
                    existing.album = existing_album

                    if public_ids and existing.id is not None:
                        leaf_pid = public_ids[-1]
                        leaf_album = session.exec(select(Album).where(Album.public_id == leaf_pid)).first()
                        if leaf_album and leaf_album.id is not None:
                            exists_row = session.exec(
                                select(AlbumImage)
                                .where(AlbumImage.album_id == leaf_album.id)
                                .where(AlbumImage.image_id == existing.id)
                            ).first()
                            if not exists_row:
                                session.add(AlbumImage(album_id=leaf_album.id, image_id=existing.id))

                if thumb_path_str:
                    rel_thumb = to_project_relative(Path(thumb_path_str))
                    existing.thumbs = upsert_thumb(existing.thumbs, required_thumb_entry(rel_thumb))
                if not existing.quick_hash and quick_hash:
                    existing.quick_hash = quick_hash
                if not existing.width and px_w is not None:
                    existing.width = px_w
                if not existing.height and px_h is not None:
                    existing.height = px_h
                if not existing.file_size:
                    existing.file_size = path.stat().st_size
                if not existing.mime_type:
                    existing.mime_type = mime_from_name(path.name)
                if not existing.full_filename:
                    existing.full_filename = path.name
                if existing.tags is None:
                    existing.tags = []
                if not existing.category_id:
                    existing.category_id = DEFAULT_CATEGORY_ID
                if not existing.date_group:
                    existing.date_group = date_group
                session.add(existing)
                outcomes.append({"rel_path": rel_path, "status": "attached"})
                continue

            stat = path.stat()
            source_time_ms = int(min(stat.st_ctime, stat.st_mtime) * 1000)
            file_created_at = datetime.datetime.fromtimestamp(source_time_ms / 1000.0)
            if px_w is None or px_h is None:
                px_w, px_h = image_dimensions_from_file(path)
            new_thumb_list: list[dict] = []
            if thumb_path_str:
                rel_thumb = to_project_relative(Path(thumb_path_str))
                new_thumb_list = [required_thumb_entry(rel_thumb)]

            album_public_ids, _album_paths = (
                _ensure_album_chain(session, subdir_chain, date_group) if subdir_chain else ([], [])
            )

            asset = ImageAsset(
                original_path=rel_path,
                full_filename=path.name,
                file_hash=file_hash,
                quick_hash=quick_hash,
                thumbs=new_thumb_list,
                media_path=[rel_path],
                date_group=date_group,
                file_created_at=file_created_at,
                imported_at=datetime.datetime.now(),
                width=px_w,
                height=px_h,
                file_size=stat.st_size,
                mime_type=mime_from_name(path.name),
                category_id=DEFAULT_CATEGORY_ID,
                tags=[],
                album=[album_public_ids] if album_public_ids else [],
                collection=[],
            )
            session.add(asset)
            session.flush()
            if album_public_ids and asset.id is not None:
                leaf_pid = album_public_ids[-1]
                leaf_album = session.exec(select(Album).where(Album.public_id == leaf_pid)).first()
                if leaf_album and leaf_album.id is not None:
                    session.add(AlbumImage(album_id=leaf_album.id, image_id=asset.id))
            created += 1
            outcomes.append({"rel_path": rel_path, "status": "created"})

        session.commit()

    return created, hash_conflicts, outcomes


def _ingest_new_media_files_full(active_album_paths: set[str]) -> tuple[int, int]:
    _ = active_album_paths

    all_files = [path for path in list_image_files(MEDIA_DIR) if path.is_file()]
    all_entries = [(_normalize_rel_path(to_project_relative(path)), path) for path in all_files]

    with get_session() as session:
        known_paths = {
            _normalize_rel_path(path)
            for asset in session.exec(select(ImageAsset)).all()
            for path in (asset.media_path or [])
            if isinstance(path, str) and path
        }

    unknown = [(rel_path, path) for rel_path, path in all_entries if rel_path not in known_paths]
    if not unknown:
        return 0, 0

    new_ingested, hash_conflicts, _outcomes = ingest_media_entries(unknown)
    return new_ingested, hash_conflicts


def refresh_library(
    mode: str = "quick",
    repair_cache_image_ids: list[int] | None = None,
    repair_cache_trash_entry_ids: list[int] | None = None,
) -> dict[str, int | str]:
    init_db()
    mode = (mode or "quick").strip().lower()
    if mode not in {"quick", "full"}:
        mode = "quick"

    regenerated = 0
    new_ingested = 0
    hash_conflicts = 0
    non_album_deduped = 0
    cleaned_paths = 0

    pruned, non_album_deduped, cleaned_paths, active_album_paths = reconcile_library_paths()

    if mode == "full":
        new_ingested, hash_conflicts = _ingest_new_media_files_full(active_album_paths)

    with get_session() as session:
        live_hashes: set[str] = set()
        for asset in session.exec(select(ImageAsset)).all():
            media_path = _first_live_media_path(asset)
            if asset.file_hash and media_path:
                live_hashes.add(asset.file_hash)
        for file_hash in session.exec(select(TrashEntry.file_hash).where(TrashEntry.file_hash != None)).all():  # noqa: E711
            if isinstance(file_hash, str) and file_hash:
                live_hashes.add(file_hash)

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

    with get_session() as session:
        remaining = session.exec(select(ImageAsset).order_by(col(ImageAsset.id))).all()
        total_images = len(remaining)

        group_rep: dict[str, ImageAsset] = {}
        for asset in remaining:
            if asset.date_group and asset.date_group not in group_rep:
                group_rep[asset.date_group] = asset

        needs_thumb: list[ImageAsset] = []
        for asset in group_rep.values():
            media_path = _first_live_media_path(asset)
            if not media_path:
                continue
            if not has_required_thumb(asset.thumbs):
                needs_thumb.append(asset)

    if needs_thumb:
        entries = [
            (str(asset.id), str(_first_live_media_path(asset)))
            for asset in needs_thumb
            if _first_live_media_path(asset)
        ]
        proc = process_from_paths(entries, TEMP_DIR)
    else:
        proc = {}

    with get_session() as session:
        for asset in remaining:
            media_path = _first_live_media_path(asset)
            if not media_path:
                continue

            db_asset = session.exec(select(ImageAsset).where(ImageAsset.id == asset.id)).first()
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
                    db_asset.quick_hash = quick_hash_from_bytes(content)
            if not db_asset.width or not db_asset.height:
                if proc_w is not None and proc_h is not None:
                    db_asset.width, db_asset.height = proc_w, proc_h
                else:
                    db_asset.width, db_asset.height = image_dimensions_from_file(media_path)
            if not db_asset.file_size:
                db_asset.file_size = media_path.stat().st_size
            if not db_asset.mime_type:
                db_asset.mime_type = mime_from_name(media_path.name)
            if not db_asset.full_filename:
                db_asset.full_filename = media_path.name
            if db_asset.tags is None:
                db_asset.tags = []
            if not db_asset.category_id:
                db_asset.category_id = DEFAULT_CATEGORY_ID

            if db_asset.thumbs:
                live: list[dict] = []
                for thumb in db_asset.thumbs:
                    if not isinstance(thumb, dict):
                        continue
                    thumb_path = resolve_stored_path(thumb.get("path"))
                    if thumb_path and thumb_path.exists():
                        live.append(thumb)
                db_asset.thumbs = live

            if thumb_path_str:
                rel_thumb = to_project_relative(Path(thumb_path_str))
                db_asset.thumbs = upsert_thumb(db_asset.thumbs, required_thumb_entry(rel_thumb))
                regenerated += 1

            if not db_asset.file_hash and _file_hash:
                db_asset.file_hash = _file_hash

            session.add(db_asset)
        session.commit()

    targeted_cache_result = _repair_targeted_cache_entries(
        image_ids=repair_cache_image_ids,
        trash_entry_ids=repair_cache_trash_entry_ids,
    )

    rebuild_hash_index()
    recalculate_album_counts()

    return {
        "mode": mode,
        "pruned": pruned,
        "total_images": total_images,
        "cache_deleted": cache_deleted,
        "regenerated": regenerated,
        "new_ingested": new_ingested,
        "hash_conflicts": hash_conflicts,
        "non_album_deduped": non_album_deduped,
        "cleaned_paths": cleaned_paths,
        **targeted_cache_result,
    }
