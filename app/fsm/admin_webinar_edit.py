from aiogram.fsm.state import StatesGroup, State


class WebinarEditStates(StatesGroup):
    waiting_title = State()
    waiting_desc_small = State()
    waiting_desc_full = State()
    waiting_date = State()
    waiting_time = State()
    confirm = State()
