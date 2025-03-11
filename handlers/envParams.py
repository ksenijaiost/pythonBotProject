import os

from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Получаем список админов
admin_ids = list(map(int, os.getenv("ADMIN_ID_LIST", "").split(","))) if os.getenv("ADMIN_ID_LIST") else []