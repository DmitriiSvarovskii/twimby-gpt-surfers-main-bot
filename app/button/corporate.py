BUTTONS = {
    "corporate": [
        {"text": "Оставить заявку", "callback": "corporate_request"},
        {"text": "Задать вопрос", "callback": "ask_question"},
        {"text": "Назад", "callback": "corporate_back"},
    ]
}


# def build_corporate_keyboard() -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="Оставить заявку", callback_data="corporate_request")],
#             [InlineKeyboardButton(text="Назад", callback_data="corporate_back")],
#         ]
#     )
