import enum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User
from app.model.webinar import WebinarRegistration


class WebinarRegistrationStatus(str, enum.Enum):
    registered = "registered"


async def register_user_for_webinar(
    *,
    session: AsyncSession,
    tg_id: int,
    webinar_id: int,
    name: str | None = None,
    nick: str | None = None,
    email: str | None = None,
) -> WebinarRegistration:
    # 1) найти пользователя
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = res.scalar_one_or_none()
    if user is None:
        raise RuntimeError("User not found")

    # 2) upsert регистрации (чтобы не падать на unique user_id+webinar_id)
    res = await session.execute(
        select(WebinarRegistration).where(
            WebinarRegistration.user_id == user.id,
            WebinarRegistration.webinar_id == webinar_id,
        )
    )
    reg = res.scalar_one_or_none()

    if reg is None:
        reg = WebinarRegistration(
            user_id=user.id,
            webinar_id=webinar_id,
            status=WebinarRegistrationStatus.registered,
        )
        session.add(reg)
    else:
        reg.status = WebinarRegistrationStatus.registered

    # (если хочешь хранить name/nick/email — нужно добавить поля в модель и миграцию)

    await session.commit()
    return reg
