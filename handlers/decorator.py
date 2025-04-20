from telebot import types


# Декоратор проверки приватности чата
def private_chat_only(bot_instance):
    def decorator(func):
        def wrapper(message_or_call, *args, **kwargs):
            # Определяем тип сообщения
            if isinstance(message_or_call, types.CallbackQuery):
                chat = message_or_call.message.chat
                answer = lambda: bot_instance.answer_callback_query(
                    message_or_call.id, "ℹ️ Используйте бота в личных сообщениях"
                )
            else:
                chat = message_or_call.chat
                answer = lambda: None

            # Проверяем тип чата
            if chat.type != "private":
                answer()
                return

            return func(message_or_call, *args, **kwargs)

        return wrapper

    return decorator
