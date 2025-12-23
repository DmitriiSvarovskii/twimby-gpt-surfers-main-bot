from aiogram import Router

from .main import router as main_router
from .fsm_broadcast import router as fsm_broadcast_router
from .fsm_webinar import router as fsm_webinar_router
from .fsm_webinars_edit import router as fsm_webinars_edit_router


router = Router(name=__name__)

router.include_routers(
    main_router,
    fsm_broadcast_router,
    fsm_webinar_router,
    fsm_webinars_edit_router,
)
