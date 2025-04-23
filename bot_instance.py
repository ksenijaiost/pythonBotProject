import os

import telebot
from dotenv import load_dotenv
from telebot.storage import StateMemoryStorage  # Импорт хранилища состояний

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден в .env!")

bot = telebot.TeleBot(TOKEN, state_storage=StateMemoryStorage())
