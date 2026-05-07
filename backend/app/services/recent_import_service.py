from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlmodel import Session, col, delete, select

from app.db.session import get_session
from app.models.recent_import_operation import RecentImportOperation


def _normalize_int_list(values: Iterable[int | None] | None) -> list[int]:
    normalized: list[int] = []
    seen: set[int] = set()
    for value in values or []:
        if not isinstance(value, int) or value <= 0 or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized


def _normalize_string_list(values: Iterable[str | None] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        normalized.append(candidate)
        seen.add(candidate)
    return normalized


def _normalize_mode(mode: str | None) -> str:
    normalized = str(mode or "replace").strip().lower()
    return "append" if normalized == "append" else "replace"


def _merge_int_lists(existing: Iterable[int | None] | None, incoming: Iterable[int | None] | None) -> list[int]:
    return _normalize_int_list([*(existing or []), *(incoming or [])])


def _merge_string_lists(existing: Iterable[str | None] | None, incoming: Iterable[str | None] | None) -> list[str]:
    return _normalize_string_list([*(existing or []), *(incoming or [])])


def record_recent_import_operation(
    *,
    successful_image_ids: Iterable[int | None] | None = None,
    preview_image_ids: Iterable[int | None] | None,
    direct_image_ids: Iterable[int | None] | None,
    top_album_public_ids: Iterable[str | None] | None,
    mode: str = "replace",
) -> RecentImportOperation | None:
    preview_ids = _normalize_int_list(preview_image_ids)
    successful_ids = _normalize_int_list(successful_image_ids if successful_image_ids is not None else preview_image_ids)
    direct_ids = _normalize_int_list(direct_image_ids)
    album_public_ids = _normalize_string_list(top_album_public_ids)
    normalized_mode = _normalize_mode(mode)

    with get_session() as session:
        latest = get_latest_recent_import_operation(session)

        if normalized_mode == "append" and latest is not None:
            if successful_ids or preview_ids or direct_ids or album_public_ids:
                latest.successful_image_ids = _merge_int_lists(latest.successful_image_ids, successful_ids)
                latest.preview_image_ids = _merge_int_lists(latest.preview_image_ids, preview_ids)
                latest.direct_image_ids = _merge_int_lists(latest.direct_image_ids, direct_ids)
                latest.top_album_public_ids = _merge_string_lists(latest.top_album_public_ids, album_public_ids)
                latest.created_at = datetime.now()
                session.add(latest)
                session.commit()
                session.refresh(latest)
            return latest

        if normalized_mode == "append" and not successful_ids and not preview_ids and not direct_ids and not album_public_ids:
            return None

        session.exec(delete(RecentImportOperation))
        operation = RecentImportOperation(
            successful_image_ids=successful_ids,
            preview_image_ids=preview_ids,
            direct_image_ids=direct_ids,
            top_album_public_ids=album_public_ids,
        )
        session.add(operation)
        session.commit()
        session.refresh(operation)
        return operation


def get_latest_recent_import_operation(session: Session) -> RecentImportOperation | None:
    return session.exec(
        select(RecentImportOperation).order_by(col(RecentImportOperation.created_at).desc(), col(RecentImportOperation.id).desc())
    ).first()
