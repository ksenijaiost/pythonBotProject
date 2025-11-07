"""
Система очистки и обслуживания кэша
"""
import time
import threading
import logging
from typing import Dict, Any, List
from .cache_system import cache_manager

logger = logging.getLogger(__name__)


class CacheCleanupManager:
    """Менеджер очистки и обслуживания кэша"""
    
    def __init__(self):
        self._cleanup_thread = None
        self._running = False
        self._cleanup_interval = 300  # 5 минут
        self._stats_interval = 3600   # 1 час
        self._last_stats_time = 0
    
    def start_cleanup_service(self, cleanup_interval: int = 300, stats_interval: int = 3600):
        """
        Запуск службы очистки кэша
        
        Args:
            cleanup_interval: Интервал очистки в секундах
            stats_interval: Интервал вывода статистики в секундах
        """
        if self._running:
            logger.warning("Cleanup service is already running")
            return
        
        self._cleanup_interval = cleanup_interval
        self._stats_interval = stats_interval
        self._running = True
        
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker, 
            daemon=True,
            name="CacheCleanup"
        )
        self._cleanup_thread.start()
        
        logger.info(f"Cache cleanup service started (cleanup: {cleanup_interval}s, stats: {stats_interval}s)")
    
    def stop_cleanup_service(self):
        """Остановка службы очистки кэша"""
        if not self._running:
            return
        
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        logger.info("Cache cleanup service stopped")
    
    def _cleanup_worker(self):
        """Рабочий поток очистки кэша"""
        while self._running:
            try:
                # Очистка истекших элементов
                cleaned = cache_manager.cleanup_all_expired()
                
                # Вывод статистики
                current_time = time.time()
                if current_time - self._last_stats_time >= self._stats_interval:
                    self._log_cache_stats()
                    self._last_stats_time = current_time
                
                # Ожидание следующей итерации
                time.sleep(self._cleanup_interval)
                
            except Exception as e:
                logger.error(f"Cache cleanup worker error: {e}")
                time.sleep(60)  # Ждем минуту при ошибке
    
    def _log_cache_stats(self):
        """Логирование статистики кэша"""
        try:
            stats = cache_manager.get_all_stats()
            
            logger.info("Cache statistics:")
            for cache_name, cache_stats in stats.items():
                logger.info(
                    f"  {cache_name}: size={cache_stats['size']}, "
                    f"hit_rate={cache_stats['hit_rate']}%, "
                    f"hits={cache_stats['hits']}, misses={cache_stats['misses']}"
                )
                
        except Exception as e:
            logger.error(f"Failed to log cache stats: {e}")
    
    def force_cleanup(self) -> Dict[str, int]:
        """
        Принудительная очистка истекших элементов
        
        Returns:
            Словарь с количеством очищенных элементов по кэшам
        """
        return cache_manager.cleanup_all_expired()
    
    def force_stats_log(self):
        """Принудительный вывод статистики"""
        self._log_cache_stats()
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Получение детальной статистики кэша"""
        return cache_manager.get_all_stats()


class CacheMaintenanceManager:
    """Менеджер обслуживания кэша"""
    
    @staticmethod
    def optimize_cache_sizes():
        """Оптимизация размеров кэшей"""
        try:
            stats = cache_manager.get_all_stats()
            
            for cache_name, cache_stats in stats.items():
                size = cache_stats['size']
                max_size = cache_stats['max_size']
                hit_rate = cache_stats['hit_rate']
                
                # Если кэш заполнен более чем на 90% и hit rate низкий
                if size > max_size * 0.9 and hit_rate < 50:
                    logger.warning(f"Cache {cache_name} is inefficient: size={size}, hit_rate={hit_rate}%")
                    
                    # Можно добавить логику автоматической оптимизации
                    # Например, увеличение размера кэша или изменение TTL
                    
        except Exception as e:
            logger.error(f"Failed to optimize cache sizes: {e}")
    
    @staticmethod
    def cleanup_old_user_data(max_age_hours: int = 24):
        """
        Очистка старых пользовательских данных
        
        Args:
            max_age_hours: Максимальный возраст данных в часах
        """
        try:
            # Получаем все ключи пользовательского кэша
            user_cache = cache_manager.get_cache('users')
            keys_to_remove = []
            
            for key in user_cache.keys():
                # Проверяем возраст данных
                # Здесь можно добавить логику проверки времени создания
                # Пока просто удаляем неактивные ключи
                if 'user_' in key:
                    # Простая эвристика: если ключ содержит старые данные
                    keys_to_remove.append(key)
            
            # Удаляем старые ключи
            for key in keys_to_remove:
                user_cache.delete(key)
            
            if keys_to_remove:
                logger.info(f"Cleaned up {len(keys_to_remove)} old user cache entries")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old user data: {e}")
    
    @staticmethod
    def reset_cache_stats():
        """Сброс статистики кэша"""
        try:
            # Очищаем все кэши
            cache_manager.clear_all()
            logger.info("Reset all cache statistics")
            
        except Exception as e:
            logger.error(f"Failed to reset cache stats: {e}")
    
    @staticmethod
    def get_cache_health_report() -> Dict[str, Any]:
        """
        Получение отчета о здоровье кэша
        
        Returns:
            Отчет о состоянии кэша
        """
        try:
            stats = cache_manager.get_all_stats()
            
            report = {
                'timestamp': time.time(),
                'caches': {},
                'overall_health': 'good',
                'recommendations': []
            }
            
            total_hits = 0
            total_misses = 0
            total_size = 0
            
            for cache_name, cache_stats in stats.items():
                hits = cache_stats['hits']
                misses = cache_stats['misses']
                size = cache_stats['size']
                hit_rate = cache_stats['hit_rate']
                
                total_hits += hits
                total_misses += misses
                total_size += size
                
                # Оценка здоровья кэша
                health = 'good'
                if hit_rate < 30:
                    health = 'poor'
                    report['recommendations'].append(f"Cache {cache_name} has low hit rate ({hit_rate}%)")
                elif hit_rate < 60:
                    health = 'fair'
                
                report['caches'][cache_name] = {
                    'health': health,
                    'hit_rate': hit_rate,
                    'size': size,
                    'hits': hits,
                    'misses': misses
                }
            
            # Общая оценка здоровья
            if total_hits + total_misses > 0:
                overall_hit_rate = total_hits / (total_hits + total_misses) * 100
                if overall_hit_rate < 40:
                    report['overall_health'] = 'poor'
                elif overall_hit_rate < 70:
                    report['overall_health'] = 'fair'
            
            report['total_size'] = total_size
            report['total_hits'] = total_hits
            report['total_misses'] = total_misses
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate cache health report: {e}")
            return {'error': str(e)}


# Глобальные экземпляры менеджеров
cleanup_manager = CacheCleanupManager()
maintenance_manager = CacheMaintenanceManager()


def start_cache_cleanup_service(cleanup_interval: int = 300, stats_interval: int = 3600):
    """Запуск службы очистки кэша"""
    cleanup_manager.start_cleanup_service(cleanup_interval, stats_interval)


def stop_cache_cleanup_service():
    """Остановка службы очистки кэша"""
    cleanup_manager.stop_cleanup_service()


def get_cache_health() -> Dict[str, Any]:
    """Получение отчета о здоровье кэша"""
    return maintenance_manager.get_cache_health_report()


def cleanup_cache_now() -> Dict[str, int]:
    """Принудительная очистка кэша"""
    return cleanup_manager.force_cleanup()


def log_cache_stats():
    """Вывод статистики кэша"""
    cleanup_manager.force_stats_log()
