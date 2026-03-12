from typing import List, Optional

from pydantic import BaseModel


class ImportResponse(BaseModel):
    imported: List[str]
    skipped: List[str]


class MonthGroup(BaseModel):
    group: str        # e.g. "2025-3"
    year: int
    month: int
    count: int
    thumb_url: str    # URL path for the first image thumbnail


class YearGroup(BaseModel):
    year: int
    months: List[MonthGroup]


class DateViewResponse(BaseModel):
    years: List[YearGroup]


class DateItem(BaseModel):
    type: str              # "image" or "album"
    name: str              # bare filename or sub-directory name
    thumb_url: str         # /thumbnails/<hash>.jpg
    count: Optional[int] = None  # total images inside an album


class DateItemsResponse(BaseModel):
    date_group: str
    items: List[DateItem]
