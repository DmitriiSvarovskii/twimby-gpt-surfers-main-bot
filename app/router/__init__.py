from aiogram import Router

from .academy import router as academy_router
from .ai_photoshoot import router as ai_photoshoot_router
from .ai_testing import router as ai_testing_router
from .ask_question import router as ask_question_router
from .corporate import router as corporate_router
from .education_info import router as education_info_router
from .experts import router as experts_router
from .lead_form import router as lead_form_router
from .pricing import router as pricing_router
from .program_view import router as program_view_router
from .start import router as start_router
from .webinar_register import router as webinar_register_router
from .webinar import router as webinar_router
from .navigation import router as navigation_router

router = Router(name=__name__)

router.include_routers(
    start_router,
    academy_router,
    ai_photoshoot_router,
    ai_testing_router,
    ask_question_router,
    corporate_router,
    education_info_router,
    experts_router,
    lead_form_router,
    pricing_router,
    program_view_router,
    webinar_register_router,
    navigation_router,
    webinar_router,
)
