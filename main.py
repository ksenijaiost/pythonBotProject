import os
import logging
import telebot.types as types
from bot_instance import bot
import handlers.admin
import handlers.user
import handlers.contest_handlers
import handlers.guide_handlers
import handlers.message_handlers
import handlers.news_handlers
import handlers.common_handlers
import handlers.admin_contest_handlers
import handlers.admin_user_handlers
import database.db_classes
from database.db_classes import user_content_storage
from handlers.envParams import admin_ids
from menu.constants import ButtonCallback
from menu.menu import Menu
from services.user_service import UserService

# Настройка логирования
logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,  # Уменьшаем уровень для производительности
)


# После нажатия старт - проверка в списке админов, выдача меню админа или пользователя
@bot.message_handler(commands=["start"])
def start(message):
    try:
        logger = logging.getLogger(__name__)
        logger.debug(f"Start command from user: {message.from_user.id}")

        # Принудительный сброс состояний
        user_id = message.from_user.id
        bot.delete_state(user_id)
        user_content_storage.clear(user_id)

        # Проверка администратора
        if UserService.is_admin(user_id):
            logger.debug(f"Admin detected - {user_id}")
            main_menu = Menu.adm_menu()
            welcome_text = "Добро пожаловать, администратор👑"
        else:
            logger.debug(f"Regular user detected - {user_id}")
            main_menu = Menu.user_menu()
            welcome_text = "Добро пожаловать😊"

        bot.send_message(
            message.chat.id,
            f"✨ {welcome_text}\nВыберите действие:",
            parse_mode="MarkdownV2",
            reply_markup=main_menu,
        )

    except Exception as e:
        logger.error(f"Start command error: {str(e)}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка\nПопробуйте еще раз",
            reply_markup=types.ReplyKeyboardRemove(),
        )


# Обработчик кнопки "В главное меню" - проверка в списке админов, выдача меню админа или пользователя
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.MAIN_MENU)
def handle_back(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    if UserService.is_admin(call.from_user.id):
        main_menu = Menu.adm_menu()
    else:
        main_menu = Menu.user_menu()
    bot.edit_message_text(
        "Главное меню\nВыберите действие::",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu,
    )


def start_polling():
    """Запуск бота в режиме polling (для разработки)"""
    print("Запуск бота в режиме polling...")
    bot.infinity_polling(allowed_updates=["message", "callback_query"])

def start_webhook():
    """Запуск бота в режиме webhook (для продакшена)"""
    from webhook_server import start_webhook_server
    print("Запуск бота в режиме webhook...")
    start_webhook_server()

if __name__ == "__main__":
    # Проверяем режим запуска из переменных окружения
    mode = os.getenv("BOT_MODE", "polling").lower()
    
    if mode == "webhook":
        start_webhook()
    else:
        start_polling()
