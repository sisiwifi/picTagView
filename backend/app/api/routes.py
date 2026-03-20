import asyncio
import hashlib
import json
import os
import shlex
import subprocess
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
    ViewerPreferenceRequest,
    YearGroup,
)
from app.core.config import CACHE_DIR, DATA_DIR, MEDIA_DIR, PROJECT_ROOT, TEMP_DIR, VIEWER_ICON_DIR
from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.services.cache_thumb_service import generate_cache_thumbs_progressively
from app.services.import_service import import_files, refresh_library

router = APIRouter()

# ── In-memory task store for async cache generation ───────────────────────────
_task_store: Dict[str, dict] = {}
_TASK_TTL = 600  # seconds

_APP_SETTINGS_FILE = DATA_DIR / "app_settings.json"
_IMAGE_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".avif",
]


def _prune_tasks() -> None:
    now = time.time()
    stale = [tid for tid, t in _task_store.items() if now - t["created_at"] > _TASK_TTL]
    for tid in stale:
        del _task_store[tid]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _thumb_url(asset: ImageAsset) -> str:
    for thumb in asset.thumbs or []:
        if not isinstance(thumb, dict):
            continue
        p = thumb.get("path")
        if not isinstance(p, str) or not p:
            continue
        resolved = _resolve_stored_path(p)
        if resolved and resolved.exists():
            return f"/thumbnails/{resolved.name}"

    if asset.thumb_path:
        resolved = _resolve_stored_path(asset.thumb_path)
        if resolved and resolved.exists():
            return f"/thumbnails/{resolved.name}"
    return ""


def _resolve_stored_path(stored_path: Optional[str]) -> Optional[Path]:
    if not stored_path:
        return None
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def _cache_thumb_url(asset: ImageAsset) -> Optional[str]:
    cache_file = CACHE_DIR / f"{asset.file_hash}_cache.webp"
    if cache_file.exists():
        return f"/cache/{asset.file_hash}_cache.webp"
    return None


def _load_app_settings() -> dict:
    if not _APP_SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(_APP_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_app_settings(data: dict) -> None:
    try:
        _APP_SETTINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _get_preferred_viewer_id() -> Optional[str]:
    data = _load_app_settings()
    viewer_id = data.get("preferred_image_viewer")
    if isinstance(viewer_id, str) and viewer_id.strip():
        return viewer_id.strip()
    return None


def _set_preferred_viewer_id(viewer_id: str) -> None:
    data = _load_app_settings()
    data["preferred_image_viewer"] = viewer_id
    _save_app_settings(data)


def _clear_preferred_viewer_id() -> None:
    data = _load_app_settings()
    if "preferred_image_viewer" in data:
        del data["preferred_image_viewer"]
        _save_app_settings(data)


def _read_reg_default(winreg_module, root, path: str, value_name: str = "") -> Optional[str]:
    try:
        with winreg_module.OpenKey(root, path) as key:
            value, _ = winreg_module.QueryValueEx(key, value_name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    except OSError:
        return None
    return None


def _enum_reg_value_names(winreg_module, root, path: str) -> list[str]:
    names: list[str] = []
    try:
        with winreg_module.OpenKey(root, path) as key:
            _, value_count, _ = winreg_module.QueryInfoKey(key)
            for idx in range(value_count):
                value_name, _, _ = winreg_module.EnumValue(key, idx)
                if value_name:
                    names.append(value_name)
    except OSError:
        return []
    return names


def _exe_name_from_command(command: str) -> str:
    if not command:
        return ""
    try:
        parts = shlex.split(command, posix=False)
    except Exception:
        parts = []
    if not parts:
        cmd = command.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 1:
                return Path(cmd[1:end]).name.lower()
        return Path(cmd.split(" ")[0]).name.lower()
    return Path(parts[0]).name.lower()


def _path_from_command(command: str) -> Optional[str]:
    if not command:
        return None
    try:
        parts = shlex.split(command, posix=False)
    except Exception:
        parts = []
    if not parts:
        cmd = command.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 1:
                return cmd[1:end]
        return cmd.split(" ")[0] if cmd else None
    return parts[0]


def _parse_default_icon_path(icon_value: str) -> Optional[str]:
    if not icon_value:
        return None

    raw = icon_value.strip()
    if not raw:
        return None

    path_part = raw
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end > 1:
            path_part = raw[1:end]
    else:
        if "," in raw:
            left, right = raw.rsplit(",", 1)
            try:
                int(right.strip())
                path_part = left.strip()
            except Exception:
                path_part = raw

    path_part = os.path.expandvars(path_part).strip().strip('"')
    if not path_part:
        return None
    return path_part


def _extract_icon_png_windows(source_path: str, output_path: Path) -> bool:
    if sys.platform != "win32":
        return False
    if not source_path:
        return False

    source = Path(os.path.expandvars(source_path)).resolve()
    if not source.exists() or not source.is_file():
        return False

    src = str(source).replace("'", "''")
    out = str(output_path).replace("'", "''")

    ps_script = (
        "$ErrorActionPreference = 'Stop'; "
        "Add-Type -AssemblyName System.Drawing; "
        f"$src = '{src}'; "
        f"$out = '{out}'; "
        "$icon = $null; "
        "$ext = [System.IO.Path]::GetExtension($src).ToLowerInvariant(); "
        "if ($ext -eq '.ico') { $icon = New-Object System.Drawing.Icon($src) } "
        "else { $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($src) }; "
        "if ($null -eq $icon) { exit 2 }; "
        "$bmp = $icon.ToBitmap(); "
        "$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png); "
        "$bmp.Dispose(); $icon.Dispose(); "
        "exit 0"
    )

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=6,
        )
        return completed.returncode == 0 and output_path.exists()
    except Exception:
        return False


def _viewer_icon_filename(viewer_id: str) -> str:
    digest = hashlib.sha1(viewer_id.encode("utf-8", errors="ignore")).hexdigest()
    return f"{digest}.png"


def _ensure_viewer_icon(viewer: dict) -> Optional[str]:
    if sys.platform != "win32":
        return None

    viewer_id = viewer.get("id") or ""
    if not viewer_id:
        return None

    file_name = _viewer_icon_filename(viewer_id)
    icon_path = VIEWER_ICON_DIR / file_name
    if icon_path.exists() and icon_path.stat().st_size > 0:
        return f"/viewer-icons/{file_name}"

    for source in viewer.get("icon_sources", []):
        if _extract_icon_png_windows(source, icon_path):
            return f"/viewer-icons/{file_name}"
    return None


def _score_viewer_candidate(display_name: str, command: str, prog_id: str) -> int:
    text = f"{display_name} {command} {prog_id}".lower()
    score = 1

    keep_keywords = [
        "photo", "image", "picture", "viewer", "jpeg", "jpg", "png", "webp", "gif", "bmp", "tiff", "heic", "avif",
        "照片", "图片", "看图", "查看", "画图", "irfan", "i_view", "xnview", "honeyview", "nomacs", "photos",
    ]
    drop_keywords = [
        "chrome", "msedge", "firefox", "code", "devenv", "notepad", "word", "excel", "powerpoint", "outlook",
        "powershell", "cmd.exe", "wscript", "cscript",
    ]

    if any(k in text for k in keep_keywords):
        score += 2
    if any(k in text for k in drop_keywords):
        score -= 3

    exe_name = _exe_name_from_command(command)
    if exe_name in {
        "i_view64.exe", "i_view32.exe", "irfanview.exe", "photos.exe", "mspaint.exe", "photoviewer.dll",
        "honeyview.exe", "xnview.exe", "xnviewmp.exe", "nomacs.exe", "qimgv.exe",
    }:
        score += 3
    if exe_name in {"chrome.exe", "msedge.exe", "firefox.exe", "code.exe", "notepad.exe", "winword.exe", "excel.exe"}:
        score -= 4

    return score


def _resolve_viewer_candidate(prog_id: str) -> Optional[dict]:
    if sys.platform != "win32" or not prog_id:
        return None

    import winreg

    display_name = (
        _read_reg_default(winreg, winreg.HKEY_CLASSES_ROOT, prog_id)
        or _read_reg_default(winreg, winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\\Application")
        or prog_id
    )
    command = _read_reg_default(winreg, winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\\shell\\open\\command") or ""
    default_icon_raw = _read_reg_default(winreg, winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\\DefaultIcon") or ""
    app_icon_raw = _read_reg_default(winreg, winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\\Application", "ApplicationIcon") or ""

    icon_sources: list[str] = []
    for raw in (default_icon_raw, app_icon_raw):
        parsed = _parse_default_icon_path(raw)
        if parsed:
            icon_sources.append(parsed)
    cmd_path = _path_from_command(command)
    if cmd_path:
        icon_sources.append(cmd_path)

    # Keep order and de-duplicate.
    seen: set[str] = set()
    unique_sources: list[str] = []
    for src in icon_sources:
        key = src.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_sources.append(src)

    source_type = "appx" if prog_id.startswith("AppX") else "win32"
    icon_text = (display_name[:1].upper() if display_name else "?")

    return {
        "id": prog_id,
        "display_name": display_name,
        "command": command,
        "source_type": source_type,
        "icon_text": icon_text,
        "icon_sources": unique_sources,
    }


def _collect_image_viewers(extensions: list[str]) -> tuple[list[dict], dict[str, str]]:
    if sys.platform != "win32":
        return [], {}

    import winreg

    ext_defaults: dict[str, str] = {}
    all_progids: set[str] = set()

    for ext in extensions:
        ext = ext.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"

        user_choice = _read_reg_default(
            winreg,
            winreg.HKEY_CURRENT_USER,
            rf"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\UserChoice",
            "ProgId",
        )
        if user_choice:
            ext_defaults[ext] = user_choice
            all_progids.add(user_choice)

        class_default = _read_reg_default(winreg, winreg.HKEY_CLASSES_ROOT, ext)
        if class_default:
            all_progids.add(class_default)

        for p in _enum_reg_value_names(
            winreg,
            winreg.HKEY_CURRENT_USER,
            rf"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\OpenWithProgids",
        ):
            all_progids.add(p)
        for p in _enum_reg_value_names(
            winreg,
            winreg.HKEY_CLASSES_ROOT,
            rf"{ext}\\OpenWithProgids",
        ):
            all_progids.add(p)

    raw_candidates: list[dict] = []
    for prog_id in sorted(all_progids):
        candidate = _resolve_viewer_candidate(prog_id)
        if not candidate:
            continue
        raw_candidates.append(candidate)

    preferred = _get_preferred_viewer_id()
    default_ids = set(ext_defaults.values())

    filtered: list[dict] = []
    for c in raw_candidates:
        score = _score_viewer_candidate(c["display_name"], c["command"], c["id"])
        keep = score >= 1 or c["id"] in default_ids or c["id"] == preferred
        if not keep:
            continue
        filtered.append(c)

    return filtered, ext_defaults


def _launch_with_preferred_viewer(command_template: str, file_path: Path) -> bool:
    if not command_template:
        return False

    path_str = str(file_path)
    cmd = command_template.strip()
    if not cmd:
        return False

    try:
        if any(token in cmd for token in ("%1", "%L", "%*")):
            final_cmd = (
                cmd.replace("%1", f'"{path_str}"')
                .replace("%L", f'"{path_str}"')
                .replace("%*", f'"{path_str}"')
            )
            subprocess.Popen(final_cmd, shell=True)
            return True

        parts = shlex.split(cmd, posix=False)
        if not parts:
            return False
        parts.append(path_str)
        subprocess.Popen(parts, shell=False)
        return True
    except Exception:
        return False


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


def _get_viewer_name_by_id(viewer_id: Optional[str]) -> Optional[str]:
    if not viewer_id:
        return None
    candidate = _resolve_viewer_candidate(viewer_id)
    if candidate and candidate.get("display_name"):
        return candidate["display_name"]
    return viewer_id


# ── Basic ─────────────────────────────────────────────────────────────────────

@router.get("/")
def root() -> dict:
    return {"status": "ok"}


@router.post("/api/import", response_model=ImportResponse)
async def import_images(
    files: List[UploadFile] = File(...),
    last_modified_json: Optional[str] = Form(None),
    created_time_json: Optional[str] = Form(None),
) -> ImportResponse:
    last_modified_times: Optional[List[Optional[int]]] = None
    created_times: Optional[List[Optional[int]]] = None

    if last_modified_json:
        try:
            last_modified_times = json.loads(last_modified_json)
        except Exception:
            last_modified_times = None

    if created_time_json:
        try:
            created_times = json.loads(created_time_json)
        except Exception:
            created_times = None

    result = await import_files(files, last_modified_times, created_times)
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
            (a for a in group_assets if _thumb_url(a)),
            None,
        )
        thumb_url = _thumb_url(rep) if rep else ""

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

    media_base = (MEDIA_DIR / date_group).resolve()

    direct_items: list[DateItem] = []
    album_rep: dict[str, ImageAsset] = {}
    album_count: dict[str, int] = {}

    for asset in assets:
        if not asset.media_path:
            continue
        media_path = _resolve_stored_path(asset.media_path)
        if not media_path:
            continue
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
    """Open image with app-preferred viewer first, fallback to system default."""
    with get_session() as session:
        asset = session.get(ImageAsset, image_id)
    if not asset or not asset.media_path:
        raise HTTPException(status_code=404, detail="Image not found")
    path = _resolve_stored_path(asset.media_path)
    if not path:
        raise HTTPException(status_code=404, detail="File path is invalid")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    if sys.platform == "win32":
        preferred_id = _get_preferred_viewer_id()
        if preferred_id:
            preferred = _resolve_viewer_candidate(preferred_id)
            if preferred and _launch_with_preferred_viewer(preferred.get("command", ""), path):
                return {"status": "ok", "mode": "preferred", "viewer_id": preferred_id}
        os.startfile(str(path))
        return {"status": "ok", "mode": "system"}
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)

    return {"status": "ok", "mode": "system"}


# ── System info ───────────────────────────────────────────────────────────────

@router.get("/api/system/viewer-info")
def viewer_info() -> dict:
    preferred_id = _get_preferred_viewer_id()
    preferred_name = _get_viewer_name_by_id(preferred_id)
    system_name = _get_default_image_viewer()
    return {
        "viewer": preferred_name or system_name,
        "preferred_viewer_id": preferred_id,
        "system_viewer": system_name,
    }


@router.get("/api/system/image-viewers")
def image_viewers() -> dict:
    viewers, ext_defaults = _collect_image_viewers(_IMAGE_EXTENSIONS)
    preferred_id = _get_preferred_viewer_id()

    default_ids = set(ext_defaults.values())
    items = []
    for v in viewers:
        icon_url = _ensure_viewer_icon(v)
        items.append({
            "id": v["id"],
            "display_name": v["display_name"],
            "icon_text": v.get("icon_text", "?"),
            "icon_url": icon_url,
            "source_type": v.get("source_type", "win32"),
            "is_system_default": v["id"] in default_ids,
            "is_selected": v["id"] == preferred_id,
        })

    return {
        "extensions": _IMAGE_EXTENSIONS,
        "selected_viewer_id": preferred_id,
        "system_default": _get_default_image_viewer(),
        "viewers": items,
    }


@router.get("/api/system/viewer-preference")
def viewer_preference() -> dict:
    viewer_id = _get_preferred_viewer_id()
    return {
        "viewer_id": viewer_id,
        "viewer_name": _get_viewer_name_by_id(viewer_id),
    }


@router.post("/api/system/viewer-preference")
def set_viewer_preference(body: ViewerPreferenceRequest) -> dict:
    viewer_id = (body.viewer_id or "").strip()
    if not viewer_id:
        _clear_preferred_viewer_id()
        return {"ok": True, "viewer_id": "", "viewer_name": _get_default_image_viewer()}

    viewers, _ = _collect_image_viewers(_IMAGE_EXTENSIONS)
    valid_ids = {v["id"] for v in viewers}

    if viewer_id not in valid_ids:
        raise HTTPException(status_code=400, detail="viewer_id is not in filtered image viewer list")

    _set_preferred_viewer_id(viewer_id)
    return {
        "ok": True,
        "viewer_id": viewer_id,
        "viewer_name": _get_viewer_name_by_id(viewer_id),
    }


# ── Cache management ──────────────────────────────────────────────────────────

import stat
import shutil

def _force_remove_contents(dir_path: Path) -> tuple[int, list[str]]:
    deleted = 0
    errs = []
    if not (dir_path.exists() and dir_path.is_dir()):
        return 0, errs

    # Pre-list all items to avoid issues with directory iteration during deletion on Windows
    try:
        items = list(dir_path.iterdir())
    except Exception as e:
        errs.append(f"list error: {e}")
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
            except Exception as e:
                errs.append(f"file error: {item.name}")
        elif item.is_dir():
            try:
                count = sum(1 for p in item.rglob('*') if p.is_file())
                def onerror(func, path, exc_info):
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                shutil.rmtree(item, onerror=onerror)
                deleted += count
            except Exception as e:
                errs.append(f"dir error: {item.name}")
    return deleted, errs

@router.delete("/api/cache")
def clear_cache() -> dict:
    """Delete all files in TEMP_DIR and CACHE_DIR; then strip stale DB thumb references."""
    temp_deleted, temp_errs = _force_remove_contents(TEMP_DIR)
    cache_deleted, cache_errs = _force_remove_contents(CACHE_DIR)
    
    errors: list[str] = temp_errs + cache_errs

    # Strip stale thumb references from the database so that the next
    # /api/admin/refresh correctly regenerates thumbnails.
    if temp_deleted or cache_deleted:
        try:
            with get_session() as session:
                for asset in session.exec(select(ImageAsset)).all():
                    changed = False
                    if asset.thumb_path:
                        p = _resolve_stored_path(asset.thumb_path)
                        if p and not p.exists():
                            asset.thumb_path = None
                            changed = True
                    if asset.thumbs:
                        valid: list[dict] = []
                        for t in asset.thumbs:
                            if not isinstance(t, dict):
                                continue
                            p = _resolve_stored_path(t.get("path"))
                            if p and p.exists():
                                valid.append(t)
                        if len(valid) != len(asset.thumbs):
                            asset.thumbs = valid
                            changed = True
                    if changed:
                        session.add(asset)
                session.commit()
        except Exception as e:
            errors.append(f"db_cleanup: {e}")

    result: dict = {"temp_deleted": temp_deleted, "cache_deleted": cache_deleted}
    if errors:
        result["error"] = "; ".join(errors[:5])
    return result


async def _run_cache_task(task_id: str, assets: list) -> None:
    """Background coroutine: generate cache thumbs and push results progressively."""
    loop = asyncio.get_running_loop()
    try:
        valid_assets = []
        for a in assets:
            media_path = _resolve_stored_path(a.media_path)
            if media_path and media_path.exists():
                valid_assets.append((a, media_path))

        def on_each(key: str, cache_path: Optional[str], _err: Optional[str]) -> None:
            _task_store[task_id]["items"].append({
                "id": int(key),
                "cache_thumb_url": f"/cache/{Path(cache_path).name}" if cache_path else None,
            })

        def run_progressive() -> None:
            generate_cache_thumbs_progressively(
                [(str(a.id), str(media_path)) for a, media_path in valid_assets],
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



