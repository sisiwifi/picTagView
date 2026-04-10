import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import exists, not_
from sqlmodel import col, select

from app.core.config import CACHE_DIR, MEDIA_DIR, TEMP_DIR
from app.db.session import get_session, init_db
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.models.soft_delete import PathSoftDelete
from app.services.file_scanner import list_image_files
from app.services.parallel_processor import process_from_paths

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


def _ia_not_deleted_for_refresh():
    return not_(
        exists(
            select(PathSoftDelete.id)
            .where(PathSoftDelete.entity_type == "image")
            .where(PathSoftDelete.owner_id == ImageAsset.id)
        )
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


def _clear_soft_delete_for_path(session, entity_type: str, owner_id: Optional[int], target_path: str) -> None:
    normalized = _normalize_rel_path(target_path)
    rows = session.exec(
        select(PathSoftDelete)
        .where(PathSoftDelete.entity_type == entity_type)
        .where(PathSoftDelete.target_path == normalized)
    ).all()
    for row in rows:
        if owner_id is None or row.owner_id == owner_id:
            session.delete(row)


def _record_soft_delete(session, entity_type: str, owner_id: Optional[int], target_path: str) -> None:
    normalized = _normalize_rel_path(target_path)
    exists_row = session.exec(
        select(PathSoftDelete)
        .where(PathSoftDelete.entity_type == entity_type)
        .where(PathSoftDelete.owner_id == owner_id)
        .where(PathSoftDelete.target_path == normalized)
    ).first()
    if exists_row:
        return
    session.add(
        PathSoftDelete(
            entity_type=entity_type,
            owner_id=owner_id,
            target_path=normalized,
            deleted_at=datetime.datetime.now(),
            created_at=datetime.datetime.now(),
        )
    )


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
            if existing.id is not None:
                _clear_soft_delete_for_path(session, "album", existing.id, existing.path)
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

        for album in albums:
            album.photo_count = 0
            album.subtree_photo_count = 0

        # Clear existing album_image rows and rebuild
        session.exec(select(AlbumImage)).all()  # load
        from sqlalchemy import text as _text
        session.exec(_text("DELETE FROM album_image"))  # type: ignore[arg-type]

        cover_candidates: dict[str, ImageAsset] = {}

        all_assets = session.exec(select(ImageAsset).where(_ia_not_deleted_for_refresh())).all()
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

        for public_id, candidate in cover_candidates.items():
            if public_id not in album_map:
                continue
            album = album_map[public_id]
            thumb_path = ""
            for thumb in (candidate.thumbs or []):
                if isinstance(thumb, dict) and thumb.get("path"):
                    resolved = resolve_stored_path(thumb["path"])
                    if resolved and resolved.exists():
                        thumb_path = thumb["path"]
                        break
            album.cover = {
                "photo_id": candidate.id,
                "thumb_path": thumb_path,
                "filename": candidate.full_filename or "",
                "updated_at": datetime.datetime.now().isoformat(),
            }

        for album in albums:
            session.add(album)
        session.commit()


def _reconcile_assets_and_albums() -> tuple[int, int, int, set[str]]:
    pruned = 0
    non_album_deduped = 0
    cleaned_paths = 0
    active_album_paths: set[str] = set()

    with get_session() as session:
        deleted_map: dict[int, set[str]] = {}
        for row in session.exec(select(PathSoftDelete).where(PathSoftDelete.entity_type == "image")).all():
            if row.owner_id is None or not row.target_path:
                continue
            deleted_map.setdefault(row.owner_id, set()).add(_normalize_rel_path(row.target_path))

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

            visible_candidates = [
                path for path in unique_live
                if path not in deleted_map.get(asset.id or -1, set())
            ]

            non_album_paths = [path for path in visible_candidates if not _is_album_media_path(path)]
            if len(non_album_paths) > 1:
                keep_non_album = sorted(non_album_paths)[0]
                reduced: list[str] = []
                for rel_path in unique_live:
                    if rel_path in non_album_paths and rel_path != keep_non_album:
                        non_album_deduped += 1
                        if asset.id is not None:
                            _record_soft_delete(session, "image", asset.id, rel_path)
                        continue
                    reduced.append(rel_path)
                unique_live = reduced
                visible_candidates = [
                    path for path in unique_live
                    if path not in deleted_map.get(asset.id or -1, set())
                ]

            album_chains: list[list[str]] = []
            date_candidates: list[str] = []
            for rel_path in visible_candidates:
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

                if asset.id is not None:
                    _clear_soft_delete_for_path(session, "image", asset.id, rel_path)

            asset.media_path = unique_live
            asset.album = album_chains
            if date_candidates:
                asset.date_group = sorted(date_candidates)[0]
            session.add(asset)

        session.commit()

    with get_session() as session:
        all_albums = session.exec(select(Album)).all()
        for album in all_albums:
            if album.path in active_album_paths:
                if album.id is not None:
                    _clear_soft_delete_for_path(session, "album", album.id, album.path)
            else:
                _record_soft_delete(session, "album", album.id, album.path)
        session.commit()

    return pruned, non_album_deduped, cleaned_paths, active_album_paths


def _ingest_new_media_files_full(active_album_paths: set[str]) -> tuple[int, int]:
    _ = active_album_paths
    new_ingested = 0
    hash_conflicts = 0

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
        return new_ingested, hash_conflicts

    proc = process_from_paths([(str(index), str(path)) for index, (_rel, path) in enumerate(unknown)], TEMP_DIR)

    with get_session() as session:
        for index, (rel_path, path) in enumerate(unknown):
            result = proc.get(str(index), (None, None, "no result", None, None, None))
            file_hash, thumb_path_str, _error = result[0], result[1], result[2]
            quick_hash, px_w, px_h = result[3], result[4], result[5]
            if not file_hash:
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
                        if existing.id is not None:
                            _record_soft_delete(session, "image", existing.id, rel_path)
                    else:
                        existing_paths.append(rel_path)
                        existing.media_path = existing_paths

                if subdir_chain:
                    public_ids, album_paths = _ensure_album_chain(session, subdir_chain, date_group)
                    existing_album = existing.album or []
                    if public_ids and public_ids not in existing_album:
                        existing_album.append(public_ids)
                    existing.album = existing_album
                    for album_path in album_paths:
                        active_album_paths.add(album_path)
                    # Write album_image mapping for the leaf album
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
                if existing.category is None:
                    existing.category = ""
                if not existing.date_group:
                    existing.date_group = date_group
                session.add(existing)
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

            album_public_ids, album_paths = (
                _ensure_album_chain(session, subdir_chain, date_group) if subdir_chain else ([], [])
            )
            for album_path in album_paths:
                active_album_paths.add(album_path)

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
                category="",
                tags=[],
                album=[album_public_ids] if album_public_ids else [],
                collection=[],
            )
            session.add(asset)
            session.flush()
            # Write album_image mapping for the leaf album
            if album_public_ids and asset.id is not None:
                leaf_pid = album_public_ids[-1]
                leaf_album = session.exec(select(Album).where(Album.public_id == leaf_pid)).first()
                if leaf_album and leaf_album.id is not None:
                    session.add(AlbumImage(album_id=leaf_album.id, image_id=asset.id))
            new_ingested += 1

        session.commit()

    return new_ingested, hash_conflicts


def refresh_library(mode: str = "quick") -> dict[str, int | str]:
    init_db()
    mode = (mode or "quick").strip().lower()
    if mode not in {"quick", "full"}:
        mode = "quick"

    regenerated = 0
    new_ingested = 0
    hash_conflicts = 0
    non_album_deduped = 0
    cleaned_paths = 0

    pruned, non_album_deduped, cleaned_paths, active_album_paths = _reconcile_assets_and_albums()

    if mode == "full":
        new_ingested, hash_conflicts = _ingest_new_media_files_full(active_album_paths)

    with get_session() as session:
        live_hashes: set[str] = set()
        for asset in session.exec(select(ImageAsset)).all():
            media_path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if asset.file_hash and media_path and media_path.exists():
                live_hashes.add(asset.file_hash)

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
            media_path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if not media_path or not media_path.exists():
                continue
            if not has_required_thumb(asset.thumbs):
                needs_thumb.append(asset)

    if needs_thumb:
        entries = [
            (str(asset.id), str(resolve_stored_path(asset.media_path[0] if asset.media_path else None)))
            for asset in needs_thumb
            if resolve_stored_path(asset.media_path[0] if asset.media_path else None)
        ]
        proc = process_from_paths(entries, TEMP_DIR)
    else:
        proc = {}

    with get_session() as session:
        for asset in remaining:
            media_path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if not media_path or not media_path.exists():
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
            if db_asset.category is None:
                db_asset.category = ""

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
    }
