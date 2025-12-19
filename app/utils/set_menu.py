from aiogram import Bot
from aiogram.types import BotCommand
from aiogram.types.bot_command_scope_all_private_chats import BotCommandScopeAllPrivateChats
from app.lexicon import LEXICON_COMMANDS_RU


async def create_set_main_menu(bot: Bot):
    commands = [BotCommand(command=k, description=v) for k, v in LEXICON_COMMANDS_RU.items()]

    await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats(), language_code="ru")
    await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats(), language_code="ru")

    # контроль
    return await bot.get_my_commands(scope=BotCommandScopeAllPrivateChats(), language_code="ru")
# async def create_set_main_menu(bot: Bot):
#     main_menu_commands = [
#         BotCommand(
#             command=command,
#             description=description
#         )
#         for command, description in LEXICON_COMMANDS_RU.items()
#     ]
#     await bot.set_my_commands(main_menu_commands)
