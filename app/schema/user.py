from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: dt.datetime
    is_blocked: bool
    welcome_photo_generated: bool
    subbscribed_photo_generated: bool
