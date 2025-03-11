import logging
from datetime import datetime

from telebot.handler_backends import State, StatesGroup  # Импорт состояний

from database.contest import ContestManager
from handlers.envParams import admin_ids
from bot_instance import bot
from menu.constants import ButtonCallback
from menu.menu import Menu

logging.basicConfig(level=logging.DEBUG)


class AdminStates(StatesGroup):
    theme = State()
    description = State()
    start_date = State()
    end_date = State()


# Обработчик кнопки "Обновить информацию" в админ-меню
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_INFO)
def start_contest_update(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    if call.message.chat.id not in admin_ids:
        bot.send_message(call.message.chat.id, "Упс, ты не админ!")
        return

    bot.set_state(call.from_user.id, AdminStates.theme, call.message.chat.id)
    bot.send_message(call.message.chat.id, "Введите тему конкурса:")


# Шаги ввода данных
@bot.message_handler(state=AdminStates.theme)
def process_theme(message):
    logging.debug(f"Processing theme: {message.text}")
    bot.set_state(message.from_user.id, AdminStates.description, message.chat.id)
    bot.send_message(message.chat.id, "Теперь введите описание конкурса:")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['theme'] = message.text


@bot.message_handler(state=AdminStates.description)
def process_description(message):
    logging.debug(f"Processing description: {message.text}")
    bot.set_state(message.from_user.id, AdminStates.start_date, message.chat.id)
    bot.send_message(message.chat.id, "Введите дату начала (ДД.ММ.ГГГГ):")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['description'] = message.text


@bot.message_handler(state=AdminStates.start_date)
def process_start_date(message):
    logging.debug(f"Processing start_date: {message.text}")
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        bot.set_state(message.from_user.id, AdminStates.end_date, message.chat.id)
        bot.send_message(message.chat.id, "Введите дату окончания (ДД.ММ.ГГГГ):")
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['start_date'] = message.text
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат даты! Используйте ДД.ММ.ГГГГ")


@bot.message_handler(state=AdminStates.end_date)
def process_end_date(message):
    logging.debug(f"Processing end_date: {message.text}")
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['end_date'] = message.text

            # Сохраняем в БД
            ContestManager.update_contest(
                data['theme'],
                data['description'],
                data['start_date'],
                data['end_date']
            )

        bot.delete_state(message.from_user.id, message.chat.id)
        bot.send_message(message.chat.id, "✅ Информация о конкурсе обновлена!")
        bot.send_message(message.chat.id, "Меню конкурсов. Выберите действие:", reply_markup=Menu.adm_contests_menu())

    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат даты! Используйте ДД.ММ.ГГГГ")
