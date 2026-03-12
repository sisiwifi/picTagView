from pathlib import Path
from typing import Iterable, List


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}


def iter_image_files(folder: Path) -> Iterable[Path]:
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def list_image_files(folder: Path) -> List[Path]:
    return list(iter_image_files(folder))
