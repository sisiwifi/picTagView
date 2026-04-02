import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

from app.core.config import DATA_DIR, VIEWER_ICON_DIR

_APP_SETTINGS_FILE = DATA_DIR / "app_settings.json"
IMAGE_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".avif",
]


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


def get_preferred_viewer_id() -> Optional[str]:
    data = _load_app_settings()
    viewer_id = data.get("preferred_image_viewer")
    if isinstance(viewer_id, str) and viewer_id.strip():
        return viewer_id.strip()
    return None


def set_preferred_viewer_id(viewer_id: str) -> None:
    data = _load_app_settings()
    data["preferred_image_viewer"] = viewer_id
    _save_app_settings(data)


def clear_preferred_viewer_id() -> None:
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


def ensure_viewer_icon(viewer: dict) -> Optional[str]:
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


def resolve_viewer_candidate(prog_id: str) -> Optional[dict]:
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


def collect_image_viewers(extensions: list[str]) -> tuple[list[dict], dict[str, str]]:
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
        candidate = resolve_viewer_candidate(prog_id)
        if not candidate:
            continue
        raw_candidates.append(candidate)

    preferred = get_preferred_viewer_id()
    default_ids = set(ext_defaults.values())

    filtered: list[dict] = []
    for candidate in raw_candidates:
        score = _score_viewer_candidate(candidate["display_name"], candidate["command"], candidate["id"])
        keep = score >= 1 or candidate["id"] in default_ids or candidate["id"] == preferred
        if keep:
            filtered.append(candidate)

    return filtered, ext_defaults


def launch_with_preferred_viewer(command_template: str, file_path: Path) -> bool:
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


def get_default_image_viewer() -> str:
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


def get_viewer_name_by_id(viewer_id: Optional[str]) -> Optional[str]:
    if not viewer_id:
        return None
    candidate = resolve_viewer_candidate(viewer_id)
    if candidate and candidate.get("display_name"):
        return candidate["display_name"]
    return viewer_id