import logging
import time
from telebot import types
from bot_instance import bot
from logging.handlers import RotatingFileHandler
import threading
from queue import Queue
import handlers.admin
import handlers.user
import database.db_classes
from database.db_classes import user_content_storage
from handlers.envParams import admin_ids
from menu.constants import ButtonCallback, MenuTexts
from menu.menu import Menu

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(
    "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"  # 5 MB
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

task_queue = Queue()


def worker():
    while True:
        task = task_queue.get()
        try:
            task()
        except Exception as e:
            logger.error(f"Task failed: {e}")
        task_queue.task_done()


# Запустите 4 рабочих потока
for _ in range(4):
    threading.Thread(target=worker, daemon=True).start()


# После нажатия старт - проверка в списке админов, выдача меню админа или пользователя
@bot.message_handler(commands=["start"])
def start(message):
    task_queue.put(lambda: _start_handler(message))

def _start_handler(message):
    try:
        logger = logging.getLogger(__name__)
        logger.debug(f"Start command from user: {message.from_user.id}")

        # Принудительный сброс состояний
        user_id = message.from_user.id
        bot.delete_state(user_id)
        user_content_storage.clear(user_id)

        # Проверка администратора
        if message.from_user.id in admin_ids:
            logger.debug(f"Admin detected - {user_id}")
            main_menu = Menu.adm_menu()
            welcome_text = MenuTexts.ADMIN_WELCOME
        else:
            logger.debug(f"Regular user detected - {user_id}")
            main_menu = Menu.user_menu()
            welcome_text = MenuTexts.USER_WELCOME

        bot.send_message(
            message.chat.id,
            welcome_text,
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
    try:
        start_time = time.monotonic()
        
        # Кэшированный ответ
        menu = Menu.adm_menu() if call.message.chat.id in admin_ids else Menu.user_menu()
        text = "Главное меню\nВыберите действие:"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=menu
        )
        
        logger.debug(f"Menu rendered in {time.monotonic() - start_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Menu error: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка обновления меню")


if __name__ == "__main__":
    logger.info("Starting bot in production mode")
    bot.infinity_polling(
        allowed_updates=["message", "callback_query"],
        request_timeout=30,
        none_stop=True
    )
