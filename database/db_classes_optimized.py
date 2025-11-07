"""
Оптимизированные классы для работы с базой данных
"""
from datetime import datetime
import json
import logging
from typing import List, Dict, Any, Optional

from .db_connection import get_db_connection, db_transaction, execute_query, execute_transaction
from .db_optimizer import DatabaseOptimizer, OptimizedQueries
from menu.constants import UserState

logger = logging.getLogger(__name__)


class OptimizedContestManager:
    """Оптимизированный менеджер конкурсов"""
    
    @staticmethod
    def initialize_database():
        """
        Инициализация базы данных с оптимизациями
        """
        # Создаем таблицы
        tables_sql = [
            # Таблица для инфо о конкурсе
            """CREATE TABLE IF NOT EXISTS contests
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                description TEXT NOT NULL,
                contest_date TEXT NOT NULL,
                end_date_of_admission TEXT NOT NULL)""",
            
            # Таблица для работ
            """CREATE TABLE IF NOT EXISTS submissions
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                photos TEXT NOT NULL,
                caption TEXT,
                status TEXT DEFAULT 'pending',
                reason TEXT,
                submission_number INTEGER,
                timestamp DATETIME)""",
            
            # Таблица для одобренных работ
            """CREATE TABLE IF NOT EXISTS approved_submissions (
                user_id INTEGER NOT NULL,
                submission_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, submission_id)
            )""",
            
            # Таблица для судей
            """CREATE TABLE IF NOT EXISTS judges
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL)""",
            
            # Таблица для счетчиков
            """CREATE TABLE IF NOT EXISTS counters
                (name TEXT PRIMARY KEY,
                value INTEGER NOT NULL)"""
        ]
        
        with db_transaction() as conn:
            cursor = conn.cursor()
            
            for table_sql in tables_sql:
                cursor.execute(table_sql)
            
            # Инициализируем счетчики
            cursor.execute("INSERT OR IGNORE INTO counters VALUES ('submission', 0)")
            cursor.execute("INSERT OR IGNORE INTO counters VALUES ('contest', 0)")
            cursor.execute("INSERT OR IGNORE INTO counters VALUES ('judge', 0)")
        
        # Создаем индексы и оптимизируем
        DatabaseOptimizer.optimize_database()
        
        logger.info("Database initialized and optimized")
    
    @staticmethod
    def create_contest(theme: str, description: str, contest_date: str, end_date: str) -> int:
        """
        Создание нового конкурса
        
        Args:
            theme: Тема конкурса
            description: Описание
            contest_date: Дата проведения
            end_date: Дата окончания приема работ
            
        Returns:
            ID созданного конкурса
        """
        query = """
            INSERT INTO contests (theme, description, contest_date, end_date_of_admission)
            VALUES (?, ?, ?, ?)
        """
        
        contest_id = execute_query(query, (theme, description, contest_date, end_date), "none")
        
        # Обновляем счетчик
        execute_query("UPDATE counters SET value = value + 1 WHERE name = 'contest'")
        
        logger.info(f"Created contest: {theme} (ID: {contest_id})")
        return contest_id
    
    @staticmethod
    def get_current_contest() -> Optional[Dict[str, Any]]:
        """
        Получение текущего конкурса
        
        Returns:
            Информация о текущем конкурсе или None
        """
        query = """
            SELECT id, theme, description, contest_date, end_date_of_admission
            FROM contests
            ORDER BY id DESC
            LIMIT 1
        """
        
        result = execute_query(query, fetch="one")
        
        if result:
            return {
                "id": result[0],
                "theme": result[1],
                "description": result[2],
                "contest_date": result[3],
                "end_date_of_admission": result[4]
            }
        
        return None
    
    @staticmethod
    def reset_contest_data():
        """Сброс данных конкурса"""
        queries = [
            "DELETE FROM contests",
            "UPDATE counters SET value = 0 WHERE name = 'contest'"
        ]
        
        execute_transaction(queries)
        logger.info("Contest data reset")


class OptimizedSubmissionManager:
    """Оптимизированный менеджер заявок"""
    
    @staticmethod
    def create_submission(user_id: int, username: str, full_name: str, photos: List[Dict], caption: str) -> int:
        """
        Создание новой заявки
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            full_name: Полное имя
            photos: Список фото
            caption: Подпись
            
        Returns:
            ID созданной заявки
        """
        # Получаем следующий номер заявки
        submission_number = execute_query(
            "SELECT value FROM counters WHERE name = 'submission'", 
            fetch="one"
        )[0] + 1
        
        query = """
            INSERT INTO submissions 
            (user_id, username, full_name, photos, caption, submission_number, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        submission_id = execute_query(
            query, 
            (
                user_id, username, full_name, json.dumps(photos), 
                caption, submission_number, datetime.now().isoformat()
            ), 
            "none"
        )
        
        # Обновляем счетчик
        execute_query("UPDATE counters SET value = ? WHERE name = 'submission'", (submission_number,))
        
        logger.info(f"Created submission {submission_id} for user {user_id}")
        return submission_id
    
    @staticmethod
    def get_pending_submissions() -> List[Dict[str, Any]]:
        """
        Получение ожидающих заявок
        
        Returns:
            Список ожидающих заявок
        """
        return OptimizedQueries.get_pending_submissions_with_user_info()
    
    @staticmethod
    def update_submission(submission_id: int, status: str, reason: Optional[str] = None):
        """
        Обновление заявки
        
        Args:
            submission_id: ID заявки
            status: Новый статус
            reason: Причина (опционально)
        """
        query = "UPDATE submissions SET status = ?, reason = ? WHERE id = ?"
        execute_query(query, (status, reason, submission_id))
        
        logger.info(f"Updated submission {submission_id} to status {status}")
    
    @staticmethod
    def get_user_submissions(user_id: int) -> List[Dict[str, Any]]:
        """
        Получение заявок пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список заявок пользователя
        """
        return OptimizedQueries.get_user_submissions(user_id)
    
    @staticmethod
    def approve_submission(user_id: int, submission_id: int):
        """
        Одобрение заявки
        
        Args:
            user_id: ID пользователя
            submission_id: ID заявки
        """
        queries = [
            "UPDATE submissions SET status = 'approved' WHERE id = ?",
            "INSERT OR IGNORE INTO approved_submissions (user_id, submission_id) VALUES (?, ?)"
        ]
        
        execute_transaction(queries, [(submission_id,), (user_id, submission_id)])
        
        logger.info(f"Approved submission {submission_id} for user {user_id}")
    
    @staticmethod
    def reject_submission(submission_id: int, reason: str):
        """
        Отклонение заявки
        
        Args:
            submission_id: ID заявки
            reason: Причина отклонения
        """
        query = "UPDATE submissions SET status = 'rejected', reason = ? WHERE id = ?"
        execute_query(query, (reason, submission_id))
        
        logger.info(f"Rejected submission {submission_id}: {reason}")
    
    @staticmethod
    def get_contest_statistics() -> Dict[str, int]:
        """
        Получение статистики конкурса
        
        Returns:
            Словарь со статистикой
        """
        return OptimizedQueries.get_contest_statistics()
    
    @staticmethod
    def bulk_update_submissions(updates: List[Dict[str, Any]]):
        """
        Массовое обновление заявок
        
        Args:
            updates: Список обновлений
        """
        OptimizedQueries.bulk_update_submissions(updates)


class OptimizedJudgeManager:
    """Оптимизированный менеджер судей"""
    
    @staticmethod
    def add_judge(user_id: int, username: str, full_name: str) -> int:
        """
        Добавление судьи
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            full_name: Полное имя
            
        Returns:
            ID созданной записи
        """
        query = """
            INSERT INTO judges (user_id, username, full_name)
            VALUES (?, ?, ?)
        """
        
        judge_id = execute_query(query, (user_id, username, full_name), "none")
        
        # Обновляем счетчик
        execute_query("UPDATE counters SET value = value + 1 WHERE name = 'judge'")
        
        logger.info(f"Added judge: {full_name} (ID: {judge_id})")
        return judge_id
    
    @staticmethod
    def is_user_judge(user_id: int) -> bool:
        """
        Проверка, является ли пользователь судьей
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если пользователь судья
        """
        query = "SELECT COUNT(*) FROM judges WHERE user_id = ?"
        result = execute_query(query, (user_id,), "one")
        return result[0] > 0 if result else False
    
    @staticmethod
    def get_judges_count() -> int:
        """
        Получение количества судей
        
        Returns:
            Количество судей
        """
        return OptimizedQueries.get_judges_count()
    
    @staticmethod
    def get_all_judges() -> List[Dict[str, Any]]:
        """
        Получение всех судей
        
        Returns:
            Список судей
        """
        query = "SELECT id, user_id, username, full_name FROM judges ORDER BY id"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results


class DatabaseManager:
    """Главный менеджер базы данных"""
    
    @staticmethod
    def initialize():
        """Инициализация всей базы данных"""
        OptimizedContestManager.initialize_database()
        logger.info("Database manager initialized")
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """Получение статистики базы данных"""
        return DatabaseOptimizer.get_database_stats()
    
    @staticmethod
    def cleanup_old_data(days_old: int = 30) -> int:
        """Очистка старых данных"""
        return OptimizedQueries.cleanup_old_data(days_old)
    
    @staticmethod
    def optimize():
        """Оптимизация базы данных"""
        return DatabaseOptimizer.optimize_database()


# Экспортируем оптимизированные классы
ContestManager = OptimizedContestManager
SubmissionManager = OptimizedSubmissionManager
JudgeManager = OptimizedJudgeManager
