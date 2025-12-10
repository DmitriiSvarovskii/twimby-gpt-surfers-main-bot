from aiogram import Router, types, F

from app.lexicon import lead_form as lead_lexicon
from app.button.factory import build_inline_kb

router = Router()


@router.callback_query(F.data == "leave_request")
async def open_leave_request(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        lead_lexicon.TEXTS["leave_request_intro"],
        reply_markup=build_inline_kb("leave_request"),
    )
    await callback.answer()


@router.callback_query(F.data == "lead_share_contact")
async def lead_share_contact(callback: types.CallbackQuery):
    # сюда подвяжешь сбор контактов
    await callback.answer("Ок, отправь, пожалуйста, контактные данные.", show_alert=True)
