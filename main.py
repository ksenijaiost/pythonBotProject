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

kb = types.ReplyKeyboardMarkup(row_width=2)
button1 = types.KeyboardButton(ButtonText.USER_GUIDES)
button2 = types.KeyboardButton(ButtonText.USER_CONTEST)
kb.add(button1, button2)

ikb = types.InlineKeyboardMarkup(row_width=2)
button1 = types.InlineKeyboardButton(ButtonText.USER_GUIDES, callback_data='good')
button2 = types.InlineKeyboardButton(ButtonText.USER_CONTEST, callback_data='bad')
ikb.add(button1,button2)


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Hello World!", reply_markup=kb)


@bot.message_handler(content_types=['text'])
def handler(message):
    if message.text == ButtonText.USER_GUIDES:
        bot.send_message(message.chat.id, "Тут будут гайды", reply_markup=ikb)
    if message.text == ButtonText.USER_CONTEST:
        bot.send_message(message.chat.id, "Тут будет всё о конкурсах", reply_markup=ikb)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            if call.data == "good":
                bot.send_message(call.message.chat.id, "Тык")
            if call.data == "bad":
                bot.send_message(call.message.chat.id, "Тык Тык")
    except Exception as e:
        print(repr(e))


bot.polling(none_stop=True)
