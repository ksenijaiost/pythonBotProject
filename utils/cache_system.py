"""
Система кэширования для Telegram бота
"""
import time
import threading
import logging
from typing import Any, Dict, Optional, Callable, Union
from collections import OrderedDict
from functools import wraps
import json

logger = logging.getLogger(__name__)


class CacheItem:
    """Элемент кэша с временем жизни"""
    
    def __init__(self, value: Any, ttl: float = 300.0):
        """
        Args:
            value: Значение для кэширования
            ttl: Время жизни в секундах (по умолчанию 5 минут)
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Проверка истечения времени жизни"""
        return time.time() - self.created_at > self.ttl
    
    def get_value(self) -> Any:
        """Получение значения (None если истекло)"""
        if self.is_expired():
            return None
        return self.value


class LRUCache:
    """LRU кэш с поддержкой TTL"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        """
        Args:
            max_size: Максимальный размер кэша
            default_ttl: Время жизни по умолчанию в секундах
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheItem] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша
        
        Args:
            key: Ключ
            
        Returns:
            Значение или None если не найдено/истекло
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            item = self._cache[key]
            
            # Проверяем истечение
            if item.is_expired():
                del self._cache[key]
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None
            
            # Перемещаем в конец (LRU)
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            return item.get_value()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Сохранение значения в кэш
        
        Args:
            key: Ключ
            value: Значение
            ttl: Время жизни (если None, используется default_ttl)
        """
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # Удаляем старый элемент если есть
            if key in self._cache:
                del self._cache[key]
            
            # Проверяем размер кэша
            while len(self._cache) >= self.max_size:
                # Удаляем самый старый элемент
                oldest_key, _ = self._cache.popitem(last=False)
                self._stats['evictions'] += 1
            
            # Добавляем новый элемент
            self._cache[key] = CacheItem(value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Удаление элемента из кэша
        
        Args:
            key: Ключ
            
        Returns:
            True если элемент был удален
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Очистка истекших элементов
        
        Returns:
            Количество удаленных элементов
        """
        with self._lock:
            expired_keys = []
            for key, item in self._cache.items():
                if item.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expired'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'expired': self._stats['expired']
            }
    
    def keys(self) -> list:
        """Получение всех ключей"""
        with self._lock:
            return list(self._cache.keys())


class CacheManager:
    """Менеджер кэширования с разными типами кэшей"""
    
    def __init__(self):
        self._caches: Dict[str, LRUCache] = {}
        self._lock = threading.RLock()
        
        # Создаем кэши для разных типов данных
        self._create_default_caches()
        
        # Запускаем фоновую очистку
        self._start_cleanup_thread()
    
    def _create_default_caches(self):
        """Создание кэшей по умолчанию"""
        # Кэш для данных конкурсов (долгий TTL)
        self._caches['contests'] = LRUCache(max_size=100, default_ttl=1800.0)  # 30 минут
        
        # Кэш для пользовательских данных (средний TTL)
        self._caches['users'] = LRUCache(max_size=500, default_ttl=600.0)  # 10 минут
        
        # Кэш для статистики (короткий TTL)
        self._caches['stats'] = LRUCache(max_size=50, default_ttl=300.0)  # 5 минут
        
        # Кэш для админов и судей (долгий TTL)
        self._caches['permissions'] = LRUCache(max_size=200, default_ttl=3600.0)  # 1 час
        
        # Кэш для состояний пользователей (короткий TTL)
        self._caches['states'] = LRUCache(max_size=1000, default_ttl=1800.0)  # 30 минут
    
    def _start_cleanup_thread(self):
        """Запуск фоновой очистки кэша"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Очистка каждые 5 минут
                    self.cleanup_all_expired()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Cache cleanup thread started")
    
    def get_cache(self, cache_name: str) -> LRUCache:
        """Получение кэша по имени"""
        with self._lock:
            if cache_name not in self._caches:
                self._caches[cache_name] = LRUCache()
            return self._caches[cache_name]
    
    def get(self, cache_name: str, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        cache = self.get_cache(cache_name)
        return cache.get(key)
    
    def set(self, cache_name: str, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Сохранение значения в кэш"""
        cache = self.get_cache(cache_name)
        cache.set(key, value, ttl)
    
    def delete(self, cache_name: str, key: str) -> bool:
        """Удаление значения из кэша"""
        cache = self.get_cache(cache_name)
        return cache.delete(key)
    
    def clear_cache(self, cache_name: str) -> None:
        """Очистка конкретного кэша"""
        cache = self.get_cache(cache_name)
        cache.clear()
    
    def clear_all(self) -> None:
        """Очистка всех кэшей"""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """Очистка истекших элементов во всех кэшах"""
        results = {}
        with self._lock:
            for name, cache in self._caches.items():
                cleaned = cache.cleanup_expired()
                if cleaned > 0:
                    results[name] = cleaned
        
        if results:
            logger.info(f"Cleaned expired cache items: {results}")
        
        return results
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Получение статистики всех кэшей"""
        with self._lock:
            return {name: cache.get_stats() for name, cache in self._caches.items()}
    
    def invalidate_pattern(self, cache_name: str, pattern: str) -> int:
        """
        Инвалидация кэша по паттерну
        
        Args:
            cache_name: Имя кэша
            pattern: Паттерн для поиска ключей
            
        Returns:
            Количество удаленных элементов
        """
        cache = self.get_cache(cache_name)
        keys_to_delete = []
        
        for key in cache.keys():
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache.delete(key)
        
        return len(keys_to_delete)


# Глобальный экземпляр менеджера кэша
cache_manager = CacheManager()


def cached(cache_name: str, ttl: Optional[float] = None, key_func: Optional[Callable] = None):
    """
    Декоратор для кэширования результатов функций
    
    Args:
        cache_name: Имя кэша
        ttl: Время жизни в секундах
        key_func: Функция для генерации ключа кэша
    
    Example:
        @cached('contests', ttl=1800)
        def get_current_contest():
            return ContestManager.get_current_contest()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Простая генерация ключа
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in kwargs.items()])
                cache_key = f"{func.__name__}:{':'.join(key_parts)}"
            
            # Пытаемся получить из кэша
            cached_value = cache_manager.get(cache_name, cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_name}:{cache_key}")
                return cached_value
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache_manager.set(cache_name, cache_key, result, ttl)
            logger.debug(f"Cache miss: {cache_name}:{cache_key}")
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(cache_name: str, pattern: str = None):
    """
    Декоратор для инвалидации кэша после выполнения функции
    
    Args:
        cache_name: Имя кэша
        pattern: Паттерн для инвалидации (если None, очищается весь кэш)
    
    Example:
        @cache_invalidate('contests')
        def create_contest(theme, description):
            return ContestManager.create_contest(theme, description)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Инвалидируем кэш
            if pattern:
                cache_manager.invalidate_pattern(cache_name, pattern)
            else:
                cache_manager.clear_cache(cache_name)
            
            logger.debug(f"Cache invalidated: {cache_name}")
            return result
        
        return wrapper
    return decorator


# Утилиты для работы с кэшем
def get_cached_contest_data(contest_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Получение данных конкурса из кэша"""
    key = f"current_contest" if contest_id is None else f"contest_{contest_id}"
    return cache_manager.get('contests', key)


def set_cached_contest_data(contest_data: Dict[str, Any], contest_id: Optional[int] = None) -> None:
    """Сохранение данных конкурса в кэш"""
    key = f"current_contest" if contest_id is None else f"contest_{contest_id}"
    cache_manager.set('contests', key, contest_data, ttl=1800.0)  # 30 минут


def get_cached_user_data(user_id: int, data_type: str) -> Optional[Any]:
    """Получение пользовательских данных из кэша"""
    key = f"user_{user_id}_{data_type}"
    return cache_manager.get('users', key)


def set_cached_user_data(user_id: int, data_type: str, data: Any, ttl: float = 600.0) -> None:
    """Сохранение пользовательских данных в кэш"""
    key = f"user_{user_id}_{data_type}"
    cache_manager.set('users', key, data, ttl)


def get_cached_stats(stats_type: str) -> Optional[Dict[str, Any]]:
    """Получение статистики из кэша"""
    return cache_manager.get('stats', stats_type)


def set_cached_stats(stats_type: str, stats_data: Dict[str, Any]) -> None:
    """Сохранение статистики в кэш"""
    cache_manager.set('stats', stats_type, stats_data, ttl=300.0)  # 5 минут


def is_cached_admin(user_id: int) -> Optional[bool]:
    """Проверка кэшированного статуса админа"""
    return cache_manager.get('permissions', f"admin_{user_id}")


def set_cached_admin(user_id: int, is_admin: bool) -> None:
    """Сохранение статуса админа в кэш"""
    cache_manager.set('permissions', f"admin_{user_id}", is_admin, ttl=3600.0)  # 1 час


def is_cached_judge(user_id: int) -> Optional[bool]:
    """Проверка кэшированного статуса судьи"""
    return cache_manager.get('permissions', f"judge_{user_id}")


def set_cached_judge(user_id: int, is_judge: bool) -> None:
    """Сохранение статуса судьи в кэш"""
    cache_manager.set('permissions', f"judge_{user_id}", is_judge, ttl=3600.0)  # 1 час
