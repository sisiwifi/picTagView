from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from app.core.config import TEMP_DIR


TARGET_SIZE: Tuple[int, int] = (300, 200)


def create_thumbnail_from_bytes(content: bytes, file_hash: str) -> Path:
    thumb_name = f"{file_hash}.jpg"
    thumb_path = TEMP_DIR / thumb_name

    if thumb_path.exists():
        return thumb_path

    image_array = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image data")

    target_width, target_height = TARGET_SIZE
    height, width = image.shape[:2]
    target_ratio = target_width / target_height
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        x_offset = (width - new_width) // 2
        cropped = image[:, x_offset : x_offset + new_width]
    else:
        new_height = int(width / target_ratio)
        y_offset = (height - new_height) // 2
        cropped = image[y_offset : y_offset + new_height, :]

    resized = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(thumb_path), resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

    return thumb_path
