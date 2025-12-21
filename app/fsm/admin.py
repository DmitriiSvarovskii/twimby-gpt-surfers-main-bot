from aiogram.fsm.state import StatesGroup, State


class BroadcastStates(StatesGroup):
    choose_audience = State()
    choose_webinar = State()
    waiting_content = State()
    confirm = State()
    ready = State()
