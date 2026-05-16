from __future__ import annotations

import shutil
import sys
from pathlib import Path
from threading import Lock

from app.api.common import normalize_stored_path
from app.core.config import MEDIA_DIR
from app.services.imports.helpers import apply_file_times, unique_dir_dest

_DIRECTORY_DIALOG_LOCK = Lock()


def select_directory_path(*, initial_dir: str | None = None, title: str = '选择文件夹') -> str | None:
    if sys.platform != 'win32':
        raise RuntimeError('当前系统暂不支持系统目录选择对话框')

    try:
        from tkinter import Tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError('系统目录选择对话框不可用') from exc

    with _DIRECTORY_DIALOG_LOCK:
        root = None
        try:
            root = Tk()
            root.withdraw()
            try:
                root.attributes('-topmost', True)
            except Exception:
                pass
            root.update_idletasks()

            selected = filedialog.askdirectory(
                parent=root,
                mustexist=True,
                initialdir=str(initial_dir or '').strip() or None,
                title=title,
            )
        except Exception as exc:
            raise RuntimeError('打开系统目录选择对话框失败') from exc
        finally:
            if root is not None:
                try:
                    root.destroy()
                except Exception:
                    pass

    normalized = str(selected or '').strip()
    if not normalized:
        return None
    return str(Path(normalized).resolve())


def reserve_unique_target_path(dest_dir: Path, filename: str, reserved: set[str] | None = None) -> Path:
    reserved_targets = reserved if reserved is not None else set()
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    index = 0
    while True:
        candidate_name = filename if index == 0 else f'{base_name}_{index}{suffix}'
        candidate = dest_dir / candidate_name
        candidate_key = str(candidate.resolve()).casefold()
        if candidate_key not in reserved_targets and not candidate.exists():
            reserved_targets.add(candidate_key)
            return candidate
        index += 1


def source_time_ms(path: Path) -> int | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return int(min(stat.st_ctime, stat.st_mtime) * 1000)


def normalize_export_album_path(album_path: str) -> str:
    normalized = normalize_stored_path(album_path).strip('/').strip()
    if not normalized:
        raise ValueError('相册路径不能为空')
    parts = [segment for segment in normalized.split('/') if segment]
    if not parts or any(segment in {'.', '..'} for segment in parts):
        raise ValueError('相册路径不合法')
    return '/'.join(parts)


def normalize_export_media_rel_path(media_rel_path: str) -> str:
    normalized = normalize_stored_path(media_rel_path).strip('/').strip()
    parts = [segment for segment in normalized.split('/') if segment]
    if len(parts) < 3 or parts[0] != 'media':
        raise ValueError('图片路径不合法')
    if any(segment in {'.', '..'} for segment in parts):
        raise ValueError('图片路径不合法')
    return '/'.join(parts)


def _sync_relative_directory_chain_times(source_root: Path, target_root: Path, relative_dir: Path) -> None:
    current_rel = Path()
    for segment in relative_dir.parts:
        current_rel = current_rel / segment
        source_dir = source_root / current_rel
        target_dir = target_root / current_rel
        if target_dir.exists():
            apply_file_times(target_dir, source_time_ms(source_dir))


def _sync_tree_times(source_root: Path, target_root: Path) -> None:
    if not target_root.exists():
        return

    file_paths = [path for path in source_root.rglob('*') if path.is_file()]
    for source_path in file_paths:
        target_path = target_root / source_path.relative_to(source_root)
        if target_path.exists():
            apply_file_times(target_path, source_time_ms(source_path))

    dir_paths = sorted(
        [path for path in source_root.rglob('*') if path.is_dir()],
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for source_dir in dir_paths:
        target_dir = target_root / source_dir.relative_to(source_root)
        if target_dir.exists():
            apply_file_times(target_dir, source_time_ms(source_dir))

    apply_file_times(target_root, source_time_ms(source_root))


def export_image_file(source_path: Path, media_rel_path: str, target_root: Path, reserved_targets: set[str] | None = None) -> Path:
    normalized_path = normalize_export_media_rel_path(media_rel_path)
    relative_path = Path(*normalized_path.split('/')[1:])
    relative_parent = relative_path.parent
    destination_dir = target_root / relative_parent
    destination_dir.mkdir(parents=True, exist_ok=True)

    target_path = reserve_unique_target_path(destination_dir, relative_path.name, reserved_targets)
    shutil.copy2(source_path, target_path)
    apply_file_times(target_path, source_time_ms(source_path))
    _sync_relative_directory_chain_times(MEDIA_DIR.resolve(), target_root.resolve(), relative_parent)
    return target_path


def export_album_directory(source_dir: Path, album_path: str, target_root: Path) -> Path:
    normalized_album_path = normalize_export_album_path(album_path)
    relative_path = Path(normalized_album_path)
    relative_parent = relative_path.parent
    destination_parent = target_root / relative_parent
    destination_parent.mkdir(parents=True, exist_ok=True)

    candidate_path = unique_dir_dest(destination_parent, source_dir.name)
    try:
        candidate_path.resolve().relative_to(source_dir.resolve())
    except ValueError:
        pass
    else:
        raise ValueError('导出目录不能位于相册内部')

    shutil.copytree(source_dir, candidate_path, copy_function=shutil.copy2)
    _sync_tree_times(source_dir, candidate_path)
    _sync_relative_directory_chain_times(MEDIA_DIR.resolve(), target_root.resolve(), relative_parent)
    return candidate_path