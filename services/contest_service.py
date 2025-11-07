"""
Сервис для работы с конкурсами
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.db_classes import ContestManager, SubmissionManager
from utils.contest_cache import ContestCacheManager, StatsCacheManager

logger = logging.getLogger(__name__)


class ContestService:
    """Сервис для работы с конкурсами"""
    
    @staticmethod
    def get_current_contest() -> Optional[Dict[str, Any]]:
        """
        Получение текущего конкурса
        
        Returns:
            Данные конкурса или None
        """
        try:
            # Пытаемся получить из кэша
            cached_contest = ContestCacheManager.get_current_contest()
            if cached_contest:
                return cached_contest
            
            # Получаем из базы данных
            contest = ContestManager.get_current_contest()
            if contest:
                # Кэшируем результат
                ContestCacheManager.set_current_contest(contest)
            
            return contest
            
        except Exception as e:
            logger.error(f"Failed to get current contest: {e}")
            return None
    
    @staticmethod
    def get_contest_by_id(contest_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение конкурса по ID
        
        Args:
            contest_id: ID конкурса
            
        Returns:
            Данные конкурса или None
        """
        try:
            # Пытаемся получить из кэша
            cached_contest = ContestCacheManager.get_contest_by_id(contest_id)
            if cached_contest:
                return cached_contest
            
            # Получаем из базы данных
            contest = ContestManager.get_contest_by_id(contest_id)
            if contest:
                # Кэшируем результат
                ContestCacheManager.set_contest_by_id(contest_id, contest)
            
            return contest
            
        except Exception as e:
            logger.error(f"Failed to get contest by ID {contest_id}: {e}")
            return None
    
    @staticmethod
    def create_contest(theme: str, description: str, contest_date: str, 
                      end_date: str) -> bool:
        """
        Создание нового конкурса
        
        Args:
            theme: Тема конкурса
            description: Описание
            contest_date: Дата проведения
            end_date: Дата окончания приема работ
            
        Returns:
            True если успешно создан
        """
        try:
            # Создаем конкурс в базе данных
            success = ContestManager.create_contest(
                theme=theme,
                description=description,
                contest_date=contest_date,
                end_date_of_admission=end_date
            )
            
            if success:
                # Инвалидируем кэш
                ContestCacheManager.invalidate_contest_cache()
                logger.info(f"Contest created: {theme}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create contest: {e}")
            return False
    
    @staticmethod
    def update_contest(contest_id: int, **kwargs) -> bool:
        """
        Обновление конкурса
        
        Args:
            contest_id: ID конкурса
            **kwargs: Поля для обновления
            
        Returns:
            True если успешно обновлен
        """
        try:
            # Обновляем в базе данных
            success = ContestManager.update_contest(contest_id, **kwargs)
            
            if success:
                # Инвалидируем кэш
                ContestCacheManager.invalidate_contest_cache(contest_id)
                logger.info(f"Contest {contest_id} updated")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update contest {contest_id}: {e}")
            return False
    
    @staticmethod
    def delete_contest(contest_id: int) -> bool:
        """
        Удаление конкурса
        
        Args:
            contest_id: ID конкурса
            
        Returns:
            True если успешно удален
        """
        try:
            # Удаляем из базы данных
            success = ContestManager.delete_contest(contest_id)
            
            if success:
                # Инвалидируем кэш
                ContestCacheManager.invalidate_contest_cache(contest_id)
                logger.info(f"Contest {contest_id} deleted")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete contest {contest_id}: {e}")
            return False
    
    @staticmethod
    def get_contest_statistics() -> Dict[str, Any]:
        """
        Получение статистики конкурса
        
        Returns:
            Словарь со статистикой
        """
        try:
            # Пытаемся получить из кэша
            cached_stats = StatsCacheManager.get_contest_statistics()
            if cached_stats:
                return cached_stats
            
            # Получаем из базы данных
            stats = SubmissionManager.get_contest_statistics()
            if stats:
                # Кэшируем результат
                StatsCacheManager.set_contest_statistics(stats)
            
            return stats or {}
            
        except Exception as e:
            logger.error(f"Failed to get contest statistics: {e}")
            return {}
    
    @staticmethod
    def get_pending_submissions() -> List[Dict[str, Any]]:
        """
        Получение ожидающих заявок
        
        Returns:
            Список заявок
        """
        try:
            # Пытаемся получить из кэша
            cached_submissions = StatsCacheManager.get_pending_submissions()
            if cached_submissions is not None:
                return cached_submissions
            
            # Получаем из базы данных
            submissions = SubmissionManager.get_pending_submissions()
            if submissions:
                # Кэшируем результат
                StatsCacheManager.set_pending_submissions(submissions)
            
            return submissions or []
            
        except Exception as e:
            logger.error(f"Failed to get pending submissions: {e}")
            return []
    
    @staticmethod
    def get_user_submission(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение заявки пользователя
        
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
    def create_submission(user_id: int, photos: List[str], 
                         description: str, status: str = "pending") -> bool:
        """
        Создание заявки на конкурс
        
        Args:
            user_id: ID пользователя
            photos: Список ID фотографий
            description: Описание работы
            status: Статус заявки
            
        Returns:
            True если успешно создана
        """
        try:
            # Создаем заявку в базе данных
            success = SubmissionManager.create_submission(
                user_id=user_id,
                photos=photos,
                description=description,
                status=status
            )
            
            if success:
                # Инвалидируем кэш статистики
                StatsCacheManager.invalidate_stats_cache()
                logger.info(f"Submission created for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create submission for user {user_id}: {e}")
            return False
    
    @staticmethod
    def update_submission(submission_id: int, **kwargs) -> bool:
        """
        Обновление заявки
        
        Args:
            submission_id: ID заявки
            **kwargs: Поля для обновления
            
        Returns:
            True если успешно обновлена
        """
        try:
            # Обновляем в базе данных
            success = SubmissionManager.update_submission(submission_id, **kwargs)
            
            if success:
                # Инвалидируем кэш статистики
                StatsCacheManager.invalidate_stats_cache()
                logger.info(f"Submission {submission_id} updated")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update submission {submission_id}: {e}")
            return False
    
    @staticmethod
    def approve_submission(submission_id: int) -> bool:
        """
        Одобрение заявки
        
        Args:
            submission_id: ID заявки
            
        Returns:
            True если успешно одобрена
        """
        try:
            return ContestService.update_submission(
                submission_id, 
                status="approved",
                approved_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to approve submission {submission_id}: {e}")
            return False
    
    @staticmethod
    def reject_submission(submission_id: int, reason: str = "") -> bool:
        """
        Отклонение заявки
        
        Args:
            submission_id: ID заявки
            reason: Причина отклонения
            
        Returns:
            True если успешно отклонена
        """
        try:
            return ContestService.update_submission(
                submission_id,
                status="rejected",
                rejection_reason=reason,
                rejected_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to reject submission {submission_id}: {e}")
            return False
    
    @staticmethod
    def get_contest_winners(contest_id: int) -> List[Dict[str, Any]]:
        """
        Получение победителей конкурса
        
        Args:
            contest_id: ID конкурса
            
        Returns:
            Список победителей
        """
        try:
            return SubmissionManager.get_contest_winners(contest_id)
            
        except Exception as e:
            logger.error(f"Failed to get contest winners {contest_id}: {e}")
            return []
    
    @staticmethod
    def is_contest_active(contest_id: int) -> bool:
        """
        Проверка активности конкурса
        
        Args:
            contest_id: ID конкурса
            
        Returns:
            True если конкурс активен
        """
        try:
            contest = ContestService.get_contest_by_id(contest_id)
            if not contest:
                return False
            
            end_date = datetime.strptime(contest["end_date_of_admission"], "%Y-%m-%d")
            return datetime.now().date() <= end_date.date()
            
        except Exception as e:
            logger.error(f"Failed to check contest activity {contest_id}: {e}")
            return False
