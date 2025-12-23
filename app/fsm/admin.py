from aiogram.fsm.state import StatesGroup, State


class BroadcastStates(StatesGroup):
    choose_audience = State()
    choose_webinar = State()
    waiting_content = State()
    confirm = State()
    ready = State()


class WebinarCreateStates(StatesGroup):
    title = State()
    description_small = State()
    description_full = State()
    date = State()
    time = State()
    confirm = State()
