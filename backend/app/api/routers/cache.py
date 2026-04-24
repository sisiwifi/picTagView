import json
import os
import shutil
import stat
import threading
import time
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.api.common import cache_thumb_url, resolve_stored_path
from app.api.schemas import CacheRequest, CacheStartResponse, CacheStatusItem, CacheStatusResponse
from app.core.config import CACHE_DIR, TEMP_DIR
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.cache_thumb_service import generate_cache_thumb_entry, get_cache_thumb_worker_count
from app.services.imports.helpers import required_thumb_entry, to_project_relative, upsert_thumb

router = APIRouter()

_task_store: Dict[str, dict] = {}
_page_store: Dict[str, dict] = {}
_image_payloads: Dict[int, dict] = {}
_inflight_jobs: Dict[int, Future] = {}
_dispatch_order: deque[str] = deque()
_TASK_TTL = 600
_queue_lock = threading.RLock()
_worker_pool = ThreadPoolExecutor(max_workers=get_cache_thumb_worker_count())


def _log_cache_event(event: str, **payload: object) -> None:
    message = {
        "scope": "cache_queue",
        "event": event,
        **payload,
    }
    print(json.dumps(message, ensure_ascii=False, sort_keys=True), flush=True)


def _prune_tasks() -> None:
    now = time.time()
    stale = [tid for tid, task in _task_store.items() if now - task["created_at"] > _TASK_TTL]
    for tid in stale:
        task = _task_store.pop(tid, None)
        if not task:
            continue
        page_token = task.get("page_token")
        page = _page_store.get(page_token)
        if page and page.get("task_id") == tid:
            _page_store.pop(page_token, None)


def _force_remove_contents(dir_path: Path) -> tuple[int, list[str]]:
    deleted = 0
    errs = []
    if not (dir_path.exists() and dir_path.is_dir()):
        return 0, errs

    try:
        items = list(dir_path.iterdir())
    except Exception as exc:
        errs.append(f"list error: {exc}")
        return 0, errs

    for item in items:
        if item.is_file() or item.is_symlink():
            try:
                item.unlink(missing_ok=True)
                deleted += 1
            except PermissionError:
                try:
                    os.chmod(item, stat.S_IWRITE)
                    item.unlink(missing_ok=True)
                    deleted += 1
                except Exception:
                    errs.append(f"locked file: {item.name}")
            except Exception:
                errs.append(f"file error: {item.name}")
        elif item.is_dir():
            try:
                count = sum(1 for p in item.rglob("*") if p.is_file())

                def onerror(func, path, _exc_info):
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass

                shutil.rmtree(item, onerror=onerror)
                deleted += count
            except Exception:
                errs.append(f"dir error: {item.name}")
    return deleted, errs


def _normalize_requested_ids(body: CacheRequest) -> list[int]:
    raw_ids = body.ordered_image_ids or body.image_ids
    normalized: list[int] = []
    seen: set[int] = set()
    for value in raw_ids:
        image_id = int(value)
        if image_id <= 0 or image_id in seen:
            continue
        seen.add(image_id)
        normalized.append(image_id)
    return normalized


def _register_dispatch_token(page_token: str) -> None:
    if page_token in _dispatch_order:
        return
    _dispatch_order.append(page_token)


def _cleanup_dispatch_tokens_locked() -> None:
    stale_tokens = [token for token in _dispatch_order if token not in _page_store]
    if not stale_tokens:
        return
    for token in stale_tokens:
        try:
            _dispatch_order.remove(token)
        except ValueError:
            pass


def _append_task_item_locked(task: dict, image_id: int, cache_url: Optional[str]) -> None:
    delivered_ids = task.setdefault("delivered_ids", set())
    if image_id in delivered_ids:
        return
    delivered_ids.add(image_id)
    task["items"].append({
        "id": image_id,
        "cache_thumb_url": cache_url,
    })


def _finalize_page_if_idle_locked(page_token: str) -> None:
    page = _page_store.get(page_token)
    if not page:
        return
    if page["pending_set"]:
        return
    task = _task_store.get(page["task_id"])
    if task and task.get("status") == "running":
        task["status"] = "done"
    _page_store.pop(page_token, None)
    _cleanup_dispatch_tokens_locked()


def _take_next_image_id_locked(page_token: str) -> Optional[int]:
    page = _page_store.get(page_token)
    if not page:
        return None
    for image_id in page["pending_order"]:
        if image_id not in page["pending_set"]:
            continue
        if image_id in _inflight_jobs:
            continue
        return image_id
    return None


def _persist_cache_entry(image_id: int, cache_path: Path, width: Optional[int], height: Optional[int]) -> None:
    try:
        rel = to_project_relative(cache_path)
        entry = required_thumb_entry(rel, width=width or 0, height=height or 0)
        with get_session() as session:
            asset = session.get(ImageAsset, image_id)
            if asset is None:
                return
            asset.thumbs = upsert_thumb(asset.thumbs, entry)
            session.add(asset)
            session.commit()
    except Exception:
        pass


def _complete_image_for_current_pages(image_id: int, cache_url: Optional[str]) -> None:
    for page_token, page in list(_page_store.items()):
        if image_id not in page["pending_set"]:
            continue
        page["pending_set"].discard(image_id)
        task = _task_store.get(page["task_id"])
        if task and cache_url:
            _append_task_item_locked(task, image_id, cache_url)
        _finalize_page_if_idle_locked(page_token)


def _generate_cache_job(image_id: int, payload: dict) -> tuple[int, Optional[str], Optional[str], Optional[int], Optional[int]]:
    _key, cache_path, error, width, height = generate_cache_thumb_entry(
        str(image_id),
        payload["media_path"],
        CACHE_DIR,
    )
    return image_id, cache_path, error, width, height


def _dispatch_jobs() -> None:
    with _queue_lock:
        _cleanup_dispatch_tokens_locked()
        while len(_inflight_jobs) < get_cache_thumb_worker_count():
            dispatched = False
            checked = 0
            total_tokens = len(_dispatch_order)
            while checked < total_tokens:
                page_token = _dispatch_order[0]
                _dispatch_order.rotate(-1)
                checked += 1

                if page_token not in _page_store:
                    continue

                image_id = _take_next_image_id_locked(page_token)
                if image_id is None:
                    _finalize_page_if_idle_locked(page_token)
                    continue

                payload = _image_payloads.get(image_id)
                if not payload:
                    _page_store[page_token]["pending_set"].discard(image_id)
                    _finalize_page_if_idle_locked(page_token)
                    continue

                future = _worker_pool.submit(_generate_cache_job, image_id, payload)
                _inflight_jobs[image_id] = future
                future.add_done_callback(lambda fut, current_image_id=image_id: _handle_job_complete(current_image_id, fut))
                dispatched = True
                break

            if not dispatched:
                break


def _handle_job_complete(image_id: int, future: Future) -> None:
    cache_url: Optional[str] = None
    try:
        _, cache_path, error, width, height = future.result()
        if cache_path and not error:
            cache_path_obj = Path(cache_path)
            cache_url = f"/cache/{cache_path_obj.name}"
            _persist_cache_entry(image_id, cache_path_obj, width, height)
    except Exception:
        cache_url = None

    with _queue_lock:
        _inflight_jobs.pop(image_id, None)
        _complete_image_for_current_pages(image_id, cache_url)

    _dispatch_jobs()


@router.delete("/api/cache")
def clear_cache() -> dict:
    temp_deleted, temp_errs = _force_remove_contents(TEMP_DIR)
    cache_deleted, cache_errs = _force_remove_contents(CACHE_DIR)
    errors: list[str] = temp_errs + cache_errs

    if temp_deleted or cache_deleted:
        try:
            with get_session() as session:
                for asset in session.exec(select(ImageAsset)).all():
                    if not asset.thumbs:
                        continue
                    live: list[dict] = []
                    for thumb in asset.thumbs:
                        if not isinstance(thumb, dict):
                            continue
                        p = resolve_stored_path(thumb.get("path"))
                        if p and p.exists():
                            live.append(thumb)
                    if len(live) != len(asset.thumbs):
                        asset.thumbs = live
                        session.add(asset)
                session.commit()
        except Exception as exc:
            errors.append(f"db_cleanup: {exc}")

    result: dict = {"temp_deleted": temp_deleted, "cache_deleted": cache_deleted}
    if errors:
        result["error"] = "; ".join(errors[:5])
    return result


@router.post("/api/thumbnails/cache", response_model=CacheStartResponse)
async def start_cache_generation(body: CacheRequest) -> CacheStartResponse:
    request_ids = _normalize_requested_ids(body)
    if not request_ids:
        raise HTTPException(status_code=400, detail="image_ids must not be empty")

    task_id = str(uuid.uuid4())
    page_token = body.page_token or f"legacy:{task_id}"
    generation = body.generation if body.generation is not None else 0

    with get_session() as session:
        assets = session.exec(
            select(ImageAsset).where(col(ImageAsset.id).in_(request_ids))
        ).all()

    asset_map = {asset.id: asset for asset in assets if asset.id is not None}
    immediate_items: list[dict] = []
    queued_ids: list[int] = []
    delivered_ids: set[int] = set()

    for image_id in request_ids:
        asset = asset_map.get(image_id)
        if asset is None:
            continue
        existing_cache_url = cache_thumb_url(asset)
        if existing_cache_url:
            immediate_items.append({
                "id": image_id,
                "cache_thumb_url": existing_cache_url,
            })
            delivered_ids.add(image_id)
            continue

        media_path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
        if not media_path or not media_path.exists():
            continue
        _image_payloads[image_id] = {
            "media_path": str(media_path),
        }
        queued_ids.append(image_id)

    with _queue_lock:
        _prune_tasks()

        previous_page = _page_store.get(page_token)
        if previous_page:
            previous_task = _task_store.get(previous_page["task_id"])
            if previous_task and previous_task.get("status") == "running":
                previous_task["status"] = "done"
            dropped_count = len(previous_page["pending_set"])
            _page_store.pop(page_token, None)
            _log_cache_event(
                "supersede",
                page_token=page_token,
                old_generation=previous_page.get("generation"),
                new_generation=generation,
                dropped=dropped_count,
            )

        _task_store[task_id] = {
            "status": "running",
            "items": immediate_items,
            "created_at": time.time(),
            "generation": generation,
            "page_token": page_token,
            "delivered_ids": delivered_ids,
        }

        if queued_ids:
            _page_store[page_token] = {
                "task_id": task_id,
                "generation": generation,
                "pending_order": queued_ids,
                "pending_set": set(queued_ids),
            }
            _register_dispatch_token(page_token)
        else:
            _task_store[task_id]["status"] = "done"

        _log_cache_event(
            "enqueue",
            anchor_image_id=body.anchor_image_id,
            anchor_item_key=body.anchor_item_key,
            anchor_offset=body.anchor_offset,
            direction=body.direction,
            generation=generation,
            immediate=len(immediate_items),
            page_token=page_token,
            queued=len(queued_ids),
            sort_signature=body.sort_signature,
            task_id=task_id,
        )

    _dispatch_jobs()
    return CacheStartResponse(task_id=task_id, generation=generation)


@router.get("/api/thumbnails/cache/status/{task_id}", response_model=CacheStatusResponse)
def cache_status(
    task_id: str,
    cursor: int = Query(default=0, ge=0),
) -> CacheStatusResponse:
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    items = task.get("items", [])
    start_index = min(cursor, len(items))
    return CacheStatusResponse(
        status=task["status"],
        items=[CacheStatusItem(**item) for item in items[start_index:]],
        next_cursor=len(items),
        generation=task.get("generation"),
    )