"""
Обработчики сообщений админам
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import telebot.types as types
from telebot.apihelper import ApiTelegramException

from bot_instance import bot
from utils.simple_locks import simple_lock, media_lock
from utils.markdown_utils import safe_markdown_v2
from handlers.decorator import private_chat_only
from handlers.envParams import ADMIN_CHAT_ID
from menu.constants import ButtonCallback, UserState
from database.db_classes import user_content_storage

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Класс для обработки сообщений админам"""
    
    @staticmethod
    def handle_admin_message_start(call):
        """Обработка начала отправки сообщения админам"""
        try:
            user_id = call.from_user.id
            
            # Очищаем временное хранилище
            if user_id in user_content_storage.data:
                del user_content_storage.data[user_id]
            
            # Устанавливаем состояние ожидания текста
            bot.set_state(user_id, UserState.WAITING_ADMIN_CONTENT)
            
            text = safe_markdown_v2(
                "📝 *Сообщение админам*\n\n"
                "Пожалуйста, напишите ваше сообщение\\.\n"
                "Опишите проблему, вопрос или предложение\\.\n\n"
                "💡 *Совет:* Будьте конкретны и вежливы\\.\n\n"
                "❌ Для отмены отправьте /cancel"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data="cancel_admin_message"
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
            logger.error(f"Admin message start error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при начале отправки сообщения",
                show_alert=True
            )
    
    @staticmethod
    def handle_admin_text(message):
        """Обработка текста сообщения админам"""
        try:
            user_id = message.from_user.id
            content_data = user_content_storage.get_data(user_id, "content")
            content_data["text"] = message.text
            
            # Переходим к этапу фото
            bot.set_state(user_id, UserState.WAITING_ADMIN_CONTENT_PHOTO)
            
            text = safe_markdown_v2(
                "📸 *Добавление фото*\n\n"
                "Теперь вы можете добавить фото к вашему сообщению\\.\n"
                "Можно отправить до 10 фотографий\\.\n\n"
                "💡 *Совет:* Фото поможет лучше понять вашу проблему\\.\n\n"
                "⏭️ *Пропустить фото* - нажмите кнопку ниже\n"
                "❌ *Отменить* - отправьте /cancel"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "⏭️ Пропустить фото",
                    callback_data="skip_admin_photos"
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data="cancel_admin_message"
                )
            )
            
            bot.reply_to(
                message,
                text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Admin text error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке текста")
    
    @staticmethod
    def handle_admin_photo(message):
        """Обработка фото для сообщения админам"""
        try:
            user_id = message.from_user.id
            content_data = user_content_storage.get_data(user_id, "content")
            
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
                        "Теперь отправьте сообщение админам:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
                # Показываем кнопку отправки
                MessageHandlers.show_admin_message_preview(user_id)
                
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
                        "📤 Отправить сообщение",
                        callback_data="send_admin_message"
                    )
                )
                markup.add(
                    types.InlineKeyboardButton(
                        "❌ Отменить",
                        callback_data="cancel_admin_message"
                    )
                )
                
                bot.send_message(
                    user_id,
                    "Выберите действие:",
                    reply_markup=markup
                )
                
        except Exception as e:
            logger.error(f"Admin photo error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке фото")
    
    @staticmethod
    def show_admin_message_preview(user_id: int):
        """Показ превью сообщения админам"""
        content_data = user_content_storage.get_data(user_id, "content")
        
        # Формируем текст превью
        photos_count = len(content_data.get("photos", []))
        text_preview = content_data.get("text", "")[:100]
        if len(content_data.get("text", "")) > 100:
            text_preview += "..."
        
        preview_text = safe_markdown_v2(
            f"📋 *Превью сообщения админам*\n\n"
            f"📝 *Текст:* {text_preview}\n"
            f"📸 *Фотографий:* {photos_count}\n\n"
            f"✅ *Все готово для отправки\\!*\n\n"
            f"Отправить сообщение админам\\?"
        )
        
        # Создаем клавиатуру
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📤 Отправить",
                callback_data="send_admin_message"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "❌ Отменить",
                callback_data="cancel_admin_message"
            )
        )
        
        bot.send_message(
            user_id,
            preview_text,
            parse_mode="MarkdownV2",
            reply_markup=markup
        )
    
    @staticmethod
    def handle_send_admin_message(call):
        """Обработка отправки сообщения админам"""
        try:
            user_id = call.from_user.id
            content_data = user_content_storage.get_data(user_id, "content")
            
            # Отправляем сообщение админам
            MessageHandlers.send_message_to_admins(user_id, content_data)
            
            # Очищаем временные данные
            user_content_storage.clear(user_id)
            bot.delete_state(user_id)
            
            # Подтверждаем отправку
            bot.answer_callback_query(
                call.id,
                "✅ Сообщение успешно отправлено админам!",
                show_alert=True
            )
            
            # Показываем главное меню
            from menu.menu import Menu
            main_menu = Menu.user_menu()
            bot.send_message(
                user_id,
                "✅ *Сообщение отправлено\\!*\n\nСпасибо за обращение\\!",
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Send admin message error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при отправке сообщения",
                show_alert=True
            )
    
    @staticmethod
    def handle_cancel_admin_message(call):
        """Обработка отмены сообщения админам"""
        try:
            user_id = call.from_user.id
            
            # Очищаем временные данные
            user_content_storage.clear(user_id)
            bot.delete_state(user_id)
            
            # Подтверждаем отмену
            bot.answer_callback_query(
                call.id,
                "❌ Отправка сообщения отменена",
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
            logger.error(f"Cancel admin message error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при отмене",
                show_alert=True
            )
    
    @staticmethod
    def handle_skip_admin_photos(call):
        """Обработка пропуска фото"""
        try:
            user_id = call.from_user.id
            
            # Показываем превью без фото
            MessageHandlers.show_admin_message_preview(user_id)
            
        except Exception as e:
            logger.error(f"Skip admin photos error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при пропуске фото",
                show_alert=True
            )
    
    @staticmethod
    def send_message_to_admins(user_id: int, content_data: Dict[str, Any]):
        """Отправка сообщения админам"""
        try:
            # Формируем сообщение для админов
            admin_text = safe_markdown_v2(
                f"📨 *Сообщение от пользователя*\n\n"
                f"👤 *Отправитель:* {user_id}\n"
                f"📝 *Текст:* {content_data.get('text', 'Не указан')}\n"
                f"📸 *Фотографий:* {len(content_data.get('photos', []))}\n\n"
                f"⏰ *Время отправки:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Отправляем текст
            bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="MarkdownV2")
            
            # Отправляем фото
            for i, photo_id in enumerate(content_data.get("photos", []), 1):
                try:
                    bot.send_photo(
                        ADMIN_CHAT_ID,
                        photo_id,
                        caption=f"📸 Фото {i}/{len(content_data['photos'])}"
                    )
                except ApiTelegramException as e:
                    logger.error(f"Failed to send photo {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to send message to admins: {e}")
            raise


# Регистрация обработчиков
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_TO_ADMIN)
@simple_lock()
@private_chat_only(bot)
def handle_user_to_admin(call):
    """Обработчик начала отправки сообщения админам"""
    MessageHandlers.handle_admin_message_start(call)


@bot.message_handler(
    content_types=["text"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.WAITING_ADMIN_CONTENT
        and not message.text.startswith("/")
    ),
)
@simple_lock()
def handle_user_text(message):
    """Обработчик текста сообщения админам"""
    MessageHandlers.handle_admin_text(message)


@bot.message_handler(
    content_types=["photo"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.WAITING_ADMIN_CONTENT_PHOTO
    ),
)
@simple_lock()
def handle_admin_photo(message):
    """Обработчик фото для сообщения админам"""
    MessageHandlers.handle_admin_photo(message)


@bot.callback_query_handler(func=lambda call: call.data == "send_admin_message")
@simple_lock()
def handle_send_admin_message(call):
    """Обработчик отправки сообщения админам"""
    MessageHandlers.handle_send_admin_message(call)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_admin_message")
@simple_lock()
def handle_cancel_admin_message(call):
    """Обработчик отмены сообщения админам"""
    MessageHandlers.handle_cancel_admin_message(call)


@bot.callback_query_handler(func=lambda call: call.data == "skip_admin_photos")
@simple_lock()
def handle_skip_admin_photos(call):
    """Обработчик пропуска фото"""
    MessageHandlers.handle_skip_admin_photos(call)
