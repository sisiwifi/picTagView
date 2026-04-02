import asyncio
import os
import shutil
import stat
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.common import resolve_stored_path
from app.api.schemas import CacheRequest, CacheStatusItem, CacheStatusResponse
from app.core.config import CACHE_DIR, TEMP_DIR
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.cache_thumb_service import generate_cache_thumbs_progressively
from app.services.imports.helpers import required_thumb_entry, to_project_relative, upsert_thumb

router = APIRouter()

_task_store: Dict[str, dict] = {}
_TASK_TTL = 600


def _prune_tasks() -> None:
    now = time.time()
    stale = [tid for tid, task in _task_store.items() if now - task["created_at"] > _TASK_TTL]
    for tid in stale:
        del _task_store[tid]


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


async def _run_cache_task(task_id: str, assets: list) -> None:
    loop = asyncio.get_running_loop()
    try:
        valid_assets = []
        for asset in assets:
            media_path = resolve_stored_path(asset.media_path[0] if asset.media_path else None)
            if media_path and media_path.exists():
                valid_assets.append((asset, media_path))

        asset_map = {str(asset.id): asset for asset, _ in valid_assets}

        def on_each(
            key: str,
            cache_path: Optional[str],
            err: Optional[str],
            thumb_w: Optional[int],
            thumb_h: Optional[int],
        ) -> None:
            _task_store[task_id]["items"].append({
                "id": int(key),
                "cache_thumb_url": f"/cache/{Path(cache_path).name}" if cache_path else None,
            })
            if cache_path and not err:
                try:
                    rel = to_project_relative(Path(cache_path))
                    entry = required_thumb_entry(rel, width=thumb_w or 0, height=thumb_h or 0)
                    orig = asset_map.get(key)
                    if orig is not None:
                        with get_session() as sess:
                            db_asset = sess.get(ImageAsset, orig.id)
                            if db_asset is not None:
                                db_asset.thumbs = upsert_thumb(db_asset.thumbs, entry)
                                sess.add(db_asset)
                                sess.commit()
                except Exception:
                    pass

        def run_progressive() -> None:
            generate_cache_thumbs_progressively(
                [(str(asset.id), str(media_path)) for asset, media_path in valid_assets],
                CACHE_DIR,
                on_each,
            )

        await loop.run_in_executor(None, run_progressive)
        _task_store[task_id]["status"] = "done"
    except Exception as exc:
        _task_store[task_id]["status"] = "error"
        _task_store[task_id]["error"] = str(exc)


@router.post("/api/thumbnails/cache")
async def start_cache_generation(body: CacheRequest) -> dict:
    _prune_tasks()
    if not body.image_ids:
        raise HTTPException(status_code=400, detail="image_ids must not be empty")

    with get_session() as session:
        assets = session.exec(
            select(ImageAsset).where(col(ImageAsset.id).in_(body.image_ids))
        ).all()

    task_id = str(uuid.uuid4())
    _task_store[task_id] = {"status": "running", "items": [], "created_at": time.time()}
    asyncio.create_task(_run_cache_task(task_id, list(assets)))
    return {"task_id": task_id}


@router.get("/api/thumbnails/cache/status/{task_id}", response_model=CacheStatusResponse)
def cache_status(task_id: str) -> CacheStatusResponse:
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return CacheStatusResponse(
        status=task["status"],
        items=[CacheStatusItem(**item) for item in task.get("items", [])],
    )