from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import DATA_DIR
from app.db import session as session_module
from app.models.tag import Tag


INITIAL_TAG_SEED_FILE = DATA_DIR / 'initial_tags_export.json'
_VALID_TAG_TYPES = {'normal', 'artist', 'copyright', 'character', 'series'}
_DRAFT_CREATED_BY = 'system:draft-reserve'


def _normalize_tag_name(value: object) -> str:
    return str(value or '').strip().lower()


def _normalize_tag_type(value: object) -> str:
    normalized = str(value or '').strip().lower() or 'normal'
    if normalized not in _VALID_TAG_TYPES:
        return 'normal'
    return normalized


def _normalize_created_by(value: object) -> str:
    normalized = str(value or '').strip() or 'import'
    if normalized == _DRAFT_CREATED_BY:
        return 'import'
    return normalized


def _normalize_metadata(value: object) -> dict:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _write_public_id(tag: Tag) -> None:
    tag.public_id = f'tag_{tag.id}'


def _extract_seed_tags(seed_path: Path) -> list[dict]:
    payload = json.loads(seed_path.read_text(encoding='utf-8'))
    if isinstance(payload, dict):
        items = payload.get('tags')
    else:
        items = payload
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def seed_initial_tags_if_needed(seed_path: Path | None = None) -> dict[str, int | bool | str]:
    target_path = seed_path or INITIAL_TAG_SEED_FILE
    if not target_path.is_file():
        return {
            'seeded': False,
            'imported': 0,
            'skipped': 0,
            'source': str(target_path),
        }

    with Session(session_module.engine) as session:
        existing_visible = session.exec(
            select(Tag.id).where(Tag.created_by != _DRAFT_CREATED_BY)  # type: ignore[attr-defined]
        ).first()
        if existing_visible is not None:
            return {
                'seeded': False,
                'imported': 0,
                'skipped': 0,
                'source': str(target_path),
            }

        imported = 0
        skipped = 0
        now = datetime.now()
        for item in _extract_seed_tags(target_path):
            name = _normalize_tag_name(item.get('name'))
            if not name:
                skipped += 1
                continue

            existing = session.exec(select(Tag).where(Tag.name == name)).first()  # type: ignore[attr-defined]
            if existing is not None:
                skipped += 1
                continue

            tag = Tag(
                name=name,
                display_name=str(item.get('display_name', name) or '').strip() or name,
                type=_normalize_tag_type(item.get('type')),
                description=str(item.get('description', '') or '').strip(),
                created_by=_normalize_created_by(item.get('created_by')),
                metadata_=_normalize_metadata(item.get('metadata')),
                created_at=now,
                updated_at=now,
            )
            session.add(tag)
            session.flush()
            _write_public_id(tag)
            session.add(tag)
            imported += 1

        session.commit()

    return {
        'seeded': imported > 0,
        'imported': imported,
        'skipped': skipped,
        'source': str(target_path),
    }