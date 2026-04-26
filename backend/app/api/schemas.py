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
    category_id: Optional[int] = None
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
    media_index: Optional[int] = None
    media_rel_path: Optional[str] = None


class DateItemsResponse(BaseModel):
    date_group: str
    items: List[DateItem]


# ── Cache generation ──────────────────────────────────────────────────────────

class CacheRequest(BaseModel):
    image_ids: List[int] = Field(default_factory=list)
    ordered_image_ids: List[int] = Field(default_factory=list)
    generation: Optional[int] = None
    page_token: Optional[str] = None
    sort_signature: Optional[str] = None
    direction: str = "none"
    anchor_image_id: Optional[int] = None
    anchor_item_key: Optional[str] = None
    anchor_offset: float = 0.0


class CacheStartResponse(BaseModel):
    task_id: str
    generation: Optional[int] = None


class CacheStatusItem(BaseModel):
    id: int
    cache_thumb_url: Optional[str] = None


class CacheStatusResponse(BaseModel):
    status: str                  # "running" | "done" | "error"
    items: List[CacheStatusItem] = Field(default_factory=list)
    next_cursor: int = 0
    generation: Optional[int] = None


class ImageMetaItem(BaseModel):
    id: int
    name: str
    category_id: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    imported_at: Optional[datetime] = None
    file_created_at: Optional[datetime] = None
    tags: List[int] = Field(default_factory=list)
    thumb_url: str = ""
    cache_thumb_url: Optional[str] = None
    media_paths: List[str] = Field(default_factory=list)


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


class PageConfigRequest(BaseModel):
    browse_mode: str = "scroll"


class PageConfigResponse(BaseModel):
    browse_mode: str
    default_browse_mode: str = "scroll"


class TagMatchSettingRequest(BaseModel):
    enabled: bool = True
    noise_tokens: List[str] = Field(default_factory=list)
    min_token_length: int = 2
    drop_numeric_only: bool = True


class TagMatchSettingResponse(BaseModel):
    enabled: bool
    noise_tokens: List[str] = Field(default_factory=list)
    min_token_length: int
    drop_numeric_only: bool
    sort_mode: str = "name_asc"


class ImageTagMatchRequest(BaseModel):
    image_ids: List[int] = Field(default_factory=list)
    apply: bool = True
    merge_mode: str = "append_unique"
    include_tokens: bool = False


class TagBriefItem(BaseModel):
    id: int
    name: str
    display_name: str = ""
    color: str = ""
    border_color: str = ""
    background_color: str = ""


class ImageTagMatchItem(BaseModel):
    image_id: int
    filename: str = ""
    tokens: List[str] = Field(default_factory=list)
    matched_tag_ids: List[int] = Field(default_factory=list)
    matched_tags: List[TagBriefItem] = Field(default_factory=list)
    before_tag_ids: List[int] = Field(default_factory=list)
    after_tag_ids: List[int] = Field(default_factory=list)
    changed: bool = False


class ImageTagMatchResponse(BaseModel):
    items: List[ImageTagMatchItem] = Field(default_factory=list)
    common_tag_ids: List[int] = Field(default_factory=list)
    common_tags: List[TagBriefItem] = Field(default_factory=list)
    multi_display: str = "empty"
    applied_count: int = 0


class ImageTagApplyRequest(BaseModel):
    image_ids: List[int] = Field(default_factory=list)
    tag_ids: List[int] = Field(default_factory=list)
    merge_mode: str = "append_unique"


class ImageTagApplyItem(BaseModel):
    image_id: int
    before_tag_ids: List[int] = Field(default_factory=list)
    after_tag_ids: List[int] = Field(default_factory=list)
    changed: bool = False


class ImageTagApplyResponse(BaseModel):
    items: List[ImageTagApplyItem] = Field(default_factory=list)
    common_tag_ids: List[int] = Field(default_factory=list)
    common_tags: List[TagBriefItem] = Field(default_factory=list)
    multi_display: str = "empty"
    applied_count: int = 0


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
    category_id: Optional[int] = None
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
    media_index: Optional[int] = None
    media_rel_path: Optional[str] = None


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


# ── Trash views ───────────────────────────────────────────────────────────────

class TrashTargetRef(BaseModel):
    type: str
    image_id: Optional[int] = None
    media_rel_path: Optional[str] = None
    album_path: Optional[str] = None


class TrashMoveRequest(BaseModel):
    items: List[TrashTargetRef]


class TrashRestoreRequest(BaseModel):
    entry_ids: List[int]


class TrashHardDeleteRequest(BaseModel):
    entry_ids: List[int]


class TrashItem(BaseModel):
    id: int
    entry_key: str
    type: str
    name: str
    category_id: Optional[int] = None
    thumb_url: str = ""
    cache_thumb_url: Optional[str] = None
    trash_media_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sort_ts: Optional[int] = None
    tags: List[int] = Field(default_factory=list)
    file_size: Optional[int] = None
    imported_at: Optional[datetime] = None
    file_created_at: Optional[datetime] = None
    photo_count: Optional[int] = None
    created_at: Optional[datetime] = None
    original_path: Optional[str] = None


class TrashListResponse(BaseModel):
    items: List[TrashItem]


class TrashActionResult(BaseModel):
    moved: int = 0
    restored: int = 0
    deleted: int = 0
    skipped: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
