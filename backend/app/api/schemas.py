from typing import List

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
