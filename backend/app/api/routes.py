import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlmodel import col, select

from app.api.schemas import (
    CacheRequest,
    CacheStatusItem,
    CacheStatusResponse,
    DateItem,
    DateItemsResponse,
    DateViewResponse,
    ImportResponse,
    MonthGroup,
    YearGroup,
)
from app.core.config import CACHE_DIR, MEDIA_DIR
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.cache_thumb_service import generate_cache_thumbs_progressively
from app.services.import_service import import_files, refresh_library

router = APIRouter()

# ── In-memory task store for async cache generation ───────────────────────────
_task_store: Dict[str, dict] = {}
_TASK_TTL = 600  # seconds


def _prune_tasks() -> None:
    now = time.time()
    stale = [tid for tid, t in _task_store.items() if now - t["created_at"] > _TASK_TTL]
    for tid in stale:
        del _task_store[tid]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _thumb_url(asset: ImageAsset) -> str:
    if asset.thumb_path:
        return f"/thumbnails/{Path(asset.thumb_path).name}"
    return ""


def _cache_thumb_url(asset: ImageAsset) -> Optional[str]:
    cache_file = CACHE_DIR / f"{asset.file_hash}_cache.webp"
    if cache_file.exists():
        return f"/cache/{asset.file_hash}_cache.webp"
    return None


def _get_default_image_viewer() -> str:
    """Return the default .jpg viewer name on Windows; 'Unknown' elsewhere."""
    try:
        if sys.platform != "win32":
            return "系统默认"
        import winreg
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.jpg\UserChoice",
            ) as key:
                prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        except OSError:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r".jpg") as key:
                prog_id = winreg.QueryValueEx(key, "")[0]
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id) as key:
                name = winreg.QueryValueEx(key, "")[0]
                if name:
                    return name
        except OSError:
            pass
        return prog_id
    except Exception:
        return "未知"


# ── Basic ─────────────────────────────────────────────────────────────────────

@router.get("/")
def root() -> dict:
    return {"status": "ok"}


@router.post("/api/import", response_model=ImportResponse)
async def import_images(
    files: List[UploadFile] = File(...),
    last_modified_json: Optional[str] = Form(None),
) -> ImportResponse:
    last_modified_times: Optional[List[Optional[int]]] = None
    if last_modified_json:
        try:
            last_modified_times = json.loads(last_modified_json)
        except Exception:
            last_modified_times = None

    result = await import_files(files, last_modified_times)
    return ImportResponse(**result)


@router.get("/api/images/count")
def images_count() -> dict:
    with get_session() as session:
        count = session.exec(select(ImageAsset)).all().__len__()
    return {"count": count}


@router.post("/api/admin/refresh")
def refresh() -> dict:
    return refresh_library()


# ── Date views ────────────────────────────────────────────────────────────────

@router.get("/api/dates", response_model=DateViewResponse)
def dates_view() -> DateViewResponse:
    with get_session() as session:
        assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group != None)  # noqa: E711
            .order_by(col(ImageAsset.id))
        ).all()

    group_map: dict[str, list[ImageAsset]] = defaultdict(list)
    for asset in assets:
        if asset.date_group:
            group_map[asset.date_group].append(asset)

    def sort_key(g: str):
        parts = g.split("-")
        return (int(parts[0]), int(parts[1]))

    sorted_groups = sorted(group_map.keys(), key=sort_key)

    year_map: dict[int, list[MonthGroup]] = defaultdict(list)
    for group in sorted_groups:
        parts = group.split("-")
        year, month = int(parts[0]), int(parts[1])
        group_assets = group_map[group]

        # Find any asset with a valid thumbnail to represent this month
        rep = next(
            (a for a in group_assets if a.thumb_path and Path(a.thumb_path).exists()),
            None,
        )
        thumb_url = f"/thumbnails/{Path(rep.thumb_path).name}" if (rep and rep.thumb_path) else ""

        year_map[year].append(
            MonthGroup(
                group=group,
                year=year,
                month=month,
                count=len(group_assets),
                thumb_url=thumb_url,
            )
        )

    years = [YearGroup(year=y, months=year_map[y]) for y in sorted(year_map.keys())]
    return DateViewResponse(years=years)


@router.get("/api/dates/{date_group}/items", response_model=DateItemsResponse)
def date_group_items(date_group: str) -> DateItemsResponse:
    with get_session() as session:
        assets = session.exec(
            select(ImageAsset)
            .where(ImageAsset.date_group == date_group)
            .order_by(col(ImageAsset.id))
        ).all()

    if not assets:
        raise HTTPException(status_code=404, detail=f"No assets for {date_group}")

    media_base = MEDIA_DIR / date_group

    direct_items: list[DateItem] = []
    album_rep: dict[str, ImageAsset] = {}
    album_count: dict[str, int] = {}

    for asset in assets:
        if not asset.media_path:
            continue
        media_path = Path(asset.media_path)
        try:
            rel = media_path.relative_to(media_base)
        except ValueError:
            continue

        parts = rel.parts
        if len(parts) == 1:
            direct_items.append(
                DateItem(
                    type="image",
                    name=parts[0],
                    thumb_url=_thumb_url(asset),
                    id=asset.id,
                    cache_thumb_url=_cache_thumb_url(asset),
                )
            )
        else:
            top_subdir = parts[0]
            if top_subdir not in album_rep:
                album_rep[top_subdir] = asset
                album_count[top_subdir] = 0
            album_count[top_subdir] += 1

    album_items: list[DateItem] = [
        DateItem(
            type="album",
            name=subdir,
            thumb_url=_thumb_url(asset),
            count=album_count[subdir],
            id=asset.id,
            cache_thumb_url=_cache_thumb_url(asset),
        )
        for subdir, asset in album_rep.items()
    ]

    return DateItemsResponse(
        date_group=date_group,
        items=direct_items + album_items,
    )


# ── Image actions ─────────────────────────────────────────────────────────────

@router.get("/api/images/{image_id}/open")
def open_image(image_id: int) -> dict:
    """Open the image with the system default viewer."""
    with get_session() as session:
        asset = session.get(ImageAsset, image_id)
    if not asset or not asset.media_path:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(asset.media_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        import subprocess
        subprocess.run(["open", str(path)], check=False)
    else:
        import subprocess
        subprocess.run(["xdg-open", str(path)], check=False)

    return {"status": "ok"}


# ── System info ───────────────────────────────────────────────────────────────

@router.get("/api/system/viewer-info")
def viewer_info() -> dict:
    return {"viewer": _get_default_image_viewer()}


# ── Cache management ──────────────────────────────────────────────────────────

@router.delete("/api/cache")
def clear_cache() -> dict:
    """Delete all files in CACHE_DIR."""
    deleted = 0
    for f in CACHE_DIR.iterdir():
        if f.is_file():
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass
    return {"deleted": deleted}


async def _run_cache_task(task_id: str, assets: list) -> None:
    """Background coroutine: generate cache thumbs and push results progressively."""
    loop = asyncio.get_running_loop()
    try:
        valid_assets = [
            a for a in assets if a.media_path and Path(a.media_path).exists()
        ]

        def on_each(key: str, cache_path: Optional[str], _err: Optional[str]) -> None:
            _task_store[task_id]["items"].append({
                "id": int(key),
                "cache_thumb_url": f"/cache/{Path(cache_path).name}" if cache_path else None,
            })

        def run_progressive() -> None:
            generate_cache_thumbs_progressively(
                [(str(a.id), str(a.media_path)) for a in valid_assets],
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
    """
    Start async cache thumbnail generation for the given image IDs.
    Returns { task_id } immediately; poll /api/thumbnails/cache/status/{task_id}.
    """
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

