import os
import logging

import telebot
from dotenv import load_dotenv
from telebot.storage import StateMemoryStorage  # Импорт хранилища состояний

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден в .env!")

# Создаем бота с оптимизированными настройками
bot = telebot.TeleBot(
    TOKEN, 
    state_storage=StateMemoryStorage(),
    threaded=True,  # Включаем многопоточность
    num_threads=10,  # Количество потоков для обработки
    skip_pending=True  # Пропускаем старые обновления при запуске
)

# Настройка логирования для бота
logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,  # Уменьшаем уровень логирования для производительности
)
