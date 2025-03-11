import os
import telebot
from telebot import types
from dotenv import load_dotenv  # Импортируем функцию для загрузки переменных

from constants import ButtonText

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден в .env!")

bot = telebot.TeleBot(TOKEN)

user_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
menu_button1 = types.KeyboardButton(ButtonText.USER_GUIDES)
menu_button2 = types.KeyboardButton(ButtonText.USER_CONTEST)
user_menu.add(menu_button1, menu_button2)

guides_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
guides_button1 = types.KeyboardButton(ButtonText.USER_GUIDE_SITE)
guides_button2 = types.KeyboardButton(ButtonText.USER_FIND_GUIDE)
guides_button3 = types.KeyboardButton(ButtonText.USER_MENU)
guides_menu.add(guides_button1, guides_button2, guides_button3)

contests_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
contests_button1 = types.KeyboardButton(ButtonText.USER_CONTEST_INFO)
contests_button2 = types.KeyboardButton(ButtonText.USER_CONTEST_SEND)
contests_button3 = types.KeyboardButton(ButtonText.USER_CONTEST_JUDGE)
contests_button4 = types.KeyboardButton(ButtonText.USER_MENU)
contests_menu.add(contests_button1, contests_button2, contests_button3, contests_button4)


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Hello World!", reply_markup=user_menu)


@bot.message_handler(content_types=['text'])
def handler(message):
    if message.text == ButtonText.USER_GUIDES:
        bot.send_message(message.chat.id, "Тут будут гайды", reply_markup=guides_menu)
    if message.text == ButtonText.USER_CONTEST:
        bot.send_message(message.chat.id, "Тут будет всё о конкурсах", reply_markup=contests_menu)
    if message.text == ButtonText.USER_MENU:
        bot.send_message(message.chat.id, "Вы в главном меню", reply_markup=user_menu)


bot.polling(none_stop=True)
