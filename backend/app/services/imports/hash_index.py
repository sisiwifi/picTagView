import json
from typing import Optional

from sqlmodel import select

from app.core.config import MEDIA_DIR
from app.db.session import get_session
from app.models.image_asset import ImageAsset

_HASH_INDEX_PATH = MEDIA_DIR / ".hash_index.json"
_hash_index: Optional[dict[str, int]] = None
_quick_hash_index: Optional[dict[str, str]] = None


def load_hash_index() -> None:
    global _hash_index, _quick_hash_index
    if _hash_index is not None:
        return
    if _HASH_INDEX_PATH.exists():
        try:
            raw = json.loads(_HASH_INDEX_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "hash_to_id" in raw:
                _hash_index = raw["hash_to_id"]
                _quick_hash_index = raw.get("quick_to_hash", {})
            else:
                _hash_index = raw if isinstance(raw, dict) else {}
                _quick_hash_index = {}
        except Exception:
            _hash_index = {}
            _quick_hash_index = {}
    else:
        _hash_index = {}
        _quick_hash_index = {}


def save_hash_index() -> None:
    if _hash_index is None:
        return
    try:
        data = {
            "hash_to_id": _hash_index,
            "quick_to_hash": _quick_hash_index or {},
        }
        _HASH_INDEX_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def add_to_hash_index(file_hash: str, image_id: int, quick_hash: Optional[str] = None) -> None:
    global _hash_index, _quick_hash_index
    if _hash_index is None:
        _hash_index = {}
    _hash_index[file_hash] = image_id
    if quick_hash:
        if _quick_hash_index is None:
            _quick_hash_index = {}
        _quick_hash_index[quick_hash] = file_hash


def lookup_hash_index(file_hash: str) -> Optional[int]:
    if _hash_index is None:
        return None
    return _hash_index.get(file_hash)


def lookup_quick_hash(quick_hash: str) -> Optional[str]:
    if _quick_hash_index is None:
        return None
    return _quick_hash_index.get(quick_hash)


def clear_hash_index_memory() -> None:
    global _hash_index, _quick_hash_index
    _hash_index = None
    _quick_hash_index = None


def rebuild_hash_index() -> None:
    global _hash_index, _quick_hash_index
    _hash_index = {}
    _quick_hash_index = {}
    with get_session() as session:
        for asset in session.exec(select(ImageAsset)).all():
            if asset.file_hash and asset.id is not None:
                _hash_index[asset.file_hash] = asset.id
                if asset.quick_hash:
                    _quick_hash_index[asset.quick_hash] = asset.file_hash
    save_hash_index()
