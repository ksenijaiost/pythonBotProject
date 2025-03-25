import os

from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Получаем список админов
admin_ids = list(map(int, os.getenv("ADMIN_ID_LIST", "").split(","))) if os.getenv("ADMIN_ID_LIST") else []

CONTEST_CHAT_ID = os.getenv("CONTEST_CHAT_ID")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
CHAT_ID = os.getenv("CHAT_ID")
if not CONTEST_CHAT_ID or not CONTEST_CHAT_ID.lstrip('-').isdigit():
    raise ValueError("CONTEST_CHAT_ID должен быть числовым ID чата!")
CHAT_USERNAME = os.getenv("CHAT_USERNAME").lstrip("@")