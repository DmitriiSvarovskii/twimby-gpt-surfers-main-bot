from aiogram import Router

from .main import router as main_router
from .fsm_broadcast import router as fsm_broadcast_router


router = Router(name=__name__)

router.include_routers(
    main_router,
    fsm_broadcast_router,
)
