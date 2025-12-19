
import datetime

from typing import TYPE_CHECKING
from sqlalchemy import (
    BIGINT,
    Boolean,
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import (
    Base, intpk
)

if TYPE_CHECKING:
    from app.model.webinar import WebinarRegistration


class User(Base):
    __tablename__ = "users"

    id: Mapped[intpk]

    # Telegram
    tg_id: Mapped[int] = mapped_column(BIGINT, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Meta
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),   # дефолт "текущее время" на стороне БД
        nullable=False,
    )

    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",      # для Postgres ок
        nullable=False,
    )

    # Флаги генерации аватарок
    welcome_photo_generated: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
    )
    subbscribed_photo_generated: Mapped[bool] = mapped_column(  # оставляю твоё имя, но лучше: subscribed_
        Boolean,
        server_default="false",
        nullable=False,
    )

    # Relationships
    webinar_registrations: Mapped[list["WebinarRegistration"]] = relationship(
        "WebinarRegistration",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
