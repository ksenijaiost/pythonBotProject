"""
Кэширование данных конкурсов
"""
import logging
from typing import Optional, Dict, Any, List
from .cache_system import (
    cache_manager,
    get_cached_contest_data,
    set_cached_contest_data,
    get_cached_stats,
    set_cached_stats,
    cached,
    cache_invalidate
)

logger = logging.getLogger(__name__)


class ContestCacheManager:
    """Менеджер кэширования данных конкурсов"""
    
    @staticmethod
    def get_current_contest() -> Optional[Dict[str, Any]]:
        """
        Получение текущего конкурса из кэша
        
        Returns:
            Данные конкурса или None если не в кэше
        """
        return get_cached_contest_data()
    
    @staticmethod
    def set_current_contest(contest_data: Dict[str, Any]) -> None:
        """
        Сохранение текущего конкурса в кэш
        
        Args:
            contest_data: Данные конкурса
        """
        set_cached_contest_data(contest_data)
        logger.debug("Cached current contest data")
    
    @staticmethod
    def get_contest_by_id(contest_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение конкурса по ID из кэша
        
        Args:
            contest_id: ID конкурса
            
        Returns:
            Данные конкурса или None если не в кэше
        """
        return get_cached_contest_data(contest_id)
    
    @staticmethod
    def set_contest_by_id(contest_id: int, contest_data: Dict[str, Any]) -> None:
        """
        Сохранение конкурса по ID в кэш
        
        Args:
            contest_id: ID конкурса
            contest_data: Данные конкурса
        """
        set_cached_contest_data(contest_data, contest_id)
        logger.debug(f"Cached contest data for ID {contest_id}")
    
    @staticmethod
    def invalidate_contest_cache(contest_id: Optional[int] = None) -> None:
        """
        Инвалидация кэша конкурсов
        
        Args:
            contest_id: ID конкурса (если None, инвалидируется весь кэш)
        """
        if contest_id is None:
            cache_manager.clear_cache('contests')
            logger.info("Invalidated all contest cache")
        else:
            cache_manager.delete('contests', f"contest_{contest_id}")
            logger.info(f"Invalidated cache for contest {contest_id}")


class StatsCacheManager:
    """Менеджер кэширования статистики"""
    
    @staticmethod
    def get_contest_statistics() -> Optional[Dict[str, Any]]:
        """
        Получение статистики конкурса из кэша
        
        Returns:
            Статистика или None если не в кэше
        """
        return get_cached_stats("contest_stats")
    
    @staticmethod
    def set_contest_statistics(stats: Dict[str, Any]) -> None:
        """
        Сохранение статистики конкурса в кэш
        
        Args:
            stats: Статистика
        """
        set_cached_stats("contest_stats", stats)
        logger.debug("Cached contest statistics")
    
    @staticmethod
    def get_pending_submissions() -> Optional[List[Dict[str, Any]]]:
        """
        Получение ожидающих заявок из кэша
        
        Returns:
            Список заявок или None если не в кэше
        """
        return get_cached_stats("pending_submissions")
    
    @staticmethod
    def set_pending_submissions(submissions: List[Dict[str, Any]]) -> None:
        """
        Сохранение ожидающих заявок в кэш
        
        Args:
            submissions: Список заявок
        """
        set_cached_stats("pending_submissions", submissions)
        logger.debug("Cached pending submissions")
    
    @staticmethod
    def get_judges_count() -> Optional[int]:
        """
        Получение количества судей из кэша
        
        Returns:
            Количество судей или None если не в кэше
        """
        return get_cached_stats("judges_count")
    
    @staticmethod
    def set_judges_count(count: int) -> None:
        """
        Сохранение количества судей в кэш
        
        Args:
            count: Количество судей
        """
        set_cached_stats("judges_count", count)
        logger.debug("Cached judges count")
    
    @staticmethod
    def invalidate_stats_cache() -> None:
        """Инвалидация кэша статистики"""
        cache_manager.clear_cache('stats')
        logger.info("Invalidated stats cache")


# Декораторы для кэширования функций конкурсов
def cache_current_contest(func):
    """Декоратор для кэширования текущего конкурса"""
    def wrapper(*args, **kwargs):
        # Пытаемся получить из кэша
        cached_contest = ContestCacheManager.get_current_contest()
        if cached_contest is not None:
            logger.debug("Cache hit: current contest")
            return cached_contest
        
        # Выполняем функцию и кэшируем результат
        contest = func(*args, **kwargs)
        if contest:
            ContestCacheManager.set_current_contest(contest)
        logger.debug("Cache miss: current contest")
        
        return contest
    
    return wrapper


def cache_contest_stats(func):
    """Декоратор для кэширования статистики конкурса"""
    def wrapper(*args, **kwargs):
        # Пытаемся получить из кэша
        cached_stats = StatsCacheManager.get_contest_statistics()
        if cached_stats is not None:
            logger.debug("Cache hit: contest statistics")
            return cached_stats
        
        # Выполняем функцию и кэшируем результат
        stats = func(*args, **kwargs)
        StatsCacheManager.set_contest_statistics(stats)
        logger.debug("Cache miss: contest statistics")
        
        return stats
    
    return wrapper


def cache_pending_submissions(func):
    """Декоратор для кэширования ожидающих заявок"""
    def wrapper(*args, **kwargs):
        # Пытаемся получить из кэша
        cached_submissions = StatsCacheManager.get_pending_submissions()
        if cached_submissions is not None:
            logger.debug("Cache hit: pending submissions")
            return cached_submissions
        
        # Выполняем функцию и кэшируем результат
        submissions = func(*args, **kwargs)
        StatsCacheManager.set_pending_submissions(submissions)
        logger.debug("Cache miss: pending submissions")
        
        return submissions
    
    return wrapper


def invalidate_contest_cache(func):
    """Декоратор для инвалидации кэша конкурсов после изменений"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Инвалидируем кэш конкурсов
        ContestCacheManager.invalidate_contest_cache()
        
        # Инвалидируем кэш статистики
        StatsCacheManager.invalidate_stats_cache()
        
        logger.debug("Invalidated contest and stats cache")
        return result
    
    return wrapper


def invalidate_submission_cache(func):
    """Декоратор для инвалидации кэша заявок после изменений"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Инвалидируем кэш статистики
        StatsCacheManager.invalidate_stats_cache()
        
        logger.debug("Invalidated submission cache")
        return result
    
    return wrapper


# Утилиты для работы с кэшем конкурсов
def warm_up_contest_cache() -> None:
    """Прогрев кэша конкурсов"""
    try:
        # Импортируем здесь чтобы избежать циклических импортов
        from database.db_classes import ContestManager, SubmissionManager
        
        # Кэшируем текущий конкурс
        current_contest = ContestManager.get_current_contest()
        if current_contest:
            ContestCacheManager.set_current_contest(current_contest)
        
        # Кэшируем статистику
        stats = SubmissionManager.get_contest_statistics()
        if stats:
            StatsCacheManager.set_contest_statistics(stats)
        
        # Кэшируем ожидающие заявки
        pending_submissions = SubmissionManager.get_pending_submissions()
        if pending_submissions:
            StatsCacheManager.set_pending_submissions(pending_submissions)
        
        logger.info("Warmed up contest cache")
        
    except Exception as e:
        logger.error(f"Failed to warm up contest cache: {e}")


def cleanup_contest_cache() -> None:
    """Очистка кэша конкурсов"""
    ContestCacheManager.invalidate_contest_cache()
    StatsCacheManager.invalidate_stats_cache()
    logger.info("Cleaned up contest cache")


def get_contest_cache_stats() -> Dict[str, Any]:
    """Получение статистики кэша конкурсов"""
    return {
        'contests': cache_manager.get_cache('contests').get_stats(),
        'stats': cache_manager.get_cache('stats').get_stats()
    }
