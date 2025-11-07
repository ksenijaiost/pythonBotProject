"""
Упрощенная система блокировок на основе кэша
"""
import time
import threading
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from .cache_system import cache_manager

logger = logging.getLogger(__name__)


class SimpleLockManager:
    """Упрощенный менеджер блокировок на основе кэша"""
    
    def __init__(self, default_ttl: float = 30.0):
        """
        Args:
            default_ttl: Время жизни блокировки по умолчанию в секундах
        """
        self.default_ttl = default_ttl
        self._local_locks = {}  # Локальные блокировки для быстрого доступа
        self._lock_creation_lock = threading.Lock()
    
    def _get_local_lock(self, key: str) -> threading.Lock:
        """Получение локальной блокировки для ключа"""
        if key not in self._local_locks:
            with self._lock_creation_lock:
                if key not in self._local_locks:
                    self._local_locks[key] = threading.Lock()
        return self._local_locks[key]
    
    def acquire(self, key: str, ttl: Optional[float] = None) -> bool:
        """
        Попытка захвата блокировки
        
        Args:
            key: Ключ блокировки
            ttl: Время жизни блокировки
            
        Returns:
            True если блокировка захвачена, False если уже занята
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # Проверяем кэш
        if cache_manager.get('locks', key) is not None:
            return False
        
        # Устанавливаем блокировку в кэш
        cache_manager.set('locks', key, {
            'acquired_at': time.time(),
            'ttl': ttl
        }, ttl=ttl)
        
        logger.debug(f"Lock acquired: {key}")
        return True
    
    def release(self, key: str) -> bool:
        """
        Освобождение блокировки
        
        Args:
            key: Ключ блокировки
            
        Returns:
            True если блокировка была освобождена
        """
        result = cache_manager.delete('locks', key)
        if result:
            logger.debug(f"Lock released: {key}")
        return result
    
    def is_locked(self, key: str) -> bool:
        """
        Проверка, заблокирован ли ключ
        
        Args:
            key: Ключ блокировки
            
        Returns:
            True если заблокирован
        """
        return cache_manager.get('locks', key) is not None
    
    def get_lock_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о блокировке
        
        Args:
            key: Ключ блокировки
            
        Returns:
            Информация о блокировке или None
        """
        return cache_manager.get('locks', key)
    
    def cleanup_expired_locks(self) -> int:
        """
        Очистка истекших блокировок
        
        Returns:
            Количество очищенных блокировок
        """
        return cache_manager.cleanup_all_expired().get('locks', 0)
    
    @contextmanager
    def lock(self, key: str, ttl: Optional[float] = None, timeout: float = 5.0):
        """
        Контекстный менеджер для блокировки
        
        Args:
            key: Ключ блокировки
            ttl: Время жизни блокировки
            timeout: Таймаут ожидания блокировки
            
        Yields:
            True если блокировка захвачена
            
        Raises:
            TimeoutError: Если не удалось захватить блокировку в течение timeout
        """
        start_time = time.time()
        
        # Пытаемся захватить блокировку
        while not self.acquire(key, ttl):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Failed to acquire lock '{key}' within {timeout} seconds")
            time.sleep(0.1)  # Ждем 100ms перед повторной попыткой
        
        try:
            yield True
        finally:
            self.release(key)


# Глобальный экземпляр менеджера блокировок
lock_manager = SimpleLockManager()


class UserLockManager:
    """Менеджер блокировок пользователей"""
    
    @staticmethod
    def get_user_lock_key(user_id: int) -> str:
        """Получение ключа блокировки для пользователя"""
        return f"user_lock_{user_id}"
    
    @staticmethod
    def get_media_group_lock_key(user_id: int, media_group_id: str) -> str:
        """Получение ключа блокировки для медиагруппы"""
        return f"media_lock_{user_id}_{media_group_id}"
    
    @staticmethod
    def acquire_user_lock(user_id: int, ttl: float = 30.0) -> bool:
        """
        Захват блокировки пользователя
        
        Args:
            user_id: ID пользователя
            ttl: Время жизни блокировки
            
        Returns:
            True если блокировка захвачена
        """
        key = UserLockManager.get_user_lock_key(user_id)
        return lock_manager.acquire(key, ttl)
    
    @staticmethod
    def release_user_lock(user_id: int) -> bool:
        """
        Освобождение блокировки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если блокировка была освобождена
        """
        key = UserLockManager.get_user_lock_key(user_id)
        return lock_manager.release(key)
    
    @staticmethod
    def is_user_locked(user_id: int) -> bool:
        """
        Проверка, заблокирован ли пользователь
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если заблокирован
        """
        key = UserLockManager.get_user_lock_key(user_id)
        return lock_manager.is_locked(key)
    
    @staticmethod
    def acquire_media_group_lock(user_id: int, media_group_id: str, ttl: float = 60.0) -> bool:
        """
        Захват блокировки медиагруппы
        
        Args:
            user_id: ID пользователя
            media_group_id: ID медиагруппы
            ttl: Время жизни блокировки
            
        Returns:
            True если блокировка захвачена
        """
        key = UserLockManager.get_media_group_lock_key(user_id, media_group_id)
        return lock_manager.acquire(key, ttl)
    
    @staticmethod
    def release_media_group_lock(user_id: int, media_group_id: str) -> bool:
        """
        Освобождение блокировки медиагруппы
        
        Args:
            user_id: ID пользователя
            media_group_id: ID медиагруппы
            
        Returns:
            True если блокировка была освобождена
        """
        key = UserLockManager.get_media_group_lock_key(user_id, media_group_id)
        return lock_manager.release(key)
    
    @staticmethod
    def is_media_group_locked(user_id: int, media_group_id: str) -> bool:
        """
        Проверка, заблокирована ли медиагруппа
        
        Args:
            user_id: ID пользователя
            media_group_id: ID медиагруппы
            
        Returns:
            True если заблокирована
        """
        key = UserLockManager.get_media_group_lock_key(user_id, media_group_id)
        return lock_manager.is_locked(key)
    
    @staticmethod
    @contextmanager
    def user_lock(user_id: int, ttl: float = 30.0, timeout: float = 5.0):
        """
        Контекстный менеджер для блокировки пользователя
        
        Args:
            user_id: ID пользователя
            ttl: Время жизни блокировки
            timeout: Таймаут ожидания
            
        Yields:
            True если блокировка захвачена
        """
        key = UserLockManager.get_user_lock_key(user_id)
        with lock_manager.lock(key, ttl, timeout):
            yield True
    
    @staticmethod
    @contextmanager
    def media_group_lock(user_id: int, media_group_id: str, ttl: float = 60.0, timeout: float = 5.0):
        """
        Контекстный менеджер для блокировки медиагруппы
        
        Args:
            user_id: ID пользователя
            media_group_id: ID медиагруппы
            ttl: Время жизни блокировки
            timeout: Таймаут ожидания
            
        Yields:
            True если блокировка захвачена
        """
        key = UserLockManager.get_media_group_lock_key(user_id, media_group_id)
        with lock_manager.lock(key, ttl, timeout):
            yield True


def simple_lock(allow_media_groups: bool = False, ttl: float = 30.0, timeout: float = 5.0):
    """
    Упрощенный декоратор блокировки
    
    Args:
        allow_media_groups: Разрешить медиагруппы
        ttl: Время жизни блокировки
        timeout: Таймаут ожидания
        
    Example:
        @simple_lock()
        def handle_message(message):
            # Обработка сообщения
            pass
    """
    def decorator(func):
        def wrapper(message_or_call):
            user_id = message_or_call.from_user.id
            media_group_id = getattr(message_or_call, "media_group_id", None)
            
            try:
                # Для медиагрупп используем специальные блокировки
                if allow_media_groups and media_group_id:
                    with UserLockManager.media_group_lock(user_id, media_group_id, ttl=ttl*2, timeout=timeout):
                        return func(message_or_call)
                else:
                    with UserLockManager.user_lock(user_id, ttl=ttl, timeout=timeout):
                        return func(message_or_call)
                        
            except TimeoutError:
                # Отправляем сообщение о занятости
                from bot_instance import bot
                error_msg = "⏳ Пожалуйста, дождитесь завершения предыдущей операции"
                
                if hasattr(message_or_call, "message"):
                    bot.answer_callback_query(message_or_call.id, error_msg)
                else:
                    bot.reply_to(message_or_call, error_msg)
                
                logger.warning(f"Lock timeout for user {user_id}")
                return None
        
        return wrapper
    return decorator


def quick_lock(func):
    """
    Быстрый декоратор блокировки с минимальными настройками
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция
    """
    return simple_lock(ttl=10.0, timeout=2.0)(func)


def media_lock(func):
    """
    Декоратор блокировки для медиагрупп
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция
    """
    return simple_lock(allow_media_groups=True, ttl=60.0, timeout=5.0)(func)


# Утилиты для работы с блокировками
def get_lock_stats() -> Dict[str, Any]:
    """Получение статистики блокировок"""
    return cache_manager.get_cache('locks').get_stats()


def cleanup_all_locks() -> int:
    """Очистка всех блокировок"""
    return lock_manager.cleanup_expired_locks()


def is_user_busy(user_id: int) -> bool:
    """Проверка, занят ли пользователь"""
    return UserLockManager.is_user_locked(user_id)


def force_release_user_lock(user_id: int) -> bool:
    """Принудительное освобождение блокировки пользователя"""
    return UserLockManager.release_user_lock(user_id)
