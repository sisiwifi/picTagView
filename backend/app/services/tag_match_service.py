from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlmodel import select

from app.models.tag import Tag
from app.services.app_settings_service import get_tag_match_setting

DRAFT_CREATED_BY = "system:draft-reserve"


@dataclass
class TagMatchContext:
    enabled: bool
    noise_tokens: set[str]
    min_token_length: int
    drop_numeric_only: bool
    tags_by_name: dict[str, Tag]
    tags_by_id: dict[int, Tag]


def now_tag_timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def filename_stem(filename: str) -> str:
    name = (filename or "").strip()
    if not name:
        return ""
    return Path(name).stem


def extract_tokens(
    stem: str,
    *,
    noise_tokens: set[str],
    min_token_length: int,
    drop_numeric_only: bool,
) -> list[str]:
    if not stem:
        return []

    tokens: list[str] = []
    seen: set[str] = set()
    for segment in stem.split(" "):
        token = segment.strip()
        if not token:
            continue
        if len(token) < min_token_length:
            continue
        if drop_numeric_only and token.isdigit():
            continue
        if token in noise_tokens:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def sanitize_tag_ids(raw_ids: object) -> list[int]:
    if not isinstance(raw_ids, list):
        return []
    result: list[int] = []
    seen: set[int] = set()
    for tag_id in raw_ids:
        if not isinstance(tag_id, int):
            continue
        if tag_id in seen:
            continue
        seen.add(tag_id)
        result.append(tag_id)
    return result


def sort_tag_ids_by_name(tag_ids: list[int], tags_by_id: dict[int, Tag]) -> list[int]:
    def _sort_key(tag_id: int) -> tuple[str, int]:
        tag = tags_by_id.get(tag_id)
        if not tag:
            return ("~", tag_id)
        return (str(tag.name or "~"), tag_id)

    return sorted(tag_ids, key=_sort_key)


def load_tag_match_context(session, *, skip_tag_query_when_disabled: bool = False) -> TagMatchContext:
    setting = get_tag_match_setting()
    enabled = bool(setting.get("enabled", True))
    if not enabled and skip_tag_query_when_disabled:
        return TagMatchContext(
            enabled=False,
            noise_tokens=set(),
            min_token_length=1,
            drop_numeric_only=False,
            tags_by_name={},
            tags_by_id={},
        )

    noise_tokens = set(setting.get("noise_tokens", [])) if enabled else set()
    min_token_length = int(setting.get("min_token_length", 2)) if enabled else 1
    drop_numeric_only = bool(setting.get("drop_numeric_only", True)) if enabled else False

    tags = session.exec(
        select(Tag).where(Tag.created_by != DRAFT_CREATED_BY)  # type: ignore[attr-defined]
    ).all()
    tags_by_name = {
        str(tag.name): tag
        for tag in tags
        if tag.id is not None and isinstance(tag.name, str) and tag.name
    }
    tags_by_id = {
        int(tag.id): tag
        for tag in tags
        if tag.id is not None
    }
    return TagMatchContext(
        enabled=enabled,
        noise_tokens=noise_tokens,
        min_token_length=min_token_length,
        drop_numeric_only=drop_numeric_only,
        tags_by_name=tags_by_name,
        tags_by_id=tags_by_id,
    )


def match_filename_tags(filename: str, context: TagMatchContext) -> tuple[list[str], list[int], dict[int, Tag]]:
    if not context.enabled:
        return [], [], {}

    tokens = extract_tokens(
        filename_stem(filename),
        noise_tokens=context.noise_tokens,
        min_token_length=context.min_token_length,
        drop_numeric_only=context.drop_numeric_only,
    )

    if not context.tags_by_name:
        return tokens, [], {}

    matched_tags_by_id: dict[int, Tag] = {}
    for token in tokens:
        tag = context.tags_by_name.get(token)
        if not tag or tag.id is None:
            continue
        matched_tags_by_id[int(tag.id)] = tag

    matched_tag_ids = sort_tag_ids_by_name(list(matched_tags_by_id.keys()), context.tags_by_id)
    return tokens, matched_tag_ids, matched_tags_by_id


def merge_matched_tag_ids(
    before_tag_ids: list[int],
    matched_tag_ids: list[int],
    *,
    merge_mode: str,
    tags_by_id: dict[int, Tag],
) -> list[int]:
    if merge_mode == "replace":
        return matched_tag_ids

    if merge_mode != "append_unique":
        raise ValueError("merge_mode must be append_unique or replace")

    merged_ids: list[int] = []
    merged_seen: set[int] = set()
    for candidate_id in before_tag_ids + matched_tag_ids:
        if candidate_id in merged_seen:
            continue
        merged_seen.add(candidate_id)
        merged_ids.append(candidate_id)
    return sort_tag_ids_by_name(merged_ids, tags_by_id)


def collect_usage_count_deltas(
    before_tag_ids: list[int],
    after_tag_ids: list[int],
    usage_deltas: dict[int, int],
) -> None:
    before_set = set(before_tag_ids)
    after_set = set(after_tag_ids)

    for tag_id in after_set - before_set:
        usage_deltas[tag_id] = usage_deltas.get(tag_id, 0) + 1
    for tag_id in before_set - after_set:
        usage_deltas[tag_id] = usage_deltas.get(tag_id, 0) - 1


def apply_usage_count_deltas(tags_by_id: dict[int, Tag], usage_deltas: dict[int, int]) -> bool:
    changed = False
    now = datetime.utcnow()
    for tag_id, delta in usage_deltas.items():
        if not delta:
            continue
        tag = tags_by_id.get(tag_id)
        if not tag:
            continue
        next_usage_count = max(0, int(tag.usage_count or 0) + int(delta))
        if int(tag.usage_count or 0) == next_usage_count:
            continue
        tag.usage_count = next_usage_count
        tag.updated_at = now
        changed = True
    return changed


def touch_tag_last_used(tags_by_id: dict[int, Tag], tag_ids: set[int], last_used_at: str) -> bool:
    changed = False
    now = datetime.utcnow()
    for tag_id in tag_ids:
        tag = tags_by_id.get(tag_id)
        if not tag:
            continue
        if tag.last_used_at == last_used_at:
            continue
        tag.last_used_at = last_used_at
        tag.updated_at = now
        changed = True
    return changed