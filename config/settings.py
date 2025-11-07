"""
Конфигурация бота
"""
import os
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str
    mode: str = "polling"
    webhook_url: Optional[str] = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8443
    webhook_path: str = "/webhook"
    
    def __post_init__(self):
        if not self.token:
            raise ValueError("BOT_TOKEN is required")


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    path: str = "database/contests.db"
    max_connections: int = 10
    timeout: float = 30.0
    
    def __post_init__(self):
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(self.path), exist_ok=True)


@dataclass
class CacheConfig:
    """Конфигурация кэша"""
    max_size: int = 1000
    default_ttl: float = 3600.0
    cleanup_interval: int = 300
    stats_interval: int = 3600


@dataclass
class LoggingConfig:
    """Конфигурация логирования"""
    level: str = "INFO"
    filename: str = "bot.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class ChatConfig:
    """Конфигурация чатов"""
    admin_chat_id: int
    newspaper_chat_id: int
    contest_chat_id: int
    chat_id: int
    admin_username: str
    chat_username: str
    
    def __post_init__(self):
        if not all([self.admin_chat_id, self.newspaper_chat_id, 
                   self.contest_chat_id, self.chat_id]):
            raise ValueError("All chat IDs are required")


@dataclass
class AdminConfig:
    """Конфигурация администраторов"""
    admin_ids: List[int]
    news_ids: List[int]
    
    def __post_init__(self):
        if not self.admin_ids:
            raise ValueError("At least one admin ID is required")


@dataclass
class AppConfig:
    """Основная конфигурация приложения"""
    bot: BotConfig
    database: DatabaseConfig
    cache: CacheConfig
    logging: LoggingConfig
    chat: ChatConfig
    admin: AdminConfig
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Создание конфигурации из переменных окружения"""
        
        # Конфигурация бота
        bot_config = BotConfig(
            token=os.getenv("BOT_TOKEN", ""),
            mode=os.getenv("BOT_MODE", "polling"),
            webhook_url=os.getenv("WEBHOOK_URL"),
            webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
            webhook_port=int(os.getenv("WEBHOOK_PORT", "8443")),
            webhook_path=os.getenv("WEBHOOK_PATH", "/webhook")
        )
        
        # Конфигурация базы данных
        database_config = DatabaseConfig(
            path=os.getenv("DATABASE_PATH", "database/contests.db"),
            max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "10")),
            timeout=float(os.getenv("DB_TIMEOUT", "30.0"))
        )
        
        # Конфигурация кэша
        cache_config = CacheConfig(
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            default_ttl=float(os.getenv("CACHE_DEFAULT_TTL", "3600.0")),
            cleanup_interval=int(os.getenv("CACHE_CLEANUP_INTERVAL", "300")),
            stats_interval=int(os.getenv("CACHE_STATS_INTERVAL", "3600"))
        )
        
        # Конфигурация логирования
        logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            filename=os.getenv("LOG_FILENAME", "bot.log"),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            max_size=int(os.getenv("LOG_MAX_SIZE", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
        )
        
        # Конфигурация чатов
        chat_config = ChatConfig(
            admin_chat_id=int(os.getenv("ADMIN_CHAT_ID", "0")),
            newspaper_chat_id=int(os.getenv("NEWSPAPER_CHAT_ID", "0")),
            contest_chat_id=int(os.getenv("CONTEST_CHAT_ID", "0")),
            chat_id=int(os.getenv("CHAT_ID", "0")),
            admin_username=os.getenv("ADMIN_USERNAME", ""),
            chat_username=os.getenv("CHAT_USERNAME", "")
        )
        
        # Конфигурация администраторов
        admin_ids_str = os.getenv("ADMIN_ID_LIST", "")
        news_ids_str = os.getenv("NEWS_ID_LIST", "")
        
        admin_config = AdminConfig(
            admin_ids=[int(x.strip()) for x in admin_ids_str.split(",") if x.strip()],
            news_ids=[int(x.strip()) for x in news_ids_str.split(",") if x.strip()]
        )
        
        return cls(
            bot=bot_config,
            database=database_config,
            cache=cache_config,
            logging=logging_config,
            chat=chat_config,
            admin=admin_config
        )


# Глобальная конфигурация
config = AppConfig.from_env()


def get_config() -> AppConfig:
    """Получение конфигурации"""
    return config


def reload_config() -> AppConfig:
    """Перезагрузка конфигурации"""
    global config
    config = AppConfig.from_env()
    return config
