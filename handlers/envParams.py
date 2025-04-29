import os
from typing import Optional
from dotenv import load_dotenv
from functools import lru_cache

# Загружаем переменные из .env
load_dotenv()


def get_env_var(name: str, required: bool = True) -> Optional[str]:
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"Переменная окружения {name} обязательна!")
    return value


def check_digit(name: str, value):
    if not value or not value.lstrip("-").isdigit():
        raise ValueError(f"{name} должен быть числовым ID чата!")


# Получаем список админов
@lru_cache(maxsize=None)
def get_admins():
    return set(map(int, os.getenv("ADMIN_ID_LIST", "").split(",")))


# Получаем список работников газеты
@lru_cache(maxsize=None)
def get_news_workers():
    return set(map(int, os.getenv("NEWS_ID_LIST", "").split(",")))


CHAT_ID = get_env_var("CHAT_ID")
check_digit("CHAT_ID", CHAT_ID)
ADMIN_CHAT_ID = get_env_var("ADMIN_CHAT_ID")
check_digit("ADMIN_CHAT_ID", ADMIN_CHAT_ID)
CONTEST_CHAT_ID = get_env_var("CONTEST_CHAT_ID")
check_digit("CONTEST_CHAT_ID", CONTEST_CHAT_ID)
NEWSPAPER_CHAT_ID = get_env_var("NEWSPAPER_CHAT_ID")
check_digit("NEWSPAPER_CHAT_ID", NEWSPAPER_CHAT_ID)

CHAT_USERNAME = get_env_var("CHAT_USERNAME").lstrip("@")
ADMIN_USERNAME = get_env_var("ADMIN_USERNAME")
