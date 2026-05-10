from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps


@dataclass(frozen=True)
class PreviewFrame:
    image: np.ndarray
    width: int
    height: int
    is_animated: bool = False
    frame_count: int = 1
    animation_format: Optional[str] = None


def _normalized_animation_format(format_name: str | None) -> Optional[str]:
    if not format_name:
        return None
    normalized = str(format_name).strip().upper()
    return normalized or None


def _frame_count_for_image(image: Image.Image) -> int:
    try:
        count = int(getattr(image, 'n_frames', 1) or 1)
    except Exception:
        count = 1
    return max(1, count)


def _is_animated_image(image: Image.Image, frame_count: int) -> bool:
    if frame_count > 1:
        return True
    try:
        return bool(getattr(image, 'is_animated', False))
    except Exception:
        return False


def _to_cv_image(frame: Image.Image) -> np.ndarray:
    if frame.mode in ('RGBA', 'LA') or 'transparency' in frame.info:
        rgba = frame.convert('RGBA')
        return cv2.cvtColor(np.array(rgba), cv2.COLOR_RGBA2BGRA)
    rgb = frame.convert('RGB')
    return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)


def extract_preview_frame_from_bytes(content: bytes) -> PreviewFrame:
    try:
        with Image.open(BytesIO(content)) as image:
            format_name = _normalized_animation_format(image.format)
            frame_count = _frame_count_for_image(image)
            is_animated = _is_animated_image(image, frame_count)

            image.seek(0)
            frame = ImageOps.exif_transpose(image.copy())
            cv_image = _to_cv_image(frame)
            height, width = cv_image.shape[:2]
            return PreviewFrame(
                image=cv_image,
                width=int(width),
                height=int(height),
                is_animated=is_animated,
                frame_count=frame_count,
                animation_format=format_name if is_animated else None,
            )
    except Exception:
        image_array = np.frombuffer(content, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError('Failed to decode image data')
        height, width = image.shape[:2]
        return PreviewFrame(
            image=image,
            width=int(width),
            height=int(height),
            is_animated=False,
            frame_count=1,
            animation_format=None,
        )


def extract_preview_frame_from_path(path: Path | str) -> PreviewFrame:
    return extract_preview_frame_from_bytes(Path(path).read_bytes())