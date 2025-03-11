import os

from dotenv import load_dotenv

load_dotenv()


class Links:
    @staticmethod
    def get_chat_url():
        raw_username = os.getenv("CHAT_ID")

        if not raw_username:
            raise ValueError("CHAT_ID отсутствует в .env!")

        username = raw_username.lstrip("@")

        if not username.isalnum() or len(username) < 5:
            raise ValueError("Некорректный CHAT_ID! Пример: @my_chat")

        return f"https://t.me/{username}"

    @staticmethod
    def get_nin_chat_url():
        raw_username = os.getenv("NINTENDO_CHAT")

        if not raw_username:
            raise ValueError("NINTENDO_CHAT отсутствует в .env!")

        username = raw_username.lstrip("@")

        if not username.isalnum() or len(username) < 5:
            raise ValueError("Некорректный NINTENDO_CHAT! Пример: @my_chat")

        return f"https://t.me/{username}"

    @staticmethod
    def get_channel_url():
        raw_username = os.getenv("CHANNEL")

        if not raw_username:
            raise ValueError("CHANNEL отсутствует в .env!")

        username = raw_username.lstrip("@")

        if not username.isalnum() or len(username) < 5:
            raise ValueError("Некорректный CHANNEL! Пример: @my_chat")

        return f"https://t.me/{username}"
