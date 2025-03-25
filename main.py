import logging
from bot_instance import bot
import handlers.admin
import handlers.user
import database.contest
from handlers.envParams import admin_ids
from menu.constants import ButtonCallback
from menu.menu import Menu

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# После нажатия старт - проверка в списке админов, выдача меню админа или пользователя
@bot.message_handler(commands=['start'])
def start(message):
    logger = logging.getLogger(__name__)
    logger.info(f"Received callback: {message}, chat_id: {message.chat.id}")
    if message.chat.id in admin_ids:
        main_menu = Menu.adm_menu()
        welcome_text = "Добро пожаловать, администратор! 👑"
    else:
        main_menu = Menu.user_menu()
        welcome_text = "Добро пожаловать! 😊"

    bot.send_message(
        message.chat.id,
        f"✨ {welcome_text}\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=main_menu
    )


# Обработчик кнопки "В главное меню" - проверка в списке админов, выдача меню админа или пользователя
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.MAIN_MENU)
def handle_back(call):
    logger = logging.getLogger(__name__)
    logger.info(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    if call.message.chat.id in admin_ids:
        main_menu = Menu.adm_menu()
    else:
        main_menu = Menu.user_menu()
    bot.edit_message_text(
        "Главное меню. Выберите действие::",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu
    )


if __name__ == '__main__':
    bot.infinity_polling(allowed_updates=['message', 'callback_query'])
