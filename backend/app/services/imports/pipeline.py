import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlmodel import col, select

from app.core.config import TEMP_DIR
from app.db.session import get_session, init_db
from app.models.album import Album
from app.models.album_image import AlbumImage
from app.models.image_asset import ImageAsset
from app.services.category_service import DEFAULT_CATEGORY_ID
from app.services.cover_service import build_asset_cover_payload, cover_is_manual, extract_cover_photo_id
from app.services.parallel_processor import (
    IMPORT_BATCH_SIZE,
    process_from_bytes,
    process_hash_only_from_bytes,
)
from app.services.tag_match_service import (
    TagMatchContext,
    apply_usage_count_deltas,
    collect_usage_count_deltas,
    load_tag_match_context,
    match_filename_tags,
    merge_matched_tag_ids,
    now_tag_timestamp,
    sanitize_tag_ids,
    touch_tag_last_used,
)

from .hash_index import (
    add_to_hash_index,
    load_hash_index,
    lookup_hash_index,
    lookup_quick_hash,
    save_hash_index,
)
from .helpers import (
    date_group_from_ts,
    has_required_thumb,
    image_dimensions_from_bytes,
    is_image_ext,
    mime_from_name,
    min_source_ts_ms,
    parse_relative_path,
    quick_hash_from_bytes,
    required_thumb_entry,
    resolve_stored_path,
    save_to_media,
    to_project_relative,
    upsert_thumb,
)

_album_chain_cache: dict[str, list[str]] = {}


def normalize_import_category_id(category_id: Optional[int]) -> int:
    if isinstance(category_id, int) and category_id > 0:
        return category_id
    return DEFAULT_CATEGORY_ID


def apply_import_category_to_image_asset(asset: ImageAsset, category_id: Optional[int]) -> bool:
    target_category_id = normalize_import_category_id(category_id)
    current_category_id = normalize_import_category_id(asset.category_id)
    if current_category_id != DEFAULT_CATEGORY_ID:
        return False
    if current_category_id == target_category_id:
        return False
    asset.category_id = target_category_id
    return True


def apply_import_filename_tags(
    asset: ImageAsset,
    filename: str,
    tag_match_context: TagMatchContext,
    *,
    usage_deltas: dict[int, int],
    touched_tag_ids: set[int],
) -> bool:
    before_tag_ids = sanitize_tag_ids(asset.tags or [])
    normalized_only = asset.tags != before_tag_ids
    if normalized_only:
        asset.tags = before_tag_ids

    if not tag_match_context.enabled or not tag_match_context.tags_by_name:
        if asset.tags is None:
            asset.tags = []
            return True
        return normalized_only

    _tokens, matched_tag_ids, _matched_tags_by_id = match_filename_tags(filename, tag_match_context)
    after_tag_ids = merge_matched_tag_ids(
        before_tag_ids,
        matched_tag_ids,
        merge_mode="append_unique",
        tags_by_id=tag_match_context.tags_by_id,
    )
    if before_tag_ids == after_tag_ids:
        return normalized_only

    asset.tags = after_tag_ids
    collect_usage_count_deltas(before_tag_ids, after_tag_ids, usage_deltas)
    touched_tag_ids.update(set(after_tag_ids) - set(before_tag_ids))
    return True


def _ensure_album_chain(
    session,
    subdir_chain: list[str],
    date_group: str,
    requested_category_id: Optional[int] = None,
) -> list[str]:
    if not subdir_chain:
        return []

    public_ids: list[str] = []
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


def _ensure_album_chain_cached(
    session,
    subdir_chain: list[str],
    date_group: str,
    requested_category_id: Optional[int] = None,
) -> list[str]:
    _ = requested_category_id
    cache_key = f"{date_group}/{'/'.join(subdir_chain)}"
    cached = _album_chain_cache.get(cache_key)
    if cached is not None:
        return cached
    result = _ensure_album_chain(session, subdir_chain, date_group, requested_category_id)
    _album_chain_cache[cache_key] = result
    return result


def _update_album_photo_counts(session, public_ids: list[str]) -> None:
    if not public_ids:
        return
    for index, public_id in enumerate(public_ids):
        album = session.exec(select(Album).where(Album.public_id == public_id)).first()
        if not album:
            continue
        album.subtree_photo_count = (album.subtree_photo_count or 0) + 1
        if index == len(public_ids) - 1:
            album.photo_count = (album.photo_count or 0) + 1
        session.add(album)


def _set_album_cover_if_needed(session, public_ids: list[str], asset: ImageAsset) -> None:
    if not public_ids:
        return
    new_filename = asset.full_filename or ""
    for public_id in public_ids:
        album = session.exec(select(Album).where(Album.public_id == public_id)).first()
        if not album:
            continue
        current_cover = album.cover or {}
        if cover_is_manual(current_cover) and extract_cover_photo_id(current_cover):
            continue
        current_filename = current_cover.get("filename", "")
        if not current_filename or new_filename < current_filename:
            album.cover = build_asset_cover_payload(asset)
            session.add(album)


async def import_files(
    files: list[UploadFile],
    last_modified_times: Optional[list[Optional[int]]] = None,
    created_times: Optional[list[Optional[int]]] = None,
    category_id: Optional[int] = None,
) -> dict[str, list[str]]:
    init_db()
    load_hash_index()
    _album_chain_cache.clear()
    requested_category_id = normalize_import_category_id(category_id)

    imported: list[str] = []
    skipped: list[str] = []

    metadata = []
    for index, upload in enumerate(files):
        raw_filename = upload.filename or ""
        ts_ms: Optional[int] = (
            last_modified_times[index]
            if last_modified_times and index < len(last_modified_times)
            else None
        )
        created_ts_ms: Optional[int] = (
            created_times[index]
            if created_times and index < len(created_times)
            else None
        )
        subdir_chain, filename = parse_relative_path(raw_filename)
        if not is_image_ext(filename):
            skipped.append(raw_filename or "unknown")
            continue

        metadata.append({
            "upload": upload,
            "original": raw_filename,
            "ts_ms": ts_ms,
            "created_ts_ms": created_ts_ms,
            "source_time_ms": min_source_ts_ms(created_ts_ms, ts_ms),
            "subdir_chain": subdir_chain,
            "filename": filename,
        })

    subdir_min_ts: dict[str, int] = {}
    for meta in metadata:
        if meta["subdir_chain"]:
            top_subdir = meta["subdir_chain"][0]
            ts = meta["ts_ms"] if meta["ts_ms"] is not None else int(
                datetime.datetime.now().timestamp() * 1000
            )
            if top_subdir not in subdir_min_ts or ts < subdir_min_ts[top_subdir]:
                subdir_min_ts[top_subdir] = ts

    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    for meta in metadata:
        is_direct = not meta["subdir_chain"]
        top_subdir = meta["subdir_chain"][0] if meta["subdir_chain"] else None
        effective_ts = (
            meta["ts_ms"]
            if is_direct
            else (subdir_min_ts.get(top_subdir) if top_subdir is not None else None)
        )
        meta["effective_ts"] = effective_ts if effective_ts is not None else now_ms
        meta["date_group_computed"] = date_group_from_ts(
            meta["ts_ms"]
            if is_direct
            else (subdir_min_ts.get(top_subdir) if top_subdir is not None else None)
        )

    all_groups = {meta["date_group_computed"] for meta in metadata}
    with get_session() as session:
        groups_with_thumb: set[str] = set()
        candidates = session.exec(
            select(ImageAsset)
            .where(col(ImageAsset.date_group).in_(list(all_groups)))
            .where(col(ImageAsset.thumbs).isnot(None))
        ).all()
        for asset in candidates:
            if asset.date_group and has_required_thumb(asset.thumbs):
                groups_with_thumb.add(asset.date_group)

    new_group_first_idx: dict[str, int] = {}
    for index, meta in enumerate(metadata):
        date_group = meta["date_group_computed"]
        if date_group in groups_with_thumb:
            continue
        if date_group not in new_group_first_idx or (
            meta["effective_ts"] < metadata[new_group_first_idx[date_group]]["effective_ts"]
        ):
            new_group_first_idx[date_group] = index

    thumb_needed_indices = set(new_group_first_idx.values())
    for index, meta in enumerate(metadata):
        meta["needs_thumb"] = index in thumb_needed_indices

    for batch_start in range(0, len(metadata), IMPORT_BATCH_SIZE):
        batch_meta = metadata[batch_start: batch_start + IMPORT_BATCH_SIZE]

        batch_ready = []
        for meta in batch_meta:
            content = await meta["upload"].read()
            if not content:
                skipped.append(meta["original"])
                continue
            batch_ready.append((meta, content))

        if not batch_ready:
            continue

        pre_resolved: dict[int, tuple] = {}
        for index, (meta, content) in enumerate(batch_ready):
            quick_hash = quick_hash_from_bytes(content)
            meta["_quick_hash"] = quick_hash
            known_fh = lookup_quick_hash(quick_hash)
            if known_fh is not None and lookup_hash_index(known_fh) is not None:
                pre_resolved[index] = (known_fh, None, None, quick_hash, None, None)

        thumb_entries = [
            (str(index), content)
            for index, (meta, content) in enumerate(batch_ready)
            if index not in pre_resolved and meta["needs_thumb"]
        ]
        hash_entries = [
            (str(index), content)
            for index, (meta, content) in enumerate(batch_ready)
            if index not in pre_resolved and not meta["needs_thumb"]
        ]

        proc_thumb = process_from_bytes(thumb_entries, TEMP_DIR) if thumb_entries else {}
        proc_hash = process_hash_only_from_bytes(hash_entries) if hash_entries else {}
        proc = {**proc_thumb, **proc_hash}
        for index, value in pre_resolved.items():
            proc[str(index)] = value

        with get_session() as session:
            tag_match_context = load_tag_match_context(session, skip_tag_query_when_disabled=True)
            tag_usage_deltas: dict[int, int] = {}
            touched_tag_ids: set[int] = set()
            for index, (meta, content) in enumerate(batch_ready):
                result = proc.get(str(index), (None, None, "no result", None, None, None))
                file_hash, thumb_path_str, _error = result[0], result[1], result[2]
                quick_hash = result[3]
                px_w = result[4]
                px_h = result[5]
                original = meta["original"]
                file_size = len(content)
                mime_type = mime_from_name(meta["filename"])
                file_created_at = None
                if isinstance(meta.get("source_time_ms"), int) and meta["source_time_ms"] > 0:
                    file_created_at = datetime.datetime.fromtimestamp(meta["source_time_ms"] / 1000.0)

                if not file_hash:
                    skipped.append(original)
                    continue

                subdir_chain = meta["subdir_chain"]
                is_direct = not subdir_chain
                top_subdir = subdir_chain[0] if subdir_chain else None

                rel_thumb_path = (
                    to_project_relative(Path(thumb_path_str)) if thumb_path_str else None
                )
                new_thumb = required_thumb_entry(rel_thumb_path) if rel_thumb_path else None

                date_group = (
                    date_group_from_ts(meta["ts_ms"])
                    if is_direct
                    else date_group_from_ts(
                        subdir_min_ts.get(top_subdir) if top_subdir is not None else None
                    )
                )

                cached_id = lookup_hash_index(file_hash)
                existing = None
                if cached_id is not None:
                    existing = session.get(ImageAsset, cached_id)
                if existing is None:
                    existing = session.exec(
                        select(ImageAsset).where(ImageAsset.file_hash == file_hash)
                    ).first()

                if existing:
                    if subdir_chain:
                        album_public_ids = _ensure_album_chain_cached(
                            session,
                            subdir_chain,
                            date_group,
                            requested_category_id,
                        )
                        media_path = save_to_media(
                            content,
                            meta["filename"],
                            date_group,
                            subdir_chain,
                            meta["source_time_ms"],
                        )
                        new_media_rel = to_project_relative(media_path)

                        existing_media = existing.media_path or []
                        existing_media.append(new_media_rel)
                        existing.media_path = existing_media

                        existing_album = existing.album or []
                        existing_album.append(album_public_ids)
                        existing.album = existing_album

                        if new_thumb:
                            existing.thumbs = upsert_thumb(existing.thumbs, new_thumb)

                        apply_import_category_to_image_asset(existing, requested_category_id)
                        apply_import_filename_tags(
                            existing,
                            meta["filename"],
                            tag_match_context,
                            usage_deltas=tag_usage_deltas,
                            touched_tag_ids=touched_tag_ids,
                        )

                        session.add(existing)
                        # Write album_image mapping for the leaf album
                        if album_public_ids and existing.id is not None:
                            leaf_pid = album_public_ids[-1]
                            leaf_album = session.exec(select(Album).where(Album.public_id == leaf_pid)).first()
                            if leaf_album and leaf_album.id is not None:
                                exists_row = session.exec(
                                    select(AlbumImage)
                                    .where(AlbumImage.album_id == leaf_album.id)
                                    .where(AlbumImage.image_id == existing.id)
                                ).first()
                                if not exists_row:
                                    session.add(AlbumImage(album_id=leaf_album.id, image_id=existing.id))
                        _update_album_photo_counts(session, album_public_ids)
                        _set_album_cover_if_needed(session, album_public_ids, existing)
                        if existing.id is not None:
                            add_to_hash_index(file_hash, existing.id, quick_hash)
                        imported.append(original)
                    else:
                        thumb_ok = has_required_thumb(existing.thumbs)
                        media_resolved = resolve_stored_path(
                            existing.media_path[0] if existing.media_path else None
                        )
                        media_ok = bool(media_resolved and media_resolved.exists())

                        needs_update = False
                        if not media_ok:
                            media_path = save_to_media(
                                content,
                                meta["filename"],
                                date_group,
                                subdir_chain,
                                meta["source_time_ms"],
                            )
                            existing.media_path = [to_project_relative(media_path)]
                            existing.date_group = date_group
                            needs_update = True
                        if not thumb_ok and meta["needs_thumb"] and new_thumb:
                            existing.thumbs = upsert_thumb(existing.thumbs, new_thumb)
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
                        if apply_import_filename_tags(
                            existing,
                            meta["filename"],
                            tag_match_context,
                            usage_deltas=tag_usage_deltas,
                            touched_tag_ids=touched_tag_ids,
                        ):
                            needs_update = True
                        if apply_import_category_to_image_asset(existing, requested_category_id):
                            needs_update = True
                        if existing.imported_at is None:
                            existing.imported_at = datetime.datetime.now()
                            needs_update = True

                        if needs_update:
                            session.add(existing)
                            if existing.id is not None:
                                add_to_hash_index(file_hash, existing.id, quick_hash)
                            imported.append(original)
                        else:
                            skipped.append(original)
                    continue

                if px_w is None or px_h is None:
                    px_w, px_h = image_dimensions_from_bytes(content)

                album_public_ids = (
                    _ensure_album_chain_cached(session, subdir_chain, date_group, requested_category_id)
                    if subdir_chain
                    else []
                )
                asset_category_id = requested_category_id
                media_path = save_to_media(
                    content,
                    meta["filename"],
                    date_group,
                    subdir_chain,
                    meta["source_time_ms"],
                )
                asset = ImageAsset(
                    original_path=original,
                    full_filename=Path(meta["filename"]).name,
                    file_hash=file_hash,
                    quick_hash=quick_hash,
                    thumbs=[new_thumb] if new_thumb else [],
                    media_path=[to_project_relative(media_path)],
                    date_group=date_group,
                    file_created_at=file_created_at,
                    imported_at=datetime.datetime.now(),
                    width=px_w,
                    height=px_h,
                    file_size=file_size,
                    mime_type=mime_type,
                    category_id=asset_category_id,
                    tags=[],
                    album=[album_public_ids] if album_public_ids else [],
                    collection=[],
                )
                apply_import_filename_tags(
                    asset,
                    meta["filename"],
                    tag_match_context,
                    usage_deltas=tag_usage_deltas,
                    touched_tag_ids=touched_tag_ids,
                )
                session.add(asset)
                session.flush()

                if album_public_ids:
                    _update_album_photo_counts(session, album_public_ids)
                    _set_album_cover_if_needed(session, album_public_ids, asset)
                    # Write album_image mapping for the leaf album
                    if asset.id is not None:
                        leaf_pid = album_public_ids[-1]
                        leaf_album = session.exec(select(Album).where(Album.public_id == leaf_pid)).first()
                        if leaf_album and leaf_album.id is not None:
                            session.add(AlbumImage(album_id=leaf_album.id, image_id=asset.id))

                if asset.id is not None:
                    add_to_hash_index(file_hash, asset.id, quick_hash)
                imported.append(original)

            if touched_tag_ids:
                touch_tag_last_used(tag_match_context.tags_by_id, touched_tag_ids, now_tag_timestamp())
            if tag_usage_deltas:
                apply_usage_count_deltas(tag_match_context.tags_by_id, tag_usage_deltas)
            session.commit()

        del batch_ready

    save_hash_index()
    return {"imported": imported, "skipped": skipped}
