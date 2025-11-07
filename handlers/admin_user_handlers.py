"""
Админские обработчики пользователей
"""
import logging
from typing import Optional, Dict, Any, List
import telebot.types as types

from bot_instance import bot
from utils.simple_locks import simple_lock
from utils.markdown_utils import safe_markdown_v2
from utils.error_handler import error_handler, admin_error_handler
from handlers.decorator import private_chat_only
from menu.constants import ButtonCallback, ButtonText
from menu.menu import Menu
from services.user_service import UserService
from services.contest_service import ContestService

logger = logging.getLogger(__name__)


class AdminUserHandlers:
    """Класс для админских обработчиков пользователей"""
    
    @staticmethod
    def check_admin(call) -> bool:
        """
        Проверка прав администратора
        
        Args:
            call: Callback query
            
        Returns:
            True если админ
        """
        if not UserService.is_admin(call.from_user.id):
            bot.answer_callback_query(
                call.id,
                "⚠️ Вы не являетесь админом\n\nВы вообще как сюда попали???",
                show_alert=True
            )
            return False
        return True
    
    @staticmethod
    def handle_user_menu(call):
        """Обработка меню пользователей для админа"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            text = safe_markdown_v2(
                "👥 *Управление пользователями*\n\n"
                "Выберите действие:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🚫 Заблокированные",
                    callback_data=ButtonCallback.ADM_USERS_BLOCKED
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "✅ Одобренные",
                    callback_data=ButtonCallback.ADM_USERS_APPROVED
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "👨‍⚖️ Судьи",
                    callback_data=ButtonCallback.ADM_USERS_JUDGES
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "📊 Статистика",
                    callback_data=ButtonCallback.ADM_USERS_STATS
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 В главное меню",
                    callback_data=ButtonCallback.ADM_MAIN_MENU
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"User menu error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при открытии меню пользователей",
                show_alert=True
            )
    
    @staticmethod
    def handle_blocked_users(call):
        """Обработка просмотра заблокированных пользователей"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            blocked_users = UserService.get_blocked_users()
            
            if not blocked_users:
                text = safe_markdown_v2(
                    "🚫 *Заблокированные пользователи*\n\n"
                    "❌ Заблокированных пользователей нет"
                )
            else:
                text = safe_markdown_v2(
                    f"🚫 *Заблокированные пользователи*\n\n"
                    f"📊 *Всего заблокировано:* {len(blocked_users)}\n\n"
                    "Выберите пользователя для разблокировки:"
                )
            
            markup = types.InlineKeyboardMarkup()
            
            # Добавляем кнопки для каждого заблокированного пользователя
            for user in blocked_users[:10]:  # Показываем первые 10
                user_id = user[0]
                reason = user[1] if len(user) > 1 else "Не указана"
                markup.add(
                    types.InlineKeyboardButton(
                        f"👤 ID: {user_id}",
                        callback_data=f"unblock_user_{user_id}"
                    )
                )
            
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_USERS
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Blocked users error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении списка заблокированных",
                show_alert=True
            )
    
    @staticmethod
    def handle_approved_users(call):
        """Обработка просмотра одобренных пользователей"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            # Здесь должна быть логика получения одобренных пользователей
            # Пока что заглушка
            text = safe_markdown_v2(
                "✅ *Одобренные пользователи*\n\n"
                "📊 *Функция в разработке*\n\n"
                "Здесь будет список одобренных пользователей"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_USERS
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Approved users error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении списка одобренных",
                show_alert=True
            )
    
    @staticmethod
    def handle_judges(call):
        """Обработка просмотра судей"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            # Здесь должна быть логика получения судей
            # Пока что заглушка
            text = safe_markdown_v2(
                "👨‍⚖️ *Судьи*\n\n"
                "📊 *Функция в разработке*\n\n"
                "Здесь будет список судей"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_USERS
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Judges error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении списка судей",
                show_alert=True
            )
    
    @staticmethod
    def handle_user_stats(call):
        """Обработка статистики пользователей"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            # Получаем статистику
            contest_stats = ContestService.get_contest_statistics()
            
            text = safe_markdown_v2(
                f"📊 *Статистика пользователей*\n\n"
                f"👥 *Всего участников:* {contest_stats.get('participants', 0)}\n"
                f"📝 *Всего заявок:* {contest_stats.get('total', 0)}\n"
                f"⏳ *Ожидают рассмотрения:* {contest_stats.get('pending', 0)}\n"
                f"✅ *Одобрено:* {contest_stats.get('approved', 0)}\n"
                f"❌ *Отклонено:* {contest_stats.get('rejected', 0)}\n\n"
                f"🚫 *Заблокировано:* {len(UserService.get_blocked_users())}"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_USERS
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"User stats error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении статистики",
                show_alert=True
            )
    
    @staticmethod
    def handle_unblock_user(call):
        """Обработка разблокировки пользователя"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            # Извлекаем ID пользователя из callback_data
            user_id = int(call.data.split("_")[-1])
            
            # Разблокируем пользователя
            success = UserService.unblock_user(user_id)
            
            if success:
                bot.answer_callback_query(
                    call.id,
                    f"✅ Пользователь {user_id} разблокирован",
                    show_alert=True
                )
                
                # Обновляем список заблокированных
                AdminUserHandlers.handle_blocked_users(call)
            else:
                bot.answer_callback_query(
                    call.id,
                    f"❌ Ошибка при разблокировке пользователя {user_id}",
                    show_alert=True
                )
                
        except Exception as e:
            logger.error(f"Unblock user error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при разблокировке",
                show_alert=True
            )
    
    @staticmethod
    def handle_block_user(call):
        """Обработка блокировки пользователя"""
        try:
            if not AdminUserHandlers.check_admin(call):
                return
            
            # Извлекаем ID пользователя из callback_data
            user_id = int(call.data.split("_")[-1])
            
            # Блокируем пользователя
            success = UserService.block_user(user_id, "Заблокирован администратором")
            
            if success:
                bot.answer_callback_query(
                    call.id,
                    f"✅ Пользователь {user_id} заблокирован",
                    show_alert=True
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    f"❌ Ошибка при блокировке пользователя {user_id}",
                    show_alert=True
                )
                
        except Exception as e:
            logger.error(f"Block user error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при блокировке",
                show_alert=True
            )


# Регистрация обработчиков
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_USERS)
@simple_lock()
@private_chat_only(bot)
def handle_adm_users(call):
    """Обработчик меню пользователей для админа"""
    AdminUserHandlers.handle_user_menu(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_USERS_BLOCKED)
@simple_lock()
@private_chat_only(bot)
def handle_adm_users_blocked(call):
    """Обработчик просмотра заблокированных пользователей"""
    AdminUserHandlers.handle_blocked_users(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_USERS_APPROVED)
@simple_lock()
@private_chat_only(bot)
def handle_adm_users_approved(call):
    """Обработчик просмотра одобренных пользователей"""
    AdminUserHandlers.handle_approved_users(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_USERS_JUDGES)
@simple_lock()
@private_chat_only(bot)
def handle_adm_users_judges(call):
    """Обработчик просмотра судей"""
    AdminUserHandlers.handle_judges(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_USERS_STATS)
@simple_lock()
@private_chat_only(bot)
def handle_adm_users_stats(call):
    """Обработчик статистики пользователей"""
    AdminUserHandlers.handle_user_stats(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_user_"))
@simple_lock()
@private_chat_only(bot)
def handle_unblock_user(call):
    """Обработчик разблокировки пользователя"""
    AdminUserHandlers.handle_unblock_user(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith("block_user_"))
@simple_lock()
@private_chat_only(bot)
def handle_block_user(call):
    """Обработчик блокировки пользователя"""
    AdminUserHandlers.handle_block_user(call)
