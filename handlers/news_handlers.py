"""
Обработчики новостей
"""
import logging
from typing import Optional, Dict, Any
import telebot.types as types

from bot_instance import bot
from utils.simple_locks import simple_lock
from utils.markdown_utils import safe_markdown_v2
from handlers.decorator import private_chat_only
from handlers.envParams import NEWSPAPER_CHAT_ID, CHAT_ID
from menu.constants import ButtonCallback, UserState
from database.db_classes import user_content_storage
from services.user_service import UserService

logger = logging.getLogger(__name__)


class NewsHandlers:
    """Класс для обработки новостей"""
    
    @staticmethod
    def is_user_in_chat(user_id: int) -> bool:
        """
        Проверка, состоит ли пользователь в чате
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если состоит в чате
        """
        try:
            chat_member = bot.get_chat_member(CHAT_ID, user_id)
            return chat_member.status not in ["left", "kicked"]
        except Exception as e:
            logger.error(f"Error checking chat membership: {e}")
            return False
    
    @staticmethod
    def handle_news_menu(call):
        """Обработка меню новостей"""
        try:
            user_id = call.from_user.id
            
            # Проверяем, состоит ли пользователь в чате
            if not NewsHandlers.is_user_in_chat(user_id):
                bot.answer_callback_query(
                    call.id,
                    "⚠️ Эта функция доступна только участникам чата",
                    show_alert=True
                )
                return
            
            text = safe_markdown_v2(
                "📰 *Новости в газету*\n\n"
                "Здесь вы можете отправить новость для публикации в газете\\.\n\n"
                "💡 *Что можно отправить:*\n"
                "• Интересные события из игры\n"
                "• Объявления и анонсы\n"
                "• Полезные советы\n"
                "• Другие новости сообщества\n\n"
                "Выберите действие:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "📝 Отправить новость",
                    callback_data=ButtonCallback.USER_NEWS_SEND
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 В главное меню",
                    callback_data=ButtonCallback.USER_MAIN_MENU
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"News menu error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при открытии меню новостей",
                show_alert=True
            )
    
    @staticmethod
    def handle_news_send_start(call):
        """Обработка начала отправки новости"""
        try:
            user_id = call.from_user.id
            
            # Проверяем, состоит ли пользователь в чате
            if not NewsHandlers.is_user_in_chat(user_id):
                bot.answer_callback_query(
                    call.id,
                    "⚠️ Эта функция доступна только участникам чата",
                    show_alert=True
                )
                return
            
            # Очищаем временное хранилище
            if user_id in user_content_storage.data:
                del user_content_storage.data[user_id]
            
            # Устанавливаем состояние ожидания текста новости
            bot.set_state(user_id, UserState.WAITING_NEWS_TEXT)
            
            text = safe_markdown_v2(
                "📝 *Отправка новости*\n\n"
                "Пожалуйста, напишите текст вашей новости\\.\n"
                "Будьте информативны и интересны\\!\n\n"
                "💡 *Советы:*\n"
                "• Используйте заголовки и подзаголовки\n"
                "• Добавляйте эмодзи для привлечения внимания\n"
                "• Проверьте орфографию\n\n"
                "❌ Для отмены отправьте /cancel"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data="cancel_news"
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"News send start error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при начале отправки новости",
                show_alert=True
            )
    
    @staticmethod
    def handle_news_text(message):
        """Обработка текста новости"""
        try:
            user_id = message.from_user.id
            content_data = user_content_storage.get_data(user_id, "news")
            content_data["text"] = message.text
            
            # Переходим к этапу фото
            bot.set_state(user_id, UserState.WAITING_NEWS_PHOTO)
            
            text = safe_markdown_v2(
                "📸 *Добавление фото*\n\n"
                "Теперь вы можете добавить фото к вашей новости\\.\n"
                "Можно отправить до 10 фотографий\\.\n\n"
                "💡 *Совет:* Фото сделают новость более наглядной\\.\n\n"
                "⏭️ *Пропустить фото* - нажмите кнопку ниже\n"
                "❌ *Отменить* - отправьте /cancel"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "⏭️ Пропустить фото",
                    callback_data="skip_news_photos"
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data="cancel_news"
                )
            )
            
            bot.reply_to(
                message,
                text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"News text error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке текста новости")
    
    @staticmethod
    def handle_news_photo(message):
        """Обработка фото для новости"""
        try:
            user_id = message.from_user.id
            content_data = user_content_storage.get_data(user_id, "news")
            
            # Получаем фото
            photo = message.photo[-1]  # Берем фото наибольшего размера
            file_id = photo.file_id
            
            # Добавляем фото к контенту
            if "photos" not in content_data:
                content_data["photos"] = []
            
            content_data["photos"].append(file_id)
            
            # Проверяем лимит фото
            if len(content_data["photos"]) >= 10:
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        "✅ *Фото добавлено*\n\n"
                        "📸 *Достигнут лимит фотографий*\\(10 штук\\)\n\n"
                        "Теперь отправьте новость:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
                # Показываем кнопку отправки
                NewsHandlers.show_news_preview(user_id)
                
            else:
                remaining = 10 - len(content_data["photos"])
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        f"✅ *Фото добавлено*\n\n"
                        f"📸 *Добавлено фотографий:* {len(content_data['photos'])}/10\n"
                        f"📷 *Осталось:* {remaining}\n\n"
                        f"Отправьте еще фото или нажмите кнопку для отправки:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
                # Показываем кнопки
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(
                        "📤 Отправить новость",
                        callback_data="send_news"
                    )
                )
                markup.add(
                    types.InlineKeyboardButton(
                        "❌ Отменить",
                        callback_data="cancel_news"
                    )
                )
                
                bot.send_message(
                    user_id,
                    "Выберите действие:",
                    reply_markup=markup
                )
                
        except Exception as e:
            logger.error(f"News photo error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке фото")
    
    @staticmethod
    def show_news_preview(user_id: int):
        """Показ превью новости"""
        content_data = user_content_storage.get_data(user_id, "news")
        
        # Формируем текст превью
        photos_count = len(content_data.get("photos", []))
        text_preview = content_data.get("text", "")[:100]
        if len(content_data.get("text", "")) > 100:
            text_preview += "..."
        
        preview_text = safe_markdown_v2(
            f"📋 *Превью новости*\n\n"
            f"📝 *Текст:* {text_preview}\n"
            f"📸 *Фотографий:* {photos_count}\n\n"
            f"✅ *Все готово для отправки\\!*\n\n"
            f"Отправить новость в газету\\?"
        )
        
        # Создаем клавиатуру
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📤 Отправить",
                callback_data="send_news"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "❌ Отменить",
                callback_data="cancel_news"
            )
        )
        
        bot.send_message(
            user_id,
            preview_text,
            parse_mode="MarkdownV2",
            reply_markup=markup
        )
    
    @staticmethod
    def handle_send_news(call):
        """Обработка отправки новости"""
        try:
            user_id = call.from_user.id
            content_data = user_content_storage.get_data(user_id, "news")
            
            # Отправляем новость в газету
            NewsHandlers.send_news_to_newspaper(user_id, content_data)
            
            # Очищаем временные данные
            user_content_storage.clear(user_id)
            bot.delete_state(user_id)
            
            # Подтверждаем отправку
            bot.answer_callback_query(
                call.id,
                "✅ Новость успешно отправлена в газету!",
                show_alert=True
            )
            
            # Показываем главное меню
            from menu.menu import Menu
            main_menu = Menu.user_menu()
            bot.send_message(
                user_id,
                "📰 *Новость отправлена\\!*\n\nСпасибо за вклад в газету\\!",
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Send news error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при отправке новости",
                show_alert=True
            )
    
    @staticmethod
    def handle_cancel_news(call):
        """Обработка отмены новости"""
        try:
            user_id = call.from_user.id
            
            # Очищаем временные данные
            user_content_storage.clear(user_id)
            bot.delete_state(user_id)
            
            # Подтверждаем отмену
            bot.answer_callback_query(
                call.id,
                "❌ Отправка новости отменена",
                show_alert=True
            )
            
            # Показываем главное меню
            from menu.menu import Menu
            main_menu = Menu.user_menu()
            bot.send_message(
                user_id,
                "❌ *Отправка отменена*\n\nВыберите действие:",
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Cancel news error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при отмене",
                show_alert=True
            )
    
    @staticmethod
    def handle_skip_news_photos(call):
        """Обработка пропуска фото"""
        try:
            user_id = call.from_user.id
            
            # Показываем превью без фото
            NewsHandlers.show_news_preview(user_id)
            
        except Exception as e:
            logger.error(f"Skip news photos error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при пропуске фото",
                show_alert=True
            )
    
    @staticmethod
    def send_news_to_newspaper(user_id: int, content_data: Dict[str, Any]):
        """Отправка новости в газету"""
        try:
            from datetime import datetime
            
            # Формируем сообщение для газеты
            news_text = safe_markdown_v2(
                f"📰 *Новость от участника*\n\n"
                f"👤 *Автор:* {user_id}\n"
                f"📝 *Текст:* {content_data.get('text', 'Не указан')}\n"
                f"📸 *Фотографий:* {len(content_data.get('photos', []))}\n\n"
                f"⏰ *Время отправки:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Отправляем текст
            bot.send_message(NEWSPAPER_CHAT_ID, news_text, parse_mode="MarkdownV2")
            
            # Отправляем фото
            for i, photo_id in enumerate(content_data.get("photos", []), 1):
                try:
                    bot.send_photo(
                        NEWSPAPER_CHAT_ID,
                        photo_id,
                        caption=f"📸 Фото {i}/{len(content_data['photos'])}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send photo {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to send news to newspaper: {e}")
            raise


# Регистрация обработчиков
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_NEWS)
@simple_lock()
@private_chat_only(bot)
def handle_user_news(call):
    """Обработчик меню новостей"""
    NewsHandlers.handle_news_menu(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_NEWS_SEND)
@simple_lock()
@private_chat_only(bot)
def handle_news_send_start(call):
    """Обработчик начала отправки новости"""
    NewsHandlers.handle_news_send_start(call)


@bot.message_handler(
    content_types=["text"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.WAITING_NEWS_TEXT
        and not message.text.startswith("/")
    ),
)
@simple_lock()
def handle_news_text(message):
    """Обработчик текста новости"""
    NewsHandlers.handle_news_text(message)


@bot.message_handler(
    content_types=["photo"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.WAITING_NEWS_PHOTO
    ),
)
@simple_lock()
def handle_news_photo(message):
    """Обработчик фото для новости"""
    NewsHandlers.handle_news_photo(message)


@bot.callback_query_handler(func=lambda call: call.data == "send_news")
@simple_lock()
def handle_send_news(call):
    """Обработчик отправки новости"""
    NewsHandlers.handle_send_news(call)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_news")
@simple_lock()
def handle_cancel_news(call):
    """Обработчик отмены новости"""
    NewsHandlers.handle_cancel_news(call)


@bot.callback_query_handler(func=lambda call: call.data == "skip_news_photos")
@simple_lock()
def handle_skip_news_photos(call):
    """Обработчик пропуска фото"""
    NewsHandlers.handle_skip_news_photos(call)
