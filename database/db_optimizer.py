"""
Оптимизация базы данных: индексы, запросы и производительность
"""
import sqlite3
import logging
from typing import List, Dict, Any
from .db_connection import get_db_connection, db_transaction

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Класс для оптимизации базы данных"""
    
    @staticmethod
    def create_indexes():
        """
        Создание индексов для ускорения запросов
        
        Индексы создаются для часто используемых полей:
        - user_id в submissions (поиск по пользователю)
        - status в submissions (фильтрация по статусу)
        - timestamp в submissions (сортировка по времени)
        - user_id в approved_submissions (быстрый поиск одобренных)
        - user_id в judges (поиск судей)
        """
        
        indexes = [
            # Индексы для таблицы submissions
            "CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON submissions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status)",
            "CREATE INDEX IF NOT EXISTS idx_submissions_timestamp ON submissions(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_submissions_user_status ON submissions(user_id, status)",
            
            # Индексы для таблицы approved_submissions
            "CREATE INDEX IF NOT EXISTS idx_approved_user_id ON approved_submissions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_approved_submission_id ON approved_submissions(submission_id)",
            
            # Индексы для таблицы judges
            "CREATE INDEX IF NOT EXISTS idx_judges_user_id ON judges(user_id)",
            
            # Индексы для таблицы contests
            "CREATE INDEX IF NOT EXISTS idx_contests_date ON contests(contest_date)",
            "CREATE INDEX IF NOT EXISTS idx_contests_end_date ON contests(end_date_of_admission)",
        ]
        
        with db_transaction() as conn:
            cursor = conn.cursor()
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.info(f"Created index: {index_sql.split()[-1]}")
                except sqlite3.Error as e:
                    logger.warning(f"Failed to create index: {e}")
    
    @staticmethod
    def analyze_tables():
        """
        Анализ таблиц для оптимизации запросов
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Анализируем каждую таблицу
            tables = ["contests", "submissions", "approved_submissions", "judges", "counters"]
            
            for table in tables:
                try:
                    cursor.execute(f"ANALYZE {table}")
                    logger.info(f"Analyzed table: {table}")
                except sqlite3.Error as e:
                    logger.warning(f"Failed to analyze table {table}: {e}")
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """
        Получение статистики базы данных
        
        Returns:
            Словарь со статистикой
        """
        stats = {}
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Размер базы данных
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            result = cursor.fetchone()
            stats["database_size_bytes"] = result[0] if result else 0
            stats["database_size_mb"] = round(stats["database_size_bytes"] / (1024 * 1024), 2)
            
            # Количество записей в таблицах
            tables = ["contests", "submissions", "approved_submissions", "judges"]
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[f"{table}_count"] = count
                except sqlite3.Error:
                    stats[f"{table}_count"] = 0
            
            # Статистика по статусам submissions
            try:
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM submissions 
                    GROUP BY status
                """)
                status_stats = dict(cursor.fetchall())
                stats["submissions_by_status"] = status_stats
            except sqlite3.Error:
                stats["submissions_by_status"] = {}
            
            # Информация об индексах
            cursor.execute("""
                SELECT name, sql 
                FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = cursor.fetchall()
            stats["indexes"] = [{"name": name, "sql": sql} for name, sql in indexes]
            
            # Настройки SQLite
            pragma_settings = [
                "journal_mode", "synchronous", "cache_size", "temp_store", 
                "mmap_size", "foreign_keys", "busy_timeout"
            ]
            
            settings = {}
            for setting in pragma_settings:
                try:
                    cursor.execute(f"PRAGMA {setting}")
                    result = cursor.fetchone()
                    settings[setting] = result[0] if result else None
                except sqlite3.Error:
                    settings[setting] = None
            
            stats["sqlite_settings"] = settings
        
        return stats
    
    @staticmethod
    def optimize_database():
        """
        Полная оптимизация базы данных
        """
        logger.info("Starting database optimization...")
        
        # Создаем индексы
        DatabaseOptimizer.create_indexes()
        
        # Анализируем таблицы
        DatabaseOptimizer.analyze_tables()
        
        # Получаем статистику
        stats = DatabaseOptimizer.get_database_stats()
        
        logger.info(f"Database optimization completed. Stats: {stats}")
        return stats


class OptimizedQueries:
    """Оптимизированные SQL запросы"""
    
    @staticmethod
    def get_user_submissions(user_id: int) -> List[Dict[str, Any]]:
        """
        Получение всех заявок пользователя (оптимизированный запрос)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список заявок пользователя
        """
        query = """
            SELECT s.id, s.user_id, s.username, s.full_name, s.photos, 
                   s.caption, s.status, s.reason, s.submission_number, s.timestamp,
                   CASE WHEN a.submission_id IS NOT NULL THEN 1 ELSE 0 END as is_approved
            FROM submissions s
            LEFT JOIN approved_submissions a ON s.id = a.submission_id AND a.user_id = s.user_id
            WHERE s.user_id = ?
            ORDER BY s.timestamp DESC
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # Парсим JSON для photos
                if result['photos']:
                    import json
                    result['photos'] = json.loads(result['photos'])
                results.append(result)
            
            return results
    
    @staticmethod
    def get_pending_submissions_with_user_info() -> List[Dict[str, Any]]:
        """
        Получение ожидающих заявок с информацией о пользователях
        
        Returns:
            Список заявок с информацией о пользователях
        """
        query = """
            SELECT s.id, s.user_id, s.username, s.full_name, s.photos, 
                   s.caption, s.status, s.reason, s.submission_number, s.timestamp
            FROM submissions s
            WHERE s.status = 'pending'
            ORDER BY s.timestamp ASC
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # Парсим JSON для photos
                if result['photos']:
                    import json
                    result['photos'] = json.loads(result['photos'])
                results.append(result)
            
            return results
    
    @staticmethod
    def get_contest_statistics() -> Dict[str, int]:
        """
        Получение статистики конкурса
        
        Returns:
            Словарь со статистикой
        """
        query = """
            SELECT 
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count,
                COUNT(*) as total_count
            FROM submissions
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            
            return {
                "pending": result[0] or 0,
                "approved": result[1] or 0,
                "rejected": result[2] or 0,
                "total": result[3] or 0
            }
    
    @staticmethod
    def get_judges_count() -> int:
        """
        Получение количества судей
        
        Returns:
            Количество судей
        """
        query = "SELECT COUNT(*) FROM judges"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    @staticmethod
    def bulk_update_submissions(submission_updates: List[Dict[str, Any]]):
        """
        Массовое обновление заявок
        
        Args:
            submission_updates: Список обновлений в формате [{"id": 1, "status": "approved", "reason": "..."}]
        """
        if not submission_updates:
            return
        
        with db_transaction() as conn:
            cursor = conn.cursor()
            
            for update in submission_updates:
                submission_id = update.get("id")
                status = update.get("status")
                reason = update.get("reason")
                
                if submission_id and status:
                    cursor.execute(
                        "UPDATE submissions SET status = ?, reason = ? WHERE id = ?",
                        (status, reason, submission_id)
                    )
            
            logger.info(f"Bulk updated {len(submission_updates)} submissions")
    
    @staticmethod
    def cleanup_old_data(days_old: int = 30):
        """
        Очистка старых данных
        
        Args:
            days_old: Удалять данные старше указанного количества дней
        """
        with db_transaction() as conn:
            cursor = conn.cursor()
            
            # Удаляем старые отклоненные заявки
            cursor.execute("""
                DELETE FROM submissions 
                WHERE status = 'rejected' 
                AND datetime(timestamp) < datetime('now', '-{} days')
            """.format(days_old))
            
            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old rejected submissions")
            
            return deleted_count
