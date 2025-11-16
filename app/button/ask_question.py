
# BUTTONS = {
#     "ask_question": [
#         {"text": "Поделиться контактом", "callback": "ask_share_contact"},
#         {"text": "Пропустить", "callback": "ask_skip_contact"},
#         {"text": "Назад", "callback": "back"},
#     ]
# }


BUTTONS = {
    "ask_question": [
        {"text": "Поделиться контактом", "callback": "send_contact_keyboard"},
        {"text": "Пропустить", "callback": "ask_skip_contact"},
        {"text": "Назад", "callback": "back"},
    ]
}
