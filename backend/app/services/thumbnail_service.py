from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from app.core.config import TEMP_DIR


TARGET_SIZE: Tuple[int, int] = (800, 800)


def create_thumbnail_from_bytes(content: bytes, file_hash: str) -> Path:
    thumb_name = f"{file_hash}.webp"
    thumb_path = TEMP_DIR / thumb_name

    if thumb_path.exists():
        return thumb_path

    image_array = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image data")

    height, width = image.shape[:2]

    # 1:1 square crop
    if width > height:
        x_offset = (width - height) // 2
        cropped = image[:, x_offset : x_offset + height]
    elif height > width:
        y_offset = (height - width) // 2
        cropped = image[y_offset : y_offset + width, :]
    else:
        cropped = image

    target_w, target_h = TARGET_SIZE
    resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(thumb_path), resized, [int(cv2.IMWRITE_WEBP_QUALITY), 85])

    return thumb_path
