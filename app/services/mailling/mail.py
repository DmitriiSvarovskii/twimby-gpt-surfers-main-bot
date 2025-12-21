from sqlalchemy import update
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.user import User
from app.model.webinar import WebinarRegistration


async def get_recipients_all(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(User.tg_id).where(User.is_blocked.is_(False))
    )
    return [r[0] for r in rows.all()]


async def get_recipients_by_webinar(session: AsyncSession, webinar_id: int) -> list[int]:
    rows = await session.execute(
        select(distinct(User.tg_id))
        .join(WebinarRegistration, WebinarRegistration.user_id == User.id)
        .where(
            WebinarRegistration.webinar_id == webinar_id,
            User.is_blocked.is_(False),
        )
    )
    return [r[0] for r in rows.all()]


async def mark_blocked(session: AsyncSession, tg_id: int) -> None:
    await session.execute(
        update(User).where(User.tg_id == tg_id).values(is_blocked=True)
    )
    await session.commit()
