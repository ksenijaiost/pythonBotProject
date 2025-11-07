"""
Общие обработчики
"""
import logging
from typing import Optional, Dict, Any
import telebot.types as types

from bot_instance import bot
from utils.simple_locks import simple_lock
from utils.markdown_utils import safe_markdown_v2, format_markdown_v2_with_preserved_formatting
from handlers.decorator import private_chat_only
from menu.constants import ButtonCallback, UserState
from database.db_classes import user_content_storage
from services.user_service import UserService

logger = logging.getLogger(__name__)


class CommonHandlers:
    """Класс для общих обработчиков"""
    
    @staticmethod
    def get_user_info(user) -> str:
        """
        Получение информации о пользователе
        
        Args:
            user: Объект пользователя
            
        Returns:
            Строка с информацией о пользователе
        """
        user_info = "\n\n👤 Отправитель: "
        
        if user.username:
            user_info += f"@{user.username}"
            if user.first_name:
                user_info += f" ({user.first_name}"
                if user.last_name:
                    user_info += f" {user.last_name}"
                user_info += ")"
        else:
            user_info += f"[id:{user.id}]"
            if user.first_name:
                user_info += f" {user.first_name}"
                if user.last_name:
                    user_info += f" {user.last_name}"
        
        return user_info
    
    @staticmethod
    def handle_help(message):
        """Обработка команды /help"""
        try:
            help_text = safe_markdown_v2(
                "❓ *Помощь по боту*\n\n\n"
                "*Гайды*: гайды по Animal Crossing и не только;\n\n"
                "*Конкурсы*: информация о конкурсах и отправка работ;\n\n"
                "*Сообщение админам*: отправка сообщений администраторам;\n\n"
                "*Новости в газету*: отправка новостей для публикации;\n\n"
                "💡 *Советы:*\n"
                "• Используйте кнопки для навигации\n"
                "• Отправляйте качественные фото\n"
                "• Будьте вежливы в сообщениях\n\n"
                "❌ *Отмена:* отправьте /cancel в любой момент\n\n"
                "🔙 *Главное меню:* /start"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 В главное меню",
                    callback_data=ButtonCallback.USER_MAIN_MENU
                )
            )
            
            bot.reply_to(
                message,
                help_text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Help command error: {e}")
            bot.reply_to(message, "❌ Ошибка при показе справки")
    
    @staticmethod
    def handle_cancel(message):
        """Обработка команды /cancel"""
        try:
            user_id = message.from_user.id
            
            # Очищаем все состояния и временные данные
            bot.delete_state(user_id)
            user_content_storage.clear(user_id)
            
            # Показываем главное меню
            from menu.menu import Menu
            from services.user_service import UserService
            
            # Определяем тип меню
            if UserService.is_admin(user_id):
                main_menu = Menu.adm_menu()
                welcome_text = "❌ *Операция отменена*\n\nДобро пожаловать, администратор👑\nВыберите действие:"
            else:
                main_menu = Menu.user_menu()
                welcome_text = "❌ *Операция отменена*\n\nВыберите действие:"
            
            # Пытаемся обновить предыдущее сообщение с клавиатурой
            try:
                # Ищем предыдущее сообщение с клавиатурой
                chat_id = message.chat.id
                message_id = message.message_id - 1
                
                # Проверяем, есть ли предыдущее сообщение с клавиатурой
                if message_id > 0:
                    bot.edit_message_text(
                        welcome_text,
                        chat_id,
                        message_id,
                        parse_mode="MarkdownV2",
                        reply_markup=main_menu
                    )
                    return
            except Exception:
                # Если не удалось обновить, отправляем новое сообщение
                pass
            
            # Отправляем новое сообщение
            bot.reply_to(
                message,
                safe_markdown_v2(welcome_text),
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Cancel command error: {e}")
            bot.reply_to(message, "❌ Ошибка при отмене операции")
    
    @staticmethod
    def handle_main_menu(call):
        """Обработка возврата в главное меню"""
        try:
            user_id = call.from_user.id
            
            # Очищаем все состояния и временные данные
            bot.delete_state(user_id)
            user_content_storage.clear(user_id)
            
            # Определяем тип меню
            if UserService.is_admin(user_id):
                from menu.menu import Menu
                main_menu = Menu.adm_menu()
                welcome_text = "Добро пожаловать, администратор👑"
            else:
                from menu.menu import Menu
                main_menu = Menu.user_menu()
                welcome_text = "Добро пожаловать😊"
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=safe_markdown_v2(f"✨ {welcome_text}\nВыберите действие:"),
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Main menu error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при возврате в главное меню",
                show_alert=True
            )
    
    @staticmethod
    def handle_start(message):
        """Обработка команды /start"""
        try:
            user_id = message.from_user.id
            
            # Принудительный сброс состояний
            bot.delete_state(user_id)
            user_content_storage.clear(user_id)
            
            # Определяем тип меню
            if UserService.is_admin(user_id):
                from menu.menu import Menu
                main_menu = Menu.adm_menu()
                welcome_text = "Добро пожаловать, администратор👑"
            else:
                from menu.menu import Menu
                main_menu = Menu.user_menu()
                welcome_text = "Добро пожаловать😊"
            
            bot.send_message(
                message.chat.id,
                safe_markdown_v2(f"✨ {welcome_text}\nВыберите действие:"),
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Start command error: {e}")
            bot.send_message(
                message.chat.id,
                "⚠️ Произошла ошибка\nПопробуйте еще раз",
                reply_markup=types.ReplyKeyboardRemove()
            )
    
    @staticmethod
    def is_user_blocked(call) -> bool:
        """
        Проверка, заблокирован ли пользователь
        
        Args:
            call: Callback query
            
        Returns:
            True если заблокирован
        """
        try:
            if UserService.is_user_blocked(call.from_user.id):
                bot.answer_callback_query(
                    call.id,
                    "⚠️ Вы заблокированы ботом\nЕсли считаете это ошибкой, свяжитесь с админами чата",
                    show_alert=True
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Block check error: {e}")
            return False
    
    @staticmethod
    def handle_unknown_message(message):
        """Обработка неизвестных сообщений"""
        try:
            user_id = message.from_user.id
            state = bot.get_state(user_id)
            
            if state:
                # Пользователь в каком-то состоянии
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        "❓ *Неизвестная команда*\n\n"
                        "Вы находитесь в процессе выполнения операции\\.\n"
                        "Пожалуйста, следуйте инструкциям или отправьте /cancel для отмены\\."
                    ),
                    parse_mode="MarkdownV2"
                )
            else:
                # Пользователь не в состоянии
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        "❓ *Неизвестная команда*\n\n"
                        "Используйте /start для открытия главного меню или /help для справки\\."
                    ),
                    parse_mode="MarkdownV2"
                )
                
        except Exception as e:
            logger.error(f"Unknown message error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке сообщения")


# Регистрация обработчиков
@bot.message_handler(commands=["help"])
@simple_lock()
def handle_help(message):
    """Обработчик команды /help"""
    CommonHandlers.handle_help(message)


@bot.message_handler(commands=["cancel"])
@simple_lock()
def handle_cancel(message):
    """Обработчик команды /cancel"""
    CommonHandlers.handle_cancel(message)


@bot.message_handler(commands=["start"])
@simple_lock()
def handle_start(message):
    """Обработчик команды /start"""
    CommonHandlers.handle_start(message)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_MAIN_MENU)
@simple_lock()
def handle_main_menu(call):
    """Обработчик возврата в главное меню"""
    CommonHandlers.handle_main_menu(call)


@bot.message_handler(func=lambda message: True)
@simple_lock()
def handle_unknown_message(message):
    """Обработчик неизвестных сообщений"""
    CommonHandlers.handle_unknown_message(message)
