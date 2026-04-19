from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from sqlmodel import col, select

from app.api.common import normalize_stored_path, resolve_stored_path
from app.api.schemas import TrashActionResult, TrashItem, TrashListResponse, TrashTargetRef
from app.core.config import CACHE_DIR, MEDIA_DIR, TEMP_DIR, TRASH_DIR
from app.db.session import get_session
from app.models.album import Album
from app.models.image_asset import ImageAsset
from app.models.trash_entry import TrashEntry
from app.services.file_scanner import iter_image_files, list_image_files
from app.services.imports.hash_index import rebuild_hash_index
from app.services.imports.helpers import mime_from_name, required_thumb_entry, to_project_relative, unique_dest, unique_dir_dest, upsert_thumb
from app.services.imports.maintenance import ingest_media_entries, recalculate_album_counts, reconcile_library_paths
from app.services.parallel_processor import process_from_paths


def _legacy_trash_entry_root(entry_key: str) -> Path:
    return TRASH_DIR / "entries" / entry_key


def _legacy_trash_payload_root(entry_key: str) -> Path:
    return _legacy_trash_entry_root(entry_key) / "payload"


def _flat_trash_payload_path(entry_key: str, payload_name: str) -> Path:
    return TRASH_DIR / f"{entry_key}__{payload_name}"


def _cleanup_empty_parent_dirs(start_dir: Path, stop_dir: Path) -> None:
    current = start_dir
    stop = stop_dir.resolve()
    while True:
        try:
            resolved = current.resolve()
        except Exception:
            break
        if resolved == stop or stop not in resolved.parents:
            break
        if not current.exists() or any(current.iterdir()):
            break
        current.rmdir()
        current = current.parent


def _stored_path_exists(stored_path: str | None) -> bool:
    resolved = resolve_stored_path(stored_path)
    return bool(resolved and resolved.exists())


def _path_relative_to(path: Path, root: Path) -> Path | None:
    try:
        return path.resolve().relative_to(root.resolve())
    except Exception:
        return None


def _find_existing_trash_payload(entry: TrashEntry) -> Path | None:
    stored_path = resolve_stored_path(entry.trash_path)
    if stored_path and stored_path.exists():
        return stored_path

    legacy_root = _legacy_trash_payload_root(entry.entry_key)
    if legacy_root.exists() and legacy_root.is_dir():
        children = sorted(legacy_root.iterdir(), key=lambda path: path.name.casefold())
        if len(children) == 1:
            return children[0]

    flat_matches = sorted(TRASH_DIR.glob(f"{entry.entry_key}__*"), key=lambda path: path.name.casefold())
    if flat_matches:
        return flat_matches[0]
    return None


def _migrate_legacy_trash_payload(entry: TrashEntry, payload_path: Path) -> tuple[Path, bool]:
    legacy_root = _legacy_trash_payload_root(entry.entry_key)
    if _path_relative_to(payload_path, legacy_root) is None:
        return payload_path, False

    preview_rel: Path | None = None
    preview_path = resolve_stored_path(entry.preview_path)
    if preview_path is not None:
        if payload_path.is_dir():
            preview_rel = _path_relative_to(preview_path, payload_path)
        elif preview_path == payload_path:
            preview_rel = Path()

    target_path = _flat_trash_payload_path(entry.entry_key, payload_path.name)
    if target_path.exists():
        if payload_path.is_dir():
            shutil.rmtree(payload_path, ignore_errors=True)
        else:
            try:
                payload_path.unlink()
            except Exception:
                pass
    else:
        shutil.move(str(payload_path), str(target_path))

    entry.trash_path = to_project_relative(target_path)
    if preview_rel is not None:
        entry.preview_path = to_project_relative(target_path if not preview_rel.parts else target_path / preview_rel)

    _cleanup_empty_parent_dirs(legacy_root, TRASH_DIR)
    return target_path, True


def _pick_trash_preview_source(entry: TrashEntry, payload_path: Path) -> Path | None:
    if entry.entity_type == "image":
        return payload_path if payload_path.exists() and payload_path.is_file() else None

    if not payload_path.exists() or not payload_path.is_dir():
        return None

    preferred = resolve_stored_path(entry.preview_path)
    if preferred and preferred.exists() and preferred.is_file() and _path_relative_to(preferred, payload_path) is not None:
        return preferred

    image_files = sorted(list_image_files(payload_path), key=lambda path: path.as_posix().casefold())
    if image_files:
        return image_files[0]
    return None


def _album_payload_snapshot(entry: TrashEntry, payload_path: Path) -> tuple[int, Path | None]:
    preferred_preview = resolve_stored_path(entry.preview_path)
    preferred_rel = _path_relative_to(preferred_preview, payload_path) if preferred_preview else None
    preferred_exists = False

    image_count = 0
    fallback_preview: Path | None = None
    fallback_key: str | None = None
    for image_path in iter_image_files(payload_path):
        image_count += 1
        rel_path = _path_relative_to(image_path, payload_path)
        if preferred_rel is not None and rel_path == preferred_rel:
            preferred_exists = True
        current_key = image_path.as_posix().casefold()
        if fallback_preview is None or (fallback_key is not None and current_key < fallback_key):
            fallback_preview = image_path
            fallback_key = current_key

    if preferred_exists and preferred_preview and preferred_preview.exists():
        return image_count, preferred_preview
    return image_count, fallback_preview


def _reconcile_trash_entries() -> None:
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    changed = False
    with get_session() as session:
        entries = session.exec(select(TrashEntry).order_by(col(TrashEntry.id))).all()
        thumb_jobs: list[tuple[str, str]] = []
        thumb_entry_ids: dict[str, int] = {}

        for entry in entries:
            payload_path = _find_existing_trash_payload(entry)
            if not payload_path or not payload_path.exists():
                session.delete(entry)
                changed = True
                continue

            payload_path, migrated = _migrate_legacy_trash_payload(entry, payload_path)
            changed = changed or migrated

            normalized_payload_path = to_project_relative(payload_path)
            if entry.trash_path != normalized_payload_path:
                entry.trash_path = normalized_payload_path
                changed = True

            preview_source: Path | None = None
            if entry.entity_type == "album" and payload_path.is_dir():
                photo_count, preview_source = _album_payload_snapshot(entry, payload_path)
                if entry.photo_count != photo_count:
                    entry.photo_count = photo_count
                    changed = True
            else:
                preview_source = _pick_trash_preview_source(entry, payload_path)

            desired_preview_path = to_project_relative(preview_source) if preview_source else None
            preview_changed = entry.preview_path != desired_preview_path
            if preview_changed:
                entry.preview_path = desired_preview_path
                changed = True

            if not preview_source:
                if entry.preview_thumb_path is not None:
                    entry.preview_thumb_path = None
                    changed = True
                if entry.preview_cache_path is not None:
                    entry.preview_cache_path = None
                    changed = True
                if entry.entity_type == "album":
                    if entry.file_hash is not None:
                        entry.file_hash = None
                        changed = True
                    if entry.width is not None:
                        entry.width = None
                        changed = True
                    if entry.height is not None:
                        entry.height = None
                        changed = True
                continue

            needs_thumb_repair = preview_changed or not _stored_path_exists(entry.preview_thumb_path)
            needs_metadata_repair = not entry.file_hash or not entry.width or not entry.height
            if needs_thumb_repair or needs_metadata_repair:
                job_key = str(entry.id or entry.entry_key)
                thumb_jobs.append((job_key, str(preview_source)))
                if entry.id is not None:
                    thumb_entry_ids[job_key] = entry.id

            cache_path = _cache_path_for_hash(entry.file_hash)
            if entry.preview_cache_path != cache_path:
                entry.preview_cache_path = cache_path
                changed = True

            if entry.entity_type == "image":
                file_size = preview_source.stat().st_size
                if entry.file_size != file_size:
                    entry.file_size = file_size
                    changed = True
                mime_type = mime_from_name(preview_source.name)
                if entry.mime_type != mime_type:
                    entry.mime_type = mime_type
                    changed = True

            session.add(entry)

        if thumb_jobs:
            thumb_results = process_from_paths(thumb_jobs, TEMP_DIR)
            for job_key, entry_id in thumb_entry_ids.items():
                result = thumb_results.get(job_key)
                if not result:
                    continue
                file_hash, thumb_path_str, error, _quick_hash, width, height = result
                if error:
                    continue
                entry = session.get(TrashEntry, entry_id)
                if not entry:
                    continue

                next_thumb_path = entry.preview_thumb_path
                if thumb_path_str:
                    next_thumb_path = to_project_relative(Path(thumb_path_str))

                next_file_hash = file_hash or entry.file_hash
                next_width = width or entry.width
                next_height = height or entry.height
                next_cache_path = _cache_path_for_hash(next_file_hash)

                if entry.preview_thumb_path != next_thumb_path:
                    entry.preview_thumb_path = next_thumb_path
                    changed = True
                if entry.file_hash != next_file_hash:
                    entry.file_hash = next_file_hash
                    changed = True
                if entry.width != next_width:
                    entry.width = next_width
                    changed = True
                if entry.height != next_height:
                    entry.height = next_height
                    changed = True
                if entry.preview_cache_path != next_cache_path:
                    entry.preview_cache_path = next_cache_path
                    changed = True

                session.add(entry)

        if changed:
            session.commit()

    if changed:
        _cleanup_unused_preview_files()


def _project_preview_url(project_path: str | None) -> str | None:
    if not project_path:
        return None
    resolved = resolve_stored_path(project_path)
    if not resolved or not resolved.exists():
        return None
    try:
        resolved.relative_to(TEMP_DIR)
        return f"/thumbnails/{resolved.name}"
    except ValueError:
        pass
    try:
        resolved.relative_to(CACHE_DIR)
        return f"/cache/{resolved.name}"
    except ValueError:
        pass
    try:
        relative = resolved.relative_to(TRASH_DIR).as_posix()
        return f"/trash-media/{relative}"
    except ValueError:
        return None


def _asset_thumb_path(asset: ImageAsset) -> str | None:
    for entry in asset.thumbs or []:
        if not isinstance(entry, dict):
            continue
        stored = entry.get("path")
        if not isinstance(stored, str) or not stored:
            continue
        resolved = resolve_stored_path(stored)
        if resolved and resolved.exists():
            return stored
    return None


def _cache_path_for_hash(file_hash: str | None) -> str | None:
    if not file_hash:
        return None
    cache_file = CACHE_DIR / f"{file_hash}_cache.webp"
    if not cache_file.exists():
        return None
    return to_project_relative(cache_file)


def _normalize_album_path(album_path: str) -> str:
    return normalize_stored_path(album_path).strip("/")


def _album_preview_data(session, album: Album, moved_root: Path) -> tuple[str | None, str | None, str | None, int | None, int | None, str | None]:
    if not album.cover or not isinstance(album.cover, dict):
        return None, None, None, None, None, None

    thumb_path = album.cover.get("thumb_path") if isinstance(album.cover.get("thumb_path"), str) else None
    cover_photo_id = album.cover.get("photo_id")
    if not isinstance(cover_photo_id, int):
        return None, thumb_path, None, None, None, None

    asset = session.get(ImageAsset, cover_photo_id)
    if not asset:
        return None, thumb_path, None, None, None, None

    album_prefix = f"media/{_normalize_album_path(album.path)}/"
    preview_path = None
    for stored in asset.media_path or []:
        if not isinstance(stored, str) or not stored:
            continue
        normalized = normalize_stored_path(stored)
        if not normalized.startswith(album_prefix):
            continue
        suffix = normalized[len(album_prefix):]
        preview_path = to_project_relative(moved_root / suffix)
        break

    return (
        preview_path,
        thumb_path,
        _cache_path_for_hash(asset.file_hash),
        asset.width,
        asset.height,
        asset.file_hash,
    )


def _refresh_library_indexes() -> None:
    reconcile_library_paths()
    rebuild_hash_index()
    recalculate_album_counts()


def _first_live_asset_path(asset: ImageAsset) -> Path | None:
    for stored_path in asset.media_path or []:
        if not isinstance(stored_path, str) or not stored_path:
            continue
        resolved = resolve_stored_path(stored_path)
        if resolved and resolved.exists():
            return resolved
    return None


def _asset_has_live_thumb(asset: ImageAsset) -> bool:
    for thumb_entry in asset.thumbs or []:
        if not isinstance(thumb_entry, dict):
            continue
        thumb_path = resolve_stored_path(thumb_entry.get("path"))
        if thumb_path and thumb_path.exists():
            return True
    return False


def _album_paths_from_restored_entries(entries: list[tuple[str, Path]]) -> set[str]:
    album_paths: set[str] = set()
    for rel_path, _path in entries:
        parts = [part for part in normalize_stored_path(rel_path).split("/") if part]
        if len(parts) < 4 or parts[0] != "media":
            continue
        date_group = parts[1]
        subdirs = parts[2:-1]
        for depth in range(1, len(subdirs) + 1):
            album_paths.add("/".join([date_group, *subdirs[:depth]]))
    return album_paths


def _ensure_album_cover_thumbs(album_paths: set[str]) -> None:
    if not album_paths:
        return

    with get_session() as session:
        albums = session.exec(
            select(Album)
            .where(Album.path.in_(sorted(album_paths)))  # type: ignore[arg-type]
            .order_by(col(Album.path))
        ).all()

        thumb_jobs: list[tuple[str, str]] = []
        job_asset_ids: dict[str, int] = {}

        for album in albums:
            if not isinstance(album.cover, dict):
                continue
            cover_photo_id = album.cover.get("photo_id")
            if not isinstance(cover_photo_id, int):
                continue
            asset = session.get(ImageAsset, cover_photo_id)
            if not asset or _asset_has_live_thumb(asset):
                continue
            media_path = _first_live_asset_path(asset)
            if not media_path:
                continue
            job_key = str(asset.id)
            if job_key in job_asset_ids:
                continue
            thumb_jobs.append((job_key, str(media_path)))
            job_asset_ids[job_key] = cover_photo_id

        if not thumb_jobs:
            return

        thumb_results = process_from_paths(thumb_jobs, TEMP_DIR)
        changed = False

        for job_key, asset_id in job_asset_ids.items():
            result = thumb_results.get(job_key)
            if not result:
                continue
            file_hash, thumb_path_str, error, _quick_hash, width, height = result
            if error or not thumb_path_str:
                continue

            asset = session.get(ImageAsset, asset_id)
            if not asset:
                continue

            rel_thumb = to_project_relative(Path(thumb_path_str))
            next_thumbs = upsert_thumb(asset.thumbs, required_thumb_entry(rel_thumb))
            if asset.thumbs != next_thumbs:
                asset.thumbs = next_thumbs
                changed = True
            if file_hash and not asset.file_hash:
                asset.file_hash = file_hash
                changed = True
            if width is not None and not asset.width:
                asset.width = width
                changed = True
            if height is not None and not asset.height:
                asset.height = height
                changed = True
            session.add(asset)

        if changed:
            session.commit()

    recalculate_album_counts()


def _cleanup_unused_preview_files() -> None:
    active_hashes: set[str] = set()
    with get_session() as session:
        for file_hash in session.exec(select(ImageAsset.file_hash)).all():
            if isinstance(file_hash, str) and file_hash:
                active_hashes.add(file_hash)
        for file_hash in session.exec(select(TrashEntry.file_hash).where(TrashEntry.file_hash != None)).all():  # noqa: E711
            if isinstance(file_hash, str) and file_hash:
                active_hashes.add(file_hash)

    for cache_file in CACHE_DIR.glob("*_cache.webp"):
        file_hash = cache_file.stem[:-6]
        if file_hash in active_hashes:
            continue
        try:
            cache_file.unlink()
        except Exception:
            pass

    for thumb_file in TEMP_DIR.glob("*.webp"):
        file_hash = thumb_file.stem
        if file_hash in active_hashes:
            continue
        try:
            thumb_file.unlink()
        except Exception:
            pass


def list_trash_items() -> TrashListResponse:
    _reconcile_trash_entries()
    with get_session() as session:
        entries = session.exec(select(TrashEntry).order_by(col(TrashEntry.created_at).desc())).all()

    items = [
        TrashItem(
            id=entry.id or 0,
            entry_key=entry.entry_key,
            type=entry.entity_type,
            name=entry.display_name,
            thumb_url=_project_preview_url(entry.preview_thumb_path) or "",
            cache_thumb_url=_project_preview_url(entry.preview_cache_path),
            trash_media_url=_project_preview_url(entry.preview_path),
            width=entry.width,
            height=entry.height,
            sort_ts=int(entry.created_at.timestamp()) if entry.created_at else None,
            tags=entry.tags or [],
            file_size=entry.file_size,
            imported_at=entry.imported_at,
            file_created_at=entry.file_created_at,
            photo_count=entry.photo_count,
            created_at=entry.source_created_at,
            original_path=entry.original_path,
        )
        for entry in entries
        if entry.id is not None
    ]
    return TrashListResponse(items=items)


def _move_image_to_trash(image_id: int, media_rel_path: str) -> None:
    normalized_path = normalize_stored_path(media_rel_path)
    with get_session() as session:
        asset = session.get(ImageAsset, image_id)
        if not asset:
            raise ValueError(f"Image not found: {image_id}")

        normalized_media_paths = {
            normalize_stored_path(path)
            for path in (asset.media_path or [])
            if isinstance(path, str) and path
        }
        if normalized_path not in normalized_media_paths:
            raise ValueError(f"Image path not found on asset: {normalized_path}")

        src_path = resolve_stored_path(normalized_path)
        if not src_path or not src_path.exists():
            raise ValueError(f"Image file not found on disk: {normalized_path}")

        entry_key = uuid.uuid4().hex
        TRASH_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = _flat_trash_payload_path(entry_key, src_path.name)
        file_stat = src_path.stat()
        shutil.move(str(src_path), str(dest_path))

        parsed_parts = [part for part in normalized_path.split("/") if part]
        original_date_group = parsed_parts[1] if len(parsed_parts) > 1 else asset.date_group
        session.add(
            TrashEntry(
                entry_key=entry_key,
                entity_type="image",
                display_name=asset.full_filename or src_path.name,
                original_path=normalized_path,
                original_date_group=original_date_group,
                trash_path=to_project_relative(dest_path),
                preview_path=to_project_relative(dest_path),
                preview_thumb_path=_asset_thumb_path(asset),
                preview_cache_path=_cache_path_for_hash(asset.file_hash),
                file_hash=asset.file_hash,
                width=asset.width,
                height=asset.height,
                file_size=asset.file_size or file_stat.st_size,
                mime_type=asset.mime_type,
                imported_at=asset.imported_at,
                file_created_at=asset.file_created_at,
                tags=list(asset.tags or []),
                metadata_json={"image_id": image_id},
            )
        )
        session.commit()

    _cleanup_empty_parent_dirs(src_path.parent, MEDIA_DIR)


def _move_album_to_trash(album_path: str) -> None:
    normalized_album_path = _normalize_album_path(album_path)
    with get_session() as session:
        album = session.exec(select(Album).where(Album.path == normalized_album_path)).first()
        if not album:
            raise ValueError(f"Album not found: {normalized_album_path}")

        src_dir = (MEDIA_DIR / normalized_album_path).resolve()
        media_root = MEDIA_DIR.resolve()
        try:
            src_dir.relative_to(media_root)
        except ValueError as exc:
            raise ValueError(f"Album path is invalid: {normalized_album_path}") from exc
        if not src_dir.exists() or not src_dir.is_dir():
            raise ValueError(f"Album directory not found: {normalized_album_path}")

        entry_key = uuid.uuid4().hex
        TRASH_DIR.mkdir(parents=True, exist_ok=True)
        dest_dir = _flat_trash_payload_path(entry_key, src_dir.name)

        shutil.move(str(src_dir), str(dest_dir))

        preview_path, thumb_path, cache_path, width, height, file_hash = _album_preview_data(session, album, dest_dir)
        session.add(
            TrashEntry(
                entry_key=entry_key,
                entity_type="album",
                display_name=album.title,
                original_path=normalized_album_path,
                original_date_group=album.date_group,
                trash_path=to_project_relative(dest_dir),
                preview_path=preview_path,
                preview_thumb_path=thumb_path,
                preview_cache_path=cache_path,
                file_hash=file_hash,
                width=width,
                height=height,
                photo_count=album.subtree_photo_count or album.photo_count,
                source_created_at=album.created_at,
                metadata_json={"album_public_id": album.public_id},
            )
        )
        session.commit()

    _cleanup_empty_parent_dirs(src_dir.parent, MEDIA_DIR)


def move_targets_to_trash(items: list[TrashTargetRef]) -> TrashActionResult:
    result = TrashActionResult()
    changed = False
    for item in items:
        try:
            if item.type == "image":
                if item.image_id is None or not item.media_rel_path:
                    raise ValueError("Image trash target requires image_id and media_rel_path")
                _move_image_to_trash(item.image_id, item.media_rel_path)
            elif item.type == "album":
                if not item.album_path:
                    raise ValueError("Album trash target requires album_path")
                _move_album_to_trash(item.album_path)
            else:
                raise ValueError(f"Unsupported trash target type: {item.type}")
            result.moved += 1
            changed = True
        except Exception as exc:
            result.errors.append(str(exc))

    if changed:
        _refresh_library_indexes()
        _cleanup_unused_preview_files()
    return result


def _restore_image_entry(entry: TrashEntry) -> tuple[list[tuple[str, Path]], list[Path]]:
    src_path = resolve_stored_path(entry.trash_path)
    if not src_path or not src_path.exists() or not src_path.is_file():
        raise ValueError(f"Trash image payload not found: {entry.trash_path}")

    parts = [part for part in normalize_stored_path(entry.original_path).split("/") if part]
    if len(parts) < 3 or parts[0] != "media":
        raise ValueError(f"Invalid original image path: {entry.original_path}")

    dest_dir = MEDIA_DIR / parts[1]
    for segment in parts[2:-1]:
        dest_dir = dest_dir / segment
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = unique_dest(dest_dir, parts[-1])
    shutil.move(str(src_path), str(dest_path))
    rel_path = normalize_stored_path(to_project_relative(dest_path))
    return [(rel_path, dest_path)], [dest_path]


def _restore_album_entry(entry: TrashEntry) -> tuple[list[tuple[str, Path]], list[Path]]:
    src_dir = resolve_stored_path(entry.trash_path)
    if not src_dir or not src_dir.exists() or not src_dir.is_dir():
        raise ValueError(f"Trash album payload not found: {entry.trash_path}")

    parts = [part for part in _normalize_album_path(entry.original_path).split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"Invalid original album path: {entry.original_path}")

    dest_parent = MEDIA_DIR / parts[0]
    for segment in parts[1:-1]:
        dest_parent = dest_parent / segment
    dest_parent.mkdir(parents=True, exist_ok=True)
    dest_dir = unique_dir_dest(dest_parent, parts[-1])
    shutil.move(str(src_dir), str(dest_dir))

    restored_files = [
        (normalize_stored_path(to_project_relative(path)), path)
        for path in list_image_files(dest_dir)
        if path.is_file()
    ]
    return restored_files, [dest_dir]


def _delete_trash_entry_payload(entry: TrashEntry) -> None:
    payload_path = resolve_stored_path(entry.trash_path)
    if payload_path and payload_path.exists():
        if payload_path.is_dir():
            shutil.rmtree(payload_path, ignore_errors=True)
        else:
            try:
                payload_path.unlink()
            except Exception:
                pass
        _cleanup_empty_parent_dirs(payload_path.parent, TRASH_DIR)

    legacy_entry_root = _legacy_trash_entry_root(entry.entry_key)
    if legacy_entry_root.exists():
        shutil.rmtree(legacy_entry_root, ignore_errors=True)

    legacy_payload_root = _legacy_trash_payload_root(entry.entry_key)
    if legacy_payload_root.exists():
        shutil.rmtree(legacy_payload_root, ignore_errors=True)

    legacy_entries_root = TRASH_DIR / "entries"
    if legacy_entries_root.exists():
        _cleanup_empty_parent_dirs(legacy_entries_root, TRASH_DIR)


def _cleanup_skipped_restore_conflicts(outcomes: list[dict[str, str]]) -> None:
    for outcome in outcomes:
        if outcome.get("status") != "skipped":
            continue
        conflict_path = resolve_stored_path(outcome.get("rel_path"))
        if conflict_path and conflict_path.exists():
            try:
                conflict_path.unlink()
            except Exception:
                pass
            _cleanup_empty_parent_dirs(conflict_path.parent, MEDIA_DIR)


def restore_trash_entries(entry_ids: list[int]) -> TrashActionResult:
    result = TrashActionResult()
    changed = False
    affected_album_paths: set[str] = set()

    with get_session() as session:
        entries = session.exec(
            select(TrashEntry)
            .where(TrashEntry.id.in_(entry_ids))  # type: ignore[arg-type]
            .order_by(col(TrashEntry.id))
        ).all()

    image_entries: list[tuple[str, Path]] = []
    album_entries: list[tuple[str, Path]] = []
    image_trash_entries: list[TrashEntry] = []
    album_trash_entries: list[TrashEntry] = []
    restored_trash_entries: list[TrashEntry] = []

    for entry in entries:
        try:
            if entry.entity_type == "image":
                image_entries.extend(_restore_image_entry(entry)[0])
                image_trash_entries.append(entry)
            elif entry.entity_type == "album":
                album_entries.extend(_restore_album_entry(entry)[0])
                album_trash_entries.append(entry)
            else:
                raise ValueError(f"Unsupported trash entry type: {entry.entity_type}")
        except Exception as exc:
            result.errors.append(str(exc))

    if image_entries:
        try:
            _created, _hash_conflicts, outcomes = ingest_media_entries(image_entries, generate_thumbs=True)
            _cleanup_skipped_restore_conflicts(outcomes)
            restored_trash_entries.extend(image_trash_entries)
        except Exception as exc:
            result.errors.append(str(exc))

    if album_entries:
        try:
            _created, _hash_conflicts, outcomes = ingest_media_entries(album_entries, generate_thumbs=False)
            _cleanup_skipped_restore_conflicts(outcomes)
            affected_album_paths.update(_album_paths_from_restored_entries(album_entries))
            restored_trash_entries.extend(album_trash_entries)
        except Exception as exc:
            result.errors.append(str(exc))

    if restored_trash_entries:
        with get_session() as session:
            for entry in restored_trash_entries:
                db_entry = session.get(TrashEntry, entry.id)
                if db_entry:
                    session.delete(db_entry)
            session.commit()

        for entry in restored_trash_entries:
            _delete_trash_entry_payload(entry)

        result.restored = len(restored_trash_entries)
        changed = True

    if changed:
        recalculate_album_counts()
        _ensure_album_cover_thumbs(affected_album_paths)
        rebuild_hash_index()
        _cleanup_unused_preview_files()
    return result


def hard_delete_trash_entries(entry_ids: list[int]) -> TrashActionResult:
    result = TrashActionResult()
    changed = False
    with get_session() as session:
        entries = session.exec(
            select(TrashEntry)
            .where(TrashEntry.id.in_(entry_ids))  # type: ignore[arg-type]
            .order_by(col(TrashEntry.id))
        ).all()

        for entry in entries:
            _delete_trash_entry_payload(entry)
            session.delete(entry)
            result.deleted += 1
            changed = True

        session.commit()

    if changed:
        _cleanup_unused_preview_files()
    return result


def clear_trash() -> TrashActionResult:
    with get_session() as session:
        entry_ids = [entry_id for entry_id in session.exec(select(TrashEntry.id)).all() if isinstance(entry_id, int)]
    return hard_delete_trash_entries(entry_ids)