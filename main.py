from bot_instance import bot
import handlers.admin
import database
from handlers.envParams import admin_ids
from menu.constants import ButtonCallback
from menu.menu import Menu


# После нажатия старт - проверка в списке админов, выдача меню админа или пользователя
@bot.message_handler(commands=['start'])
def start(message):
    print(f"Received callback: {message}, chat_id: {message.chat.id}")
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
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
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


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_GUIDES)
def handle_user_guides(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню гайдов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST)
def handle_user_guides(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.contests_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST_INFO)
def handle_user_guides(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Информация о конкурсе:\n",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.contests_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST)
def handle_adm_contest(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов (адм). Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.adm_contests_menu()
    )


if __name__ == '__main__':
    bot.polling()
