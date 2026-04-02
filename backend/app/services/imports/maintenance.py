import datetime
from pathlib import Path

from sqlalchemy import exists, not_
from sqlmodel import col, select

from app.core.config import CACHE_DIR, TEMP_DIR
from app.db.session import get_session, init_db
from app.models.album import Album
from app.models.image_asset import ImageAsset
from app.models.soft_delete import PathSoftDelete
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


def recalculate_album_counts() -> None:
    with get_session() as session:
        albums = session.exec(select(Album).order_by(col(Album.id))).all()
        album_map = {album.public_id: album for album in albums}

        for album in albums:
            album.photo_count = 0
            album.subtree_photo_count = 0

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


def refresh_library() -> dict[str, int]:
    init_db()
    pruned = 0
    regenerated = 0

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
        all_assets = session.exec(select(ImageAsset)).all()
        for asset in all_assets:
            media_path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if asset.media_path and not (media_path and media_path.exists()):
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
        session.commit()

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
