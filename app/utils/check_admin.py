from app.config import settings


def is_admin(tg_id: int) -> bool:
    return tg_id in set(settings.ADMIN_TG_IDS)
