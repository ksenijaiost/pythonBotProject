"""
Сервис для работы с пользователями
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.db_classes import SubmissionManager
from utils.user_cache import UserCacheManager, PermissionCacheManager
from handlers.envParams import admin_ids

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """
        Проверка, является ли пользователь админом
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если админ
        """
        try:
            # Пытаемся получить из кэша
            cached_result = PermissionCacheManager.is_admin(user_id)
            if cached_result is not None:
                return cached_result
            
            # Проверяем в списке админов
            is_admin = user_id in admin_ids
            
            # Кэшируем результат
            PermissionCacheManager.set_admin(user_id, is_admin)
            
            return is_admin
            
        except Exception as e:
            logger.error(f"Failed to check admin status for user {user_id}: {e}")
            return False
    
    @staticmethod
    def is_judge(user_id: int) -> bool:
        """
        Проверка, является ли пользователь судьей
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если судья
        """
        try:
            # Пытаемся получить из кэша
            cached_result = PermissionCacheManager.is_judge(user_id)
            if cached_result is not None:
                return cached_result
            
            # Проверяем в базе данных
            is_judge = SubmissionManager.is_user_judge(user_id)
            
            # Кэшируем результат
            PermissionCacheManager.set_judge(user_id, is_judge)
            
            return is_judge
            
        except Exception as e:
            logger.error(f"Failed to check judge status for user {user_id}: {e}")
            return False
    
    @staticmethod
    def is_user_approved(user_id: int) -> bool:
        """
        Проверка, одобрен ли пользователь
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если одобрен
        """
        try:
            return SubmissionManager.is_user_approved(user_id)
            
        except Exception as e:
            logger.error(f"Failed to check approval status for user {user_id}: {e}")
            return False
    
    @staticmethod
    def get_user_submissions(user_id: int) -> List[Dict[str, Any]]:
        """
        Получение заявок пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список заявок
        """
        try:
            # Пытаемся получить из кэша
            cached_submissions = UserCacheManager.get_user_submissions(user_id)
            if cached_submissions is not None:
                return cached_submissions
            
            # Получаем из базы данных
            submissions = SubmissionManager.get_user_submissions(user_id)
            
            # Кэшируем результат
            UserCacheManager.set_user_submissions(user_id, submissions)
            
            return submissions
            
        except Exception as e:
            logger.error(f"Failed to get user submissions {user_id}: {e}")
            return []
    
    @staticmethod
    def get_user_submission(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение заявки пользователя на текущий конкурс
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Данные заявки или None
        """
        try:
            return SubmissionManager.get_user_submission(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get user submission {user_id}: {e}")
            return None
    
    @staticmethod
    def block_user(user_id: int, reason: str = "") -> bool:
        """
        Блокировка пользователя
        
        Args:
            user_id: ID пользователя
            reason: Причина блокировки
            
        Returns:
            True если успешно заблокирован
        """
        try:
            success = SubmissionManager.insert_replace_blocked(user_id, reason)
            
            if success:
                # Инвалидируем кэш пользователя
                UserCacheManager.invalidate_user_cache(user_id)
                logger.info(f"User {user_id} blocked: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to block user {user_id}: {e}")
            return False
    
    @staticmethod
    def unblock_user(user_id: int) -> bool:
        """
        Разблокировка пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно разблокирован
        """
        try:
            success = SubmissionManager.delete_blocked(user_id)
            
            if success:
                # Инвалидируем кэш пользователя
                UserCacheManager.invalidate_user_cache(user_id)
                logger.info(f"User {user_id} unblocked")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to unblock user {user_id}: {e}")
            return False
    
    @staticmethod
    def is_user_blocked(user_id: int) -> bool:
        """
        Проверка, заблокирован ли пользователь
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если заблокирован
        """
        try:
            return SubmissionManager.is_user_blocked(user_id)
            
        except Exception as e:
            logger.error(f"Failed to check block status for user {user_id}: {e}")
            return False
    
    @staticmethod
    def get_blocked_users() -> List[Dict[str, Any]]:
        """
        Получение списка заблокированных пользователей
        
        Returns:
            Список заблокированных пользователей
        """
        try:
            return SubmissionManager.select_blocked()
            
        except Exception as e:
            logger.error(f"Failed to get blocked users: {e}")
            return []
    
    @staticmethod
    def approve_user(user_id: int) -> bool:
        """
        Одобрение пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно одобрен
        """
        try:
            success = SubmissionManager.approve_user(user_id)
            
            if success:
                # Инвалидируем кэш пользователя
                UserCacheManager.invalidate_user_cache(user_id)
                logger.info(f"User {user_id} approved")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to approve user {user_id}: {e}")
            return False
    
    @staticmethod
    def get_user_statistics(user_id: int) -> Dict[str, Any]:
        """
        Получение статистики пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        try:
            submissions = UserService.get_user_submissions(user_id)
            
            stats = {
                "total_submissions": len(submissions),
                "approved_submissions": len([s for s in submissions if s.get("status") == "approved"]),
                "pending_submissions": len([s for s in submissions if s.get("status") == "pending"]),
                "rejected_submissions": len([s for s in submissions if s.get("status") == "rejected"]),
                "is_admin": UserService.is_admin(user_id),
                "is_judge": UserService.is_judge(user_id),
                "is_approved": UserService.is_user_approved(user_id),
                "is_blocked": UserService.is_user_blocked(user_id)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user statistics {user_id}: {e}")
            return {}
    
    @staticmethod
    def get_user_info(user_id: int) -> Dict[str, Any]:
        """
        Получение информации о пользователе
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с информацией о пользователе
        """
        try:
            stats = UserService.get_user_statistics(user_id)
            
            info = {
                "user_id": user_id,
                "statistics": stats,
                "last_activity": datetime.now().isoformat(),
                "permissions": {
                    "admin": stats.get("is_admin", False),
                    "judge": stats.get("is_judge", False),
                    "approved": stats.get("is_approved", False),
                    "blocked": stats.get("is_blocked", False)
                }
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get user info {user_id}: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    @staticmethod
    def cleanup_user_data(user_id: int) -> bool:
        """
        Очистка данных пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно очищено
        """
        try:
            # Очищаем кэш пользователя
            UserCacheManager.invalidate_user_cache(user_id)
            
            # Очищаем кэш прав доступа
            PermissionCacheManager.invalidate_permissions_cache()
            
            logger.info(f"User data cleaned up for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup user data {user_id}: {e}")
            return False
