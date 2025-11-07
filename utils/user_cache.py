"""
Кэширование пользовательских данных
"""
import logging
from typing import Optional, Dict, Any, List
from .cache_system import (
    cache_manager, 
    get_cached_user_data, 
    set_cached_user_data,
    is_cached_admin,
    set_cached_admin,
    is_cached_judge,
    set_cached_judge,
    cached,
    cache_invalidate
)
from functools import wraps

logger = logging.getLogger(__name__)


class UserCacheManager:
    """Менеджер кэширования пользовательских данных"""
    
    @staticmethod
    def get_user_submissions(user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Получение заявок пользователя из кэша
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список заявок или None если не в кэше
        """
        return get_cached_user_data(user_id, "submissions")
    
    @staticmethod
    def set_user_submissions(user_id: int, submissions: List[Dict[str, Any]]) -> None:
        """
        Сохранение заявок пользователя в кэш
        
        Args:
            user_id: ID пользователя
            submissions: Список заявок
        """
        set_cached_user_data(user_id, "submissions", submissions, ttl=600.0)  # 10 минут
    
    @staticmethod
    def get_user_state(user_id: int) -> Optional[str]:
        """
        Получение состояния пользователя из кэша
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Состояние или None если не в кэше
        """
        return get_cached_user_data(user_id, "state")
    
    @staticmethod
    def set_user_state(user_id: int, state: str) -> None:
        """
        Сохранение состояния пользователя в кэш
        
        Args:
            user_id: ID пользователя
            state: Состояние
        """
        set_cached_user_data(user_id, "state", state, ttl=1800.0)  # 30 минут
    
    @staticmethod
    def get_user_content(user_id: int, content_type: str) -> Optional[Dict[str, Any]]:
        """
        Получение контента пользователя из кэша
        
        Args:
            user_id: ID пользователя
            content_type: Тип контента
            
        Returns:
            Контент или None если не в кэше
        """
        return get_cached_user_data(user_id, f"content_{content_type}")
    
    @staticmethod
    def set_user_content(user_id: int, content_type: str, content: Dict[str, Any]) -> None:
        """
        Сохранение контента пользователя в кэш
        
        Args:
            user_id: ID пользователя
            content_type: Тип контента
            content: Контент
        """
        set_cached_user_data(user_id, f"content_{content_type}", content, ttl=600.0)  # 10 минут
    
    @staticmethod
    def invalidate_user_cache(user_id: int) -> None:
        """
        Инвалидация всего кэша пользователя
        
        Args:
            user_id: ID пользователя
        """
        cache_manager.invalidate_pattern('users', f"user_{user_id}_")
        logger.info(f"Invalidated cache for user {user_id}")
    
    @staticmethod
    def invalidate_user_submissions(user_id: int) -> None:
        """
        Инвалидация кэша заявок пользователя
        
        Args:
            user_id: ID пользователя
        """
        cache_manager.delete('users', f"user_{user_id}_submissions")
        logger.debug(f"Invalidated submissions cache for user {user_id}")


class PermissionCacheManager:
    """Менеджер кэширования прав доступа"""
    
    @staticmethod
    def is_admin(user_id: int) -> Optional[bool]:
        """
        Проверка статуса админа из кэша
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True/False если в кэше, None если не кэшировано
        """
        return is_cached_admin(user_id)
    
    @staticmethod
    def set_admin(user_id: int, is_admin: bool) -> None:
        """
        Сохранение статуса админа в кэш
        
        Args:
            user_id: ID пользователя
            is_admin: Статус админа
        """
        set_cached_admin(user_id, is_admin)
    
    @staticmethod
    def is_judge(user_id: int) -> Optional[bool]:
        """
        Проверка статуса судьи из кэша
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True/False если в кэше, None если не кэшировано
        """
        return is_cached_judge(user_id)
    
    @staticmethod
    def set_judge(user_id: int, is_judge: bool) -> None:
        """
        Сохранение статуса судьи в кэш
        
        Args:
            user_id: ID пользователя
            is_judge: Статус судьи
        """
        set_cached_judge(user_id, is_judge)
    
    @staticmethod
    def invalidate_permissions_cache() -> None:
        """Инвалидация всего кэша прав доступа"""
        cache_manager.clear_cache('permissions')
        logger.info("Invalidated permissions cache")


# Декораторы для кэширования функций
def cache_user_submissions(func):
    """Декоратор для кэширования заявок пользователя"""
    @wraps(func)
    def wrapper(user_id: int, *args, **kwargs):
        # Пытаемся получить из кэша
        cached_submissions = UserCacheManager.get_user_submissions(user_id)
        if cached_submissions is not None:
            logger.debug(f"Cache hit: user submissions for {user_id}")
            return cached_submissions
        
        # Выполняем функцию и кэшируем результат
        submissions = func(user_id, *args, **kwargs)
        UserCacheManager.set_user_submissions(user_id, submissions)
        logger.debug(f"Cache miss: user submissions for {user_id}")
        
        return submissions
    
    return wrapper


def cache_user_state(func):
    """Декоратор для кэширования состояния пользователя"""
    @wraps(func)
    def wrapper(user_id: int, *args, **kwargs):
        # Пытаемся получить из кэша
        cached_state = UserCacheManager.get_user_state(user_id)
        if cached_state is not None:
            logger.debug(f"Cache hit: user state for {user_id}")
            return cached_state
        
        # Выполняем функцию и кэшируем результат
        state = func(user_id, *args, **kwargs)
        UserCacheManager.set_user_state(user_id, state)
        logger.debug(f"Cache miss: user state for {user_id}")
        
        return state
    
    return wrapper


def cache_permissions(func):
    """Декоратор для кэширования прав доступа"""
    @wraps(func)
    def wrapper(user_id: int, *args, **kwargs):
        # Определяем тип проверки по имени функции
        if 'admin' in func.__name__.lower():
            cached_result = PermissionCacheManager.is_admin(user_id)
            if cached_result is not None:
                logger.debug(f"Cache hit: admin check for {user_id}")
                return cached_result
            
            result = func(user_id, *args, **kwargs)
            PermissionCacheManager.set_admin(user_id, result)
            logger.debug(f"Cache miss: admin check for {user_id}")
            return result
        
        elif 'judge' in func.__name__.lower():
            cached_result = PermissionCacheManager.is_judge(user_id)
            if cached_result is not None:
                logger.debug(f"Cache hit: judge check for {user_id}")
                return cached_result
            
            result = func(user_id, *args, **kwargs)
            PermissionCacheManager.set_judge(user_id, result)
            logger.debug(f"Cache miss: judge check for {user_id}")
            return result
        
        else:
            # Для других функций просто выполняем
            return func(user_id, *args, **kwargs)
    
    return wrapper


# Утилиты для работы с кэшем пользователей
def warm_up_user_cache(user_id: int) -> None:
    """
    Прогрев кэша для пользователя
    
    Args:
        user_id: ID пользователя
    """
    try:
        # Импортируем здесь чтобы избежать циклических импортов
        from database.db_classes import SubmissionManager
        from handlers.envParams import admin_ids
        
        # Кэшируем заявки пользователя
        submissions = SubmissionManager.get_user_submissions(user_id)
        UserCacheManager.set_user_submissions(user_id, submissions)
        
        # Кэшируем права доступа
        is_admin = user_id in admin_ids
        PermissionCacheManager.set_admin(user_id, is_admin)
        
        logger.info(f"Warmed up cache for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to warm up cache for user {user_id}: {e}")


def cleanup_user_cache(user_id: int) -> None:
    """
    Очистка кэша пользователя
    
    Args:
        user_id: ID пользователя
    """
    UserCacheManager.invalidate_user_cache(user_id)
    logger.info(f"Cleaned up cache for user {user_id}")


def get_cache_stats() -> Dict[str, Any]:
    """Получение статистики кэша"""
    return cache_manager.get_all_stats()
