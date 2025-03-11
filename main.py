import os
import telebot
from dotenv import load_dotenv  # Импортируем функцию для загрузки переменных

from constants import ButtonText, ButtonCallback
from menu import Menu

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден в .env!")

bot = telebot.TeleBot(TOKEN)

# Получаем список админов
admin_ids = list(map(int, os.getenv("ADMIN_ID_LIST", "").split(","))) if os.getenv("ADMIN_ID_LIST") else []


# После нажатия старт - проверка в списке админов, выдача меню админа или пользователя
@bot.message_handler(commands=['start'])
def start(message):
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


# Обработчик кнопки "В главное меню"
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.MAIN_MENU)
def handle_back(call):
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


# Обработчик кнопки "Гайды"
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_GUIDES)
def handle_user_guides(call):
    bot.edit_message_text(
        "Меню гайдов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu()
    )


bot.polling(none_stop=True)
