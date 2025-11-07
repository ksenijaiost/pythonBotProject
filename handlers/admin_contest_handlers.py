"""
Админские обработчики конкурсов
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import telebot.types as types

from bot_instance import bot
from utils.simple_locks import simple_lock
from utils.markdown_utils import safe_markdown_v2
from utils.error_handler import error_handler, admin_error_handler
from handlers.decorator import private_chat_only
from menu.constants import ButtonCallback, ButtonText, UserState
from menu.menu import Menu
from services.contest_service import ContestService
from services.user_service import UserService
from database.db_classes import user_content_storage

logger = logging.getLogger(__name__)


class AdminContestHandlers:
    """Класс для админских обработчиков конкурсов"""
    
    ADMIN_STEPS = {
        "theme": "Введите тему конкурса:",
        "description": "Введите описание:",
        "contest_date": "Введите дату проведения конкурса, через точку ДД ММ ГГГГ:",
        "end_date_of_admission": "Введите дату окончания приёма работ, через точку ДД ММ ГГГГ:",
    }
    
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
    def handle_contest_menu(call):
        """Обработка меню конкурсов для админа"""
        try:
            if not AdminContestHandlers.check_admin(call):
                return
            
            text = safe_markdown_v2(
                "🎨 *Управление конкурсами*\n\n"
                "Выберите действие:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "📋 Текущий конкурс",
                    callback_data=ButtonCallback.ADM_CONTEST_CURRENT
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "➕ Создать конкурс",
                    callback_data=ButtonCallback.ADM_CONTEST_CREATE
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "📊 Статистика",
                    callback_data=ButtonCallback.ADM_CONTEST_STATS
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "📝 Заявки",
                    callback_data=ButtonCallback.ADM_CONTEST_SUBMISSIONS
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
            logger.error(f"Contest menu error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при открытии меню конкурсов",
                show_alert=True
            )
    
    @staticmethod
    def handle_current_contest(call):
        """Обработка просмотра текущего конкурса"""
        try:
            if not AdminContestHandlers.check_admin(call):
                return
            
            contest = ContestService.get_current_contest()
            
            if not contest:
                text = safe_markdown_v2(
                    "📋 *Текущий конкурс*\n\n"
                    "❌ Активных конкурсов нет"
                )
            else:
                text = safe_markdown_v2(
                    f"📋 *Текущий конкурс*\n\n"
                    f"🎨 *Тема:* {contest.get('theme', 'Не указана')}\n"
                    f"📝 *Описание:* {contest.get('description', 'Не указано')}\n"
                    f"📅 *Дата проведения:* {contest.get('contest_date', 'Не указана')}\n"
                    f"⏰ *Прием работ до:* {contest.get('end_date_of_admission', 'Не указана')}\n"
                    f"🆔 *ID:* {contest.get('id', 'Не указан')}"
                )
            
            markup = types.InlineKeyboardMarkup()
            if contest:
                markup.add(
                    types.InlineKeyboardButton(
                        "✏️ Редактировать",
                        callback_data=f"edit_contest_{contest['id']}"
                    )
                )
                markup.add(
                    types.InlineKeyboardButton(
                        "🗑️ Удалить",
                        callback_data=f"delete_contest_{contest['id']}"
                    )
                )
            
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_CONTEST
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
            logger.error(f"Current contest error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении информации о конкурсе",
                show_alert=True
            )
    
    @staticmethod
    def handle_create_contest(call):
        """Обработка создания конкурса"""
        try:
            if not AdminContestHandlers.check_admin(call):
                return
            
            user_id = call.from_user.id
            
            # Очищаем временное хранилище
            if user_id in user_content_storage.data:
                del user_content_storage.data[user_id]
            
            # Устанавливаем состояние создания конкурса
            bot.set_state(user_id, UserState.ADMIN_CREATING_CONTEST)
            user_content_storage.set_data(user_id, "contest_creation", {"step": "theme"})
            
            text = safe_markdown_v2(
                "➕ *Создание нового конкурса*\n\n"
                "Введите тему конкурса:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data="cancel_contest_creation"
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
            logger.error(f"Create contest error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при создании конкурса",
                show_alert=True
            )
    
    @staticmethod
    def handle_contest_creation_text(message):
        """Обработка текста при создании конкурса"""
        try:
            user_id = message.from_user.id
            contest_data = user_content_storage.get_data(user_id, "contest_creation")
            step = contest_data.get("step")
            
            if step == "theme":
                contest_data["theme"] = message.text
                contest_data["step"] = "description"
                
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        "✅ *Тема сохранена*\n\n"
                        "Введите описание конкурса:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
            elif step == "description":
                contest_data["description"] = message.text
                contest_data["step"] = "contest_date"
                
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        "✅ *Описание сохранено*\n\n"
                        "Введите дату проведения конкурса в формате ДД\\.ММ\\.ГГГГ:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
            elif step == "contest_date":
                try:
                    # Парсим дату
                    date_obj = datetime.strptime(message.text, "%d.%m.%Y")
                    contest_data["contest_date"] = date_obj.strftime("%Y-%m-%d")
                    contest_data["step"] = "end_date_of_admission"
                    
                    bot.reply_to(
                        message,
                        safe_markdown_v2(
                            "✅ *Дата проведения сохранена*\n\n"
                            "Введите дату окончания приёма работ в формате ДД\\.ММ\\.ГГГГ:"
                        ),
                        parse_mode="MarkdownV2"
                    )
                    
                except ValueError:
                    bot.reply_to(
                        message,
                        safe_markdown_v2(
                            "❌ *Неверный формат даты*\n\n"
                            "Введите дату в формате ДД\\.ММ\\.ГГГГ\\.\n"
                            "Например: 25\\.12\\.2024"
                        ),
                        parse_mode="MarkdownV2"
                    )
                    
            elif step == "end_date_of_admission":
                try:
                    # Парсим дату
                    date_obj = datetime.strptime(message.text, "%d.%m.%Y")
                    contest_data["end_date_of_admission"] = date_obj.strftime("%Y-%m-%d")
                    
                    # Создаем конкурс
                    success = ContestService.create_contest(
                        theme=contest_data["theme"],
                        description=contest_data["description"],
                        contest_date=contest_data["contest_date"],
                        end_date=contest_data["end_date_of_admission"]
                    )
                    
                    if success:
                        # Очищаем временные данные
                        user_content_storage.clear(user_id)
                        bot.delete_state(user_id)
                        
                        bot.reply_to(
                            message,
                            safe_markdown_v2(
                                "✅ *Конкурс успешно создан\\!*\n\n"
                                f"🎨 *Тема:* {contest_data['theme']}\n"
                                f"📅 *Дата проведения:* {contest_data['contest_date']}\n"
                                f"⏰ *Прием работ до:* {contest_data['end_date_of_admission']}"
                            ),
                            parse_mode="MarkdownV2"
                        )
                        
                        # Показываем главное меню
                        main_menu = Menu.adm_menu()
                        bot.send_message(
                            user_id,
                            "Выберите действие:",
                            reply_markup=main_menu
                        )
                    else:
                        bot.reply_to(
                            message,
                            safe_markdown_v2(
                                "❌ *Ошибка при создании конкурса*\n\n"
                                "Попробуйте еще раз или обратитесь к разработчику\\."
                            ),
                            parse_mode="MarkdownV2"
                        )
                        
                except ValueError:
                    bot.reply_to(
                        message,
                        safe_markdown_v2(
                            "❌ *Неверный формат даты*\n\n"
                            "Введите дату в формате ДД\\.ММ\\.ГГГГ\\.\n"
                            "Например: 25\\.12\\.2024"
                        ),
                        parse_mode="MarkdownV2"
                    )
            
        except Exception as e:
            logger.error(f"Contest creation text error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке данных")
    
    @staticmethod
    def handle_contest_stats(call):
        """Обработка статистики конкурсов"""
        try:
            if not AdminContestHandlers.check_admin(call):
                return
            
            stats = ContestService.get_contest_statistics()
            
            text = safe_markdown_v2(
                f"📊 *Статистика конкурсов*\n\n"
                f"📝 *Всего заявок:* {stats.get('total', 0)}\n"
                f"⏳ *Ожидают рассмотрения:* {stats.get('pending', 0)}\n"
                f"✅ *Одобрено:* {stats.get('approved', 0)}\n"
                f"❌ *Отклонено:* {stats.get('rejected', 0)}\n\n"
                f"👥 *Участников:* {stats.get('participants', 0)}"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_CONTEST
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
            logger.error(f"Contest stats error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении статистики",
                show_alert=True
            )
    
    @staticmethod
    def handle_contest_submissions(call):
        """Обработка просмотра заявок"""
        try:
            if not AdminContestHandlers.check_admin(call):
                return
            
            submissions = ContestService.get_pending_submissions()
            
            if not submissions:
                text = safe_markdown_v2(
                    "📝 *Заявки на конкурс*\n\n"
                    "❌ Ожидающих заявок нет"
                )
            else:
                text = safe_markdown_v2(
                    f"📝 *Заявки на конкурс*\n\n"
                    f"⏳ *Ожидают рассмотрения:* {len(submissions)}\n\n"
                    "Выберите заявку для просмотра:"
                )
            
            markup = types.InlineKeyboardMarkup()
            
            # Добавляем кнопки для каждой заявки
            for submission in submissions[:10]:  # Показываем первые 10
                user_id = submission.get('user_id')
                submission_id = submission.get('id')
                markup.add(
                    types.InlineKeyboardButton(
                        f"👤 Заявка #{submission_id}",
                        callback_data=f"view_submission_{submission_id}"
                    )
                )
            
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.ADM_CONTEST
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
            logger.error(f"Contest submissions error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении заявок",
                show_alert=True
            )
    
    @staticmethod
    def handle_cancel_contest_creation(call):
        """Обработка отмены создания конкурса"""
        try:
            user_id = call.from_user.id
            
            # Очищаем временные данные
            user_content_storage.clear(user_id)
            bot.delete_state(user_id)
            
            # Подтверждаем отмену
            bot.answer_callback_query(
                call.id,
                "❌ Создание конкурса отменено",
                show_alert=True
            )
            
            # Возвращаемся в меню конкурсов
            AdminContestHandlers.handle_contest_menu(call)
            
        except Exception as e:
            logger.error(f"Cancel contest creation error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при отмене",
                show_alert=True
            )


# Регистрация обработчиков
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST)
@simple_lock()
@private_chat_only(bot)
def handle_adm_contest(call):
    """Обработчик меню конкурсов для админа"""
    AdminContestHandlers.handle_contest_menu(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_CURRENT)
@simple_lock()
@private_chat_only(bot)
def handle_adm_contest_current(call):
    """Обработчик просмотра текущего конкурса"""
    AdminContestHandlers.handle_current_contest(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_CREATE)
@simple_lock()
@private_chat_only(bot)
def handle_adm_contest_create(call):
    """Обработчик создания конкурса"""
    AdminContestHandlers.handle_create_contest(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_STATS)
@simple_lock()
@private_chat_only(bot)
def handle_adm_contest_stats(call):
    """Обработчик статистики конкурсов"""
    AdminContestHandlers.handle_contest_stats(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_SUBMISSIONS)
@simple_lock()
@private_chat_only(bot)
def handle_adm_contest_submissions(call):
    """Обработчик просмотра заявок"""
    AdminContestHandlers.handle_contest_submissions(call)


@bot.message_handler(
    content_types=["text"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.ADMIN_CREATING_CONTEST
        and not message.text.startswith("/")
    ),
)
@simple_lock()
def handle_contest_creation_text(message):
    """Обработчик текста при создании конкурса"""
    AdminContestHandlers.handle_contest_creation_text(message)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_contest_creation")
@simple_lock()
def handle_cancel_contest_creation(call):
    """Обработчик отмены создания конкурса"""
    AdminContestHandlers.handle_cancel_contest_creation(call)
