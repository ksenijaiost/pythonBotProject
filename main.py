import os
import telebot
from dotenv import load_dotenv  # Импортируем функцию для загрузки переменных

from constants import ButtonText
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


@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id in admin_ids:
        markup = Menu.adm_menu()
        welcome_text = "Добро пожаловать, администратор! 👑"
    else:
        markup = Menu.user_menu()
        welcome_text = "Добро пожаловать! 😊"

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=markup
    )


@bot.message_handler(content_types=['text'])
def handler(message):
    if message.text == ButtonText.USER_GUIDES:
        bot.send_message(message.chat.id, "Тут будут гайды", reply_markup=Menu.guides_menu())
    if message.text == ButtonText.USER_CONTEST:
        bot.send_message(message.chat.id, "Тут будет всё о конкурсах", reply_markup=Menu.contests_menu())
    if message.text == ButtonText.MAIN_MENU:
        bot.send_message(message.chat.id, "Вы в главном меню", reply_markup=Menu.user_menu())
    if message.text == ButtonText.USER_GUIDE_SITE:
        bot.send_message(message.chat.id, "Наш сайт с гайдами - ", reply_markup=Menu.back_menu())


bot.polling(none_stop=True)
