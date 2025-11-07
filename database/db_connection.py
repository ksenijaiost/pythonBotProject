"""
Оптимизированное управление соединениями с базой данных SQLite
"""
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from typing import Optional, Generator, Any
import os

logger = logging.getLogger(__name__)


class SQLiteConnectionPool:
    """
    Пул соединений для SQLite с поддержкой многопоточности
    """
    
    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        """
        Инициализация пула соединений
        
        Args:
            db_path: Путь к файлу базы данных
            max_connections: Максимальное количество соединений
            timeout: Таймаут для получения соединения
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Пул доступных соединений
        self._available_connections = []
        # Активные соединения
        self._active_connections = set()
        # Блокировка для потокобезопасности
        self._lock = threading.RLock()
        # Событие для ожидания доступных соединений
        self._available_event = threading.Event()
        self._available_event.set()  # Изначально есть доступные соединения
        
        # Инициализируем начальные соединения
        self._initialize_connections()
        
        logger.info(f"SQLite connection pool initialized: {db_path}, max_connections={max_connections}")
    
    def _initialize_connections(self):
        """Инициализация начальных соединений"""
        for _ in range(min(3, self.max_connections)):  # Создаем 3 начальных соединения
            conn = self._create_connection()
            self._available_connections.append(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Создание нового соединения с оптимизациями"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False  # Разрешаем использование в разных потоках
        )
        
        # Оптимизации для производительности
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Баланс между скоростью и надежностью
        conn.execute("PRAGMA cache_size=10000")  # Увеличиваем кэш
        conn.execute("PRAGMA temp_store=MEMORY")  # Временные таблицы в памяти
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        
        # Включаем foreign keys
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Настройки для многопоточности
        conn.execute("PRAGMA busy_timeout=30000")  # 30 секунд ожидания
        
        return conn
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Получение соединения из пула
        
        Returns:
            Соединение с базой данных
            
        Raises:
            TimeoutError: Если не удалось получить соединение в течение timeout
        """
        start_time = time.time()
        
        with self._lock:
            # Ждем доступное соединение
            while not self._available_connections:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Timeout waiting for database connection after {self.timeout}s")
                
                # Если можем создать новое соединение
                if len(self._active_connections) < self.max_connections:
                    conn = self._create_connection()
                    self._active_connections.add(conn)
                    logger.debug(f"Created new connection, active: {len(self._active_connections)}")
                    return conn
                
                # Освобождаем блокировку и ждем
                self._lock.release()
                try:
                    self._available_event.wait(timeout=1.0)
                finally:
                    self._lock.acquire()
            
            # Берем соединение из пула
            conn = self._available_connections.pop()
            self._active_connections.add(conn)
            
            # Проверяем, что соединение еще валидно
            try:
                conn.execute("SELECT 1")
            except sqlite3.Error:
                # Соединение невалидно, создаем новое
                conn.close()
                conn = self._create_connection()
                self._active_connections.add(conn)
            
            logger.debug(f"Got connection from pool, active: {len(self._active_connections)}")
            return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """
        Возврат соединения в пул
        
        Args:
            conn: Соединение для возврата
        """
        with self._lock:
            if conn in self._active_connections:
                self._active_connections.remove(conn)
                
                # Откатываем незавершенные транзакции
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                
                # Возвращаем в пул или закрываем если пул переполнен
                if len(self._available_connections) < self.max_connections:
                    self._available_connections.append(conn)
                    self._available_event.set()
                    logger.debug(f"Returned connection to pool, available: {len(self._available_connections)}")
                else:
                    conn.close()
                    logger.debug("Closed excess connection")
            else:
                # Соединение не из нашего пула, просто закрываем
                conn.close()
    
    def close_all(self):
        """Закрытие всех соединений"""
        with self._lock:
            # Закрываем доступные соединения
            for conn in self._available_connections:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._available_connections.clear()
            
            # Закрываем активные соединения
            for conn in list(self._active_connections):
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._active_connections.clear()
            
            logger.info("All database connections closed")
    
    def get_stats(self) -> dict:
        """Получение статистики пула соединений"""
        with self._lock:
            return {
                "available_connections": len(self._available_connections),
                "active_connections": len(self._active_connections),
                "total_connections": len(self._available_connections) + len(self._active_connections),
                "max_connections": self.max_connections
            }


# Глобальный пул соединений
_connection_pool: Optional[SQLiteConnectionPool] = None


def initialize_connection_pool(db_path: str = "database/contests.db", max_connections: int = 10):
    """
    Инициализация глобального пула соединений
    
    Args:
        db_path: Путь к файлу базы данных
        max_connections: Максимальное количество соединений
    """
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.close_all()
    
    _connection_pool = SQLiteConnectionPool(db_path, max_connections)
    logger.info(f"Global connection pool initialized: {db_path}")


def get_connection_pool() -> SQLiteConnectionPool:
    """
    Получение глобального пула соединений
    
    Returns:
        Пул соединений
        
    Raises:
        RuntimeError: Если пул не инициализирован
    """
    if _connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call initialize_connection_pool() first.")
    return _connection_pool


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Контекстный менеджер для безопасной работы с базой данных
    
    Yields:
        Соединение с базой данных
        
    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    """
    pool = get_connection_pool()
    conn = None
    
    try:
        conn = pool.get_connection()
        yield conn
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if conn:
            pool.return_connection(conn)


@contextmanager
def db_transaction() -> Generator[sqlite3.Connection, None, None]:
    """
    Контекстный менеджер для транзакций
    
    Yields:
        Соединение с базой данных в транзакции
        
    Example:
        with db_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name) VALUES (?)", ("John",))
            cursor.execute("UPDATE stats SET count = count + 1")
            # Автоматический commit при выходе из контекста
    """
    with get_db_connection() as conn:
        try:
            yield conn
            conn.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise


def execute_query(query: str, params: tuple = (), fetch: str = "all") -> Any:
    """
    Выполнение SQL запроса с автоматическим управлением соединением
    
    Args:
        query: SQL запрос
        params: Параметры запроса
        fetch: Тип выборки ("all", "one", "none")
        
    Returns:
        Результат запроса
        
    Example:
        # Получить все записи
        users = execute_query("SELECT * FROM users")
        
        # Получить одну запись
        user = execute_query("SELECT * FROM users WHERE id = ?", (1,), "one")
        
        # Выполнить без результата
        execute_query("INSERT INTO users (name) VALUES (?)", ("John",), "none")
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == "all":
            return cursor.fetchall()
        elif fetch == "one":
            return cursor.fetchone()
        elif fetch == "none":
            return cursor.lastrowid
        else:
            raise ValueError(f"Invalid fetch type: {fetch}")


def execute_transaction(queries: list, params_list: list = None) -> list:
    """
    Выполнение нескольких запросов в одной транзакции
    
    Args:
        queries: Список SQL запросов
        params_list: Список параметров для каждого запроса
        
    Returns:
        Список результатов
        
    Example:
        queries = [
            "INSERT INTO users (name) VALUES (?)",
            "INSERT INTO logs (user_id, action) VALUES (?, ?)"
        ]
        params = [("John",), (1, "created")]
        results = execute_transaction(queries, params)
    """
    if params_list is None:
        params_list = [()] * len(queries)
    
    if len(queries) != len(params_list):
        raise ValueError("Number of queries must match number of parameter lists")
    
    with db_transaction() as conn:
        cursor = conn.cursor()
        results = []
        
        for query, params in zip(queries, params_list):
            cursor.execute(query, params)
            results.append(cursor.lastrowid)
        
        return results
