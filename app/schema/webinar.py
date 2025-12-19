from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class WebinarDTO(BaseModel):
    id: int
    title: str
    description_small: str
    description_full: str
    date_stream: datetime
    is_active: bool = True
    is_free: bool = True
    price: int | None = None


class WebinarListItemDTO(BaseModel):
    id: int
    title: str
    description_small: str
    date_stream: datetime
    is_free: bool = True
    price: int | None = None
