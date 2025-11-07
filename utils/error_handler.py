"""
Система обработки ошибок
"""
import logging
import traceback
from typing import Optional, Callable, Any
from functools import wraps
import telebot.types as types
from telebot.apihelper import ApiTelegramException

from bot_instance import bot
from utils.markdown_utils import safe_markdown_v2

logger = logging.getLogger(__name__)


class BotError(Exception):
    """Базовое исключение бота"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, 
                 show_to_user: bool = True):
        super().__init__(message)
        self.message = message
        self.user_id = user_id
        self.show_to_user = show_to_user


class ValidationError(BotError):
    """Ошибка валидации"""
    pass


class PermissionError(BotError):
    """Ошибка прав доступа"""
    pass


class DatabaseError(BotError):
    """Ошибка базы данных"""
    pass


class CacheError(BotError):
    """Ошибка кэша"""
    pass


class ErrorHandler:
    """Обработчик ошибок"""
    
    @staticmethod
    def handle_telegram_error(e: ApiTelegramException, user_id: int) -> None:
        """
        Обработка ошибок Telegram API
        
        Args:
            e: Исключение Telegram API
            user_id: ID пользователя
        """
        try:
            if e.description == "Forbidden: bot was blocked by the user":
                logger.warning(f"User {user_id} blocked the bot")
                return
            
            elif e.description == "Bad Request: message is not modified":
                logger.debug(f"Message not modified for user {user_id}")
                return
            
            elif e.description == "Bad Request: message to edit not found":
                logger.warning(f"Message to edit not found for user {user_id}")
                return
            
            elif "can't parse entities" in e.description:
                logger.error(f"Markdown parsing error for user {user_id}: {e.description}")
                bot.send_message(
                    user_id,
                    safe_markdown_v2("❌ Ошибка форматирования текста. Попробуйте еще раз."),
                    parse_mode="MarkdownV2"
                )
                return
            
            else:
                logger.error(f"Telegram API error for user {user_id}: {e.description}")
                bot.send_message(
                    user_id,
                    safe_markdown_v2("❌ Произошла ошибка. Попробуйте еще раз."),
                    parse_mode="MarkdownV2"
                )
                
        except Exception as handler_error:
            logger.error(f"Error in error handler: {handler_error}")
    
    @staticmethod
    def handle_bot_error(e: BotError, user_id: int) -> None:
        """
        Обработка ошибок бота
        
        Args:
            e: Исключение бота
            user_id: ID пользователя
        """
        try:
            if e.show_to_user and user_id:
                bot.send_message(
                    user_id,
                    safe_markdown_v2(f"❌ {e.message}"),
                    parse_mode="MarkdownV2"
                )
            
            logger.error(f"Bot error for user {user_id}: {e.message}")
            
        except Exception as handler_error:
            logger.error(f"Error in bot error handler: {handler_error}")
    
    @staticmethod
    def handle_generic_error(e: Exception, user_id: int) -> None:
        """
        Обработка общих ошибок
        
        Args:
            e: Исключение
            user_id: ID пользователя
        """
        try:
            logger.error(f"Generic error for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
            if user_id:
                bot.send_message(
                    user_id,
                    safe_markdown_v2("❌ Произошла внутренняя ошибка. Попробуйте еще раз."),
                    parse_mode="MarkdownV2"
                )
                
        except Exception as handler_error:
            logger.error(f"Error in generic error handler: {handler_error}")
    
    @staticmethod
    def handle_error(e: Exception, user_id: int) -> None:
        """
        Универсальный обработчик ошибок
        
        Args:
            e: Исключение
            user_id: ID пользователя
        """
        if isinstance(e, ApiTelegramException):
            ErrorHandler.handle_telegram_error(e, user_id)
        elif isinstance(e, BotError):
            ErrorHandler.handle_bot_error(e, user_id)
        else:
            ErrorHandler.handle_generic_error(e, user_id)


def error_handler(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Пытаемся извлечь user_id из аргументов
            user_id = None
            
            # Ищем user_id в аргументах
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
                elif hasattr(arg, 'id'):
                    user_id = arg.id
                    break
            
            # Обрабатываем ошибку
            ErrorHandler.handle_error(e, user_id)
            
            # Возвращаем None для предотвращения дальнейшей обработки
            return None
    
    return wrapper


def message_error_handler(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в обработчиках сообщений
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция
    """
    @wraps(func)
    def wrapper(message_or_call, *args, **kwargs):
        try:
            return func(message_or_call, *args, **kwargs)
        except Exception as e:
            user_id = None
            
            if hasattr(message_or_call, 'from_user'):
                user_id = message_or_call.from_user.id
            elif hasattr(message_or_call, 'message') and hasattr(message_or_call.message, 'from_user'):
                user_id = message_or_call.message.from_user.id
            
            ErrorHandler.handle_error(e, user_id)
            return None
    
    return wrapper


def admin_error_handler(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в админских функциях
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Admin function error: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Пытаемся отправить ошибку админам
            try:
                from handlers.envParams import admin_ids
                for admin_id in admin_ids:
                    bot.send_message(
                        admin_id,
                        safe_markdown_v2(
                            f"⚠️ *Ошибка в админской функции*\n\n"
                            f"```{str(e)}```\n\n"
                            f"Проверьте логи для деталей"
                        ),
                        parse_mode="MarkdownV2"
                    )
            except Exception as notification_error:
                logger.error(f"Failed to notify admins: {notification_error}")
            
            return None
    
    return wrapper


def validate_user_id(user_id: int) -> None:
    """
    Валидация ID пользователя
    
    Args:
        user_id: ID пользователя
        
    Raises:
        ValidationError: Если ID невалиден
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValidationError("Invalid user ID")


def validate_chat_id(chat_id: int) -> None:
    """
    Валидация ID чата
    
    Args:
        chat_id: ID чата
        
    Raises:
        ValidationError: Если ID невалиден
    """
    if not isinstance(chat_id, int) or chat_id == 0:
        raise ValidationError("Invalid chat ID")


def validate_text(text: str, max_length: int = 4096) -> None:
    """
    Валидация текста
    
    Args:
        text: Текст для валидации
        max_length: Максимальная длина
        
    Raises:
        ValidationError: Если текст невалиден
    """
    if not isinstance(text, str):
        raise ValidationError("Text must be a string")
    
    if len(text) > max_length:
        raise ValidationError(f"Text too long (max {max_length} characters)")
    
    if not text.strip():
        raise ValidationError("Text cannot be empty")


def validate_photo_list(photos: list, max_count: int = 10) -> None:
    """
    Валидация списка фотографий
    
    Args:
        photos: Список фотографий
        max_count: Максимальное количество
        
    Raises:
        ValidationError: Если список невалиден
    """
    if not isinstance(photos, list):
        raise ValidationError("Photos must be a list")
    
    if len(photos) > max_count:
        raise ValidationError(f"Too many photos (max {max_count})")
    
    if not photos:
        raise ValidationError("At least one photo is required")


# Утилиты для создания ошибок
def create_validation_error(message: str, user_id: Optional[int] = None) -> ValidationError:
    """Создание ошибки валидации"""
    return ValidationError(message, user_id)


def create_permission_error(message: str, user_id: Optional[int] = None) -> PermissionError:
    """Создание ошибки прав доступа"""
    return PermissionError(message, user_id)


def create_database_error(message: str, user_id: Optional[int] = None) -> DatabaseError:
    """Создание ошибки базы данных"""
    return DatabaseError(message, user_id)


def create_cache_error(message: str, user_id: Optional[int] = None) -> CacheError:
    """Создание ошибки кэша"""
    return CacheError(message, user_id)
