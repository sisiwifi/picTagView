from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ImportResponse(BaseModel):
    imported: List[str]
    skipped: List[str]


class MonthGroup(BaseModel):
    group: str        # e.g. "2025-3"
    year: int
    month: int
    count: int
    thumb_url: str    # URL path for the first image thumbnail
    cache_thumb_url: Optional[str] = None
    id: Optional[int] = None


class YearGroup(BaseModel):
    year: int
    months: List[MonthGroup]


class DateViewResponse(BaseModel):
    years: List[YearGroup]


class DateItem(BaseModel):
    type: str               # "image" or "album"
    name: str               # bare filename or sub-directory name
    thumb_url: str          # /thumbnails/<hash>.webp (may be empty string)
    count: Optional[int] = None          # total images inside an album
    id: Optional[int] = None             # ImageAsset.id
    cache_thumb_url: Optional[str] = None  # /cache/<hash>_cache.webp when generated
    width: Optional[int] = None
    height: Optional[int] = None
    public_id: Optional[str] = None      # Album.public_id for album items
    album_path: Optional[str] = None     # Album.path for URL routing (e.g. "2024-07/vacation")
    sort_ts: Optional[int] = None        # Unix timestamp for date sorting
    tags: List[int] = Field(default_factory=list)
    file_size: Optional[int] = None
    imported_at: Optional[datetime] = None
    file_created_at: Optional[datetime] = None
    photo_count: Optional[int] = None
    created_at: Optional[datetime] = None


class DateItemsResponse(BaseModel):
    date_group: str
    items: List[DateItem]


# ── Cache generation ──────────────────────────────────────────────────────────

class CacheRequest(BaseModel):
    image_ids: List[int]


class CacheStatusItem(BaseModel):
    id: int
    cache_thumb_url: Optional[str] = None


class CacheStatusResponse(BaseModel):
    status: str                  # "running" | "done" | "error"
    items: List[CacheStatusItem] = []


class ImageMetaItem(BaseModel):
    id: int
    name: str
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    imported_at: Optional[datetime] = None
    file_created_at: Optional[datetime] = None
    tags: List[int] = Field(default_factory=list)
    thumb_url: str = ""
    cache_thumb_url: Optional[str] = None


class ImageMetaResponse(BaseModel):
    items: List[ImageMetaItem]


class ViewerPreferenceRequest(BaseModel):
    viewer_id: Optional[str] = None


class CacheThumbSettingRequest(BaseModel):
    short_side_px: int


class CacheThumbSettingResponse(BaseModel):
    short_side_px: int
    default_short_side_px: int
    min_short_side_px: int
    max_short_side_px: int


class MonthCoverSettingRequest(BaseModel):
    size_px: int


class MonthCoverSettingResponse(BaseModel):
    size_px: int
    default_size_px: int
    min_size_px: int
    max_size_px: int


# ── Album views ───────────────────────────────────────────────────────────────

class BreadcrumbItem(BaseModel):
    public_id: str
    title: str


class AlbumItem(BaseModel):
    type: str                            # "image" or "album"
    name: str
    thumb_url: str = ""
    count: Optional[int] = None
    id: Optional[int] = None             # ImageAsset.id (for images)
    cache_thumb_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    public_id: Optional[str] = None      # Album.public_id (for sub-albums)
    album_path: Optional[str] = None     # Album.path for URL routing
    sort_ts: Optional[int] = None        # Unix timestamp for date sorting
    tags: List[int] = Field(default_factory=list)
    file_size: Optional[int] = None
    imported_at: Optional[datetime] = None
    file_created_at: Optional[datetime] = None
    photo_count: Optional[int] = None
    created_at: Optional[datetime] = None


class AlbumInfo(BaseModel):
    public_id: str
    title: str
    description: Optional[str] = None
    date_group: Optional[str] = None
    photo_count: int = 0
    subtree_photo_count: int = 0
    parent_public_id: Optional[str] = None
    ancestors: List[BreadcrumbItem] = []


class AlbumDetailResponse(BaseModel):
    album: AlbumInfo
    items: List[AlbumItem]
