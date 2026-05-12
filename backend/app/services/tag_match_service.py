from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

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
    tags_by_first_atom: dict[str, list[tuple[str, ...]]] = field(default_factory=dict)


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


def _build_tag_name_atom_index(tags_by_name: dict[str, Tag]) -> dict[str, list[tuple[str, ...]]]:
    index: dict[str, list[tuple[str, ...]]] = {}
    for tag_name in tags_by_name:
        atoms = tuple(part for part in str(tag_name or "").strip().lower().split("_") if part)
        if not atoms:
            continue
        index.setdefault(atoms[0], []).append(atoms)

    for first_atom, candidates in index.items():
        index[first_atom] = sorted(candidates, key=lambda atoms: (-len(atoms), "_".join(atoms)))
    return index


def _normalize_joined_filename_payload(stem: str) -> str:
    value = re.sub(r"\s*\(\d+\)$", "", (stem or "").strip())
    if value.startswith("__"):
        body, marker, _suffix = value[2:].rpartition("__")
        if marker and body:
            value = body
    value = re.sub(r"[^0-9a-zA-Z_]+", "_", value.lower())
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _extract_joined_filename_tokens(
    stem: str,
    context: TagMatchContext,
) -> list[str]:
    if not context.tags_by_name:
        return []

    payload = _normalize_joined_filename_payload(stem)
    if not payload or "_" not in payload:
        return []

    atoms = [atom for atom in payload.split("_") if atom]
    if not atoms:
        return []

    tags_by_first_atom = context.tags_by_first_atom or _build_tag_name_atom_index(context.tags_by_name)

    tokens: list[str] = []
    seen: set[str] = set()
    index = 0
    while index < len(atoms):
        matched_name = ""
        matched_length = 0
        for candidate_atoms in tags_by_first_atom.get(atoms[index], []):
            candidate_length = len(candidate_atoms)
            if tuple(atoms[index:index + candidate_length]) != candidate_atoms:
                continue
            candidate_name = "_".join(candidate_atoms)
            if len(candidate_name) < context.min_token_length:
                continue
            if context.drop_numeric_only and candidate_name.isdigit():
                continue
            if candidate_name in context.noise_tokens:
                continue
            matched_name = candidate_name
            matched_length = candidate_length
            break

        if matched_name:
            if matched_name not in seen:
                seen.add(matched_name)
                tokens.append(matched_name)
            index += matched_length
            continue

        index += 1

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
            tags_by_first_atom={},
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
    tags_by_first_atom = _build_tag_name_atom_index(tags_by_name)
    return TagMatchContext(
        enabled=enabled,
        noise_tokens=noise_tokens,
        min_token_length=min_token_length,
        drop_numeric_only=drop_numeric_only,
        tags_by_name=tags_by_name,
        tags_by_id=tags_by_id,
        tags_by_first_atom=tags_by_first_atom,
    )


def match_filename_tags(filename: str, context: TagMatchContext) -> tuple[list[str], list[int], dict[int, Tag]]:
    if not context.enabled:
        return [], [], {}

    stem = filename_stem(filename)
    tokens = extract_tokens(
        stem,
        noise_tokens=context.noise_tokens,
        min_token_length=context.min_token_length,
        drop_numeric_only=context.drop_numeric_only,
    )
    has_direct_token_match = any(token in context.tags_by_name for token in tokens)

    if "_" in stem:
        joined_tokens = _extract_joined_filename_tokens(stem, context)
        if joined_tokens and not has_direct_token_match:
            tokens = joined_tokens

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