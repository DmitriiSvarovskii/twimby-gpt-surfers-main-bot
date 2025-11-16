from aiogram.filters.callback_data import CallbackData
from typing import Optional


class CartCallbackData(
    CallbackData,
    prefix='main',
    sep='_'
):
    type_press: Optional[str] = None
    account_name: Optional[int] = None
