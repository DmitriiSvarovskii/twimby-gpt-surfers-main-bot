BUTTONS = {
    "ai_photoshoot": [
        {"text": "❄️ Зимняя сказка", "callback": "ai_ps_cat:winter"},
        {"text": "🏄 Серфинг", "callback": "ai_ps_cat:surf"},
        {"text": "🐾 С животными", "callback": "ai_ps_cat:animals"},
        {"text": "🌍 Путешествия", "callback": "ai_ps_cat:travel"},
        {"text": "💼 Деловой", "callback": "ai_ps_cat:business"},
        {"text": " Главное меню", "callback": "ai_ps_back_to_menu"},
    ],

    "ai_photoshoot_gender": [
        {"text": "🙋‍♂️ Мужской", "callback": "ai_ps_gender:male"},
        {"text": "🙋‍♀️ Женский", "callback": "ai_ps_gender:female"},
        {"text": "⬅️ Назад", "callback": "ai_ps_back_categories"},
        {"text": "🏠 В главное меню", "callback": "ai_ps_back_to_menu"},
    ],

    "ai_photoshoot_upload": [
        {"text": "✅ Сгенерировать", "callback": "ai_ps_generate"},
        {"text": "⬅️ Назад", "callback": "ai_ps_back_categories"},
        {"text": "🏠 В главное меню", "callback": "ai_ps_back_to_menu"},
    ],

    "ai_photoshoot_after": [
        {"text": "🔁 Перегенерировать", "callback": "ai_ps_regenerate"},
        {"text": "🏠 В главное меню", "callback": "ai_ps_back_to_menu"},
    ],

    "ai_photoshoot_gate": [
        {"text": "📌 Подписаться", "url": "https://t.me/your_channel"},  # заменишь
        {"text": "✅ Проверить подписку", "callback": "ai_ps_check_sub"},
        {"text": "🏠 В главное меню", "callback": "ai_ps_back_to_menu"},
    ],
}
