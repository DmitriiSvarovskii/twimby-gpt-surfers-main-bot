from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
import datetime
from typing import TYPE_CHECKING
from app.db.postgres import (
    Base, intpk
)

if TYPE_CHECKING:
    from app.model.user import User


class Webinar(Base):
    __tablename__ = "webinars"

    id: Mapped[intpk]

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description_small: Mapped[str] = mapped_column(String(1024), nullable=False)
    description_full: Mapped[str] = mapped_column(Text, nullable=False)

    date_stream: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
    )

    # на будущее — платные вебинары
    is_free: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
    )
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    registrations: Mapped[list["WebinarRegistration"]] = relationship(
        "WebinarRegistration",
        back_populates="webinar",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WebinarRegistrationStatus(str, enum.Enum):
    registered = "registered"
    cancelled = "cancelled"
    attended = "attended"   # опционально
    no_show = "no_show"     # опционально


class WebinarRegistration(Base):
    __tablename__ = "webinar_registrations"

    id: Mapped[intpk]

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    webinar_id: Mapped[int] = mapped_column(
        ForeignKey("webinars.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[WebinarRegistrationStatus] = mapped_column(
        Enum(WebinarRegistrationStatus, name="webinar_registration_status"),
        default=WebinarRegistrationStatus.registered,
        nullable=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="webinar_registrations")
    webinar: Mapped["Webinar"] = relationship("Webinar", back_populates="registrations")
    __table_args__ = (
        UniqueConstraint("user_id", "webinar_id", name="uq_reg_user_webinar"),
        Index("ix_reg_user_id", "user_id"),
        Index("ix_reg_webinar_id", "webinar_id"),
        Index("ix_reg_status", "status"),
    )
