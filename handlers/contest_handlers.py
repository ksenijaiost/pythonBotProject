"""
Обработчики конкурсов
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import telebot.types as types
from telebot.apihelper import ApiTelegramException

from bot_instance import bot
from utils.simple_locks import simple_lock, media_lock
from utils.markdown_utils import safe_markdown_v2
from handlers.decorator import private_chat_only
from handlers.envParams import ADMIN_CHAT_ID, CONTEST_CHAT_ID
from menu.constants import ButtonCallback, UserState
from database.db_classes import (
    ContestManager, 
    SubmissionManager, 
    user_submissions,
    user_content_storage
)

logger = logging.getLogger(__name__)


class ContestHandlers:
    """Класс для обработки конкурсов"""
    
    @staticmethod
    def format_date_ru(date_str: str) -> str:
        """Форматирование даты на русском языке"""
        MONTHS_RU = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return f"{date_obj.day} {MONTHS_RU[date_obj.month]} {date_obj.year}"
        except:
            return date_str
    
    @staticmethod
    def get_contest_info_text(contest: Dict[str, Any]) -> str:
        """Получение текста информации о конкурсе"""
        if not contest:
            return safe_markdown_v2(
                "🎉 В настоящее время активных конкурсов нет\n\n"
                "Следите за обновлениями ^^"
            )
        
        theme = contest.get("theme", "Не указана")
        description = contest.get("description", "Описание отсутствует")
        contest_date = contest.get("contest_date", "Не указана")
        end_date = contest.get("end_date_of_admission", "Не указана")
        
        # Форматируем даты
        contest_date_formatted = ContestHandlers.format_date_ru(contest_date)
        end_date_formatted = ContestHandlers.format_date_ru(end_date)
        
        text = safe_markdown_v2(
            f"🎨 *Тема конкурса:* {theme}\n\n"
            f"📝 *Описание:* {description}\n\n"
            f"📅 *Дата проведения:* {contest_date_formatted}\n"
            f"⏰ *Прием работ до:* {end_date_formatted}\n\n"
            "💡 *Как принять участие:*\n"
            "1\\. Нажмите кнопку «Отправить работу»\n"
            "2\\. Загрузите фото\\(я\\) вашей работы\n"
            "3\\. Добавьте описание\n"
            "4\\. Подтвердите отправку"
        )
        
        return text
    
    @staticmethod
    def handle_contest_info(call):
        """Обработка информации о конкурсе"""
        try:
            contest = ContestManager.get_current_contest()
            text = ContestHandlers.get_contest_info_text(contest)
            
            markup = types.InlineKeyboardMarkup()
            if contest:
                markup.add(
                    types.InlineKeyboardButton(
                        "📤 Отправить работу",
                        callback_data=ButtonCallback.USER_CONTEST_SEND
                    )
                )
            
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 В главное меню",
                    callback_data=ButtonCallback.USER_MAIN_MENU
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
            logger.error(f"Contest info error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при получении информации о конкурсе",
                show_alert=True
            )
    
    @staticmethod
    def handle_contest_submission(call):
        """Обработка отправки работы на конкурс"""
        try:
            user_id = call.from_user.id
            
            # Очищаем временное хранилище
            if user_id in user_content_storage.data:
                del user_content_storage.data[user_id]
            
            # Получаем данные о текущем конкурсе
            contest = ContestManager.get_current_contest()
            if not contest:
                bot.answer_callback_query(
                    call.id,
                    "🎉 В настоящее время активных конкурсов нет\n\nСледите за обновлениями ^^",
                    show_alert=True,
                )
                return
            
            # Проверяем, не отправил ли пользователь уже работу
            existing_submission = SubmissionManager.get_user_submission(user_id)
            if existing_submission:
                bot.answer_callback_query(
                    call.id,
                    "⚠️ Вы уже отправили работу на этот конкурс",
                    show_alert=True,
                )
                return
            
            # Создаем новую заявку
            submission = user_submissions.create_submission(user_id)
            
            # Устанавливаем состояние ожидания фото
            bot.set_state(user_id, UserState.WAITING_CONTEST_PHOTOS)
            
            # Отправляем инструкции
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=safe_markdown_v2(
                    "📸 *Отправка работы на конкурс*\n\n"
                    "Пожалуйста, отправьте фото\\(я\\) вашей работы\\.\n"
                    "Можно отправить до 10 фотографий\\.\n\n"
                    "💡 *Совет:* Отправляйте фото хорошего качества\\.\n\n"
                    "❌ Для отмены отправьте /cancel"
                ),
                parse_mode="MarkdownV2"
            )
            
        except Exception as e:
            logger.error(f"Contest submission error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при начале отправки работы",
                show_alert=True
            )
    
    @staticmethod
    def handle_contest_photos(message):
        """Обработка фото конкурсных работ"""
        user_id = message.from_user.id
        submission = user_submissions.get(user_id)
        
        if not submission:
            bot.reply_to(message, "❌ Сессия отправки истекла")
            return
        
        # Обновляем активность
        submission.update_activity()
        
        try:
            # Получаем фото
            photo = message.photo[-1]  # Берем фото наибольшего размера
            file_id = photo.file_id
            
            # Добавляем фото к заявке
            submission.add_photo(file_id)
            
            # Проверяем лимит фото
            if len(submission.photos) >= 10:
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        "✅ *Фото добавлено*\n\n"
                        "📸 *Достигнут лимит фотографий*\\(10 штук\\)\n\n"
                        "Теперь добавьте описание к работе:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
                # Переходим к этапу описания
                bot.set_state(user_id, UserState.WAITING_CONTEST_TEXT)
                ContestHandlers.request_contest_description(user_id)
                
            else:
                remaining = 10 - len(submission.photos)
                bot.reply_to(
                    message,
                    safe_markdown_v2(
                        f"✅ *Фото добавлено*\n\n"
                        f"📸 *Добавлено фотографий:* {len(submission.photos)}/10\n"
                        f"📷 *Осталось:* {remaining}\n\n"
                        f"Отправьте еще фото или напишите «Готово» для перехода к описанию:"
                    ),
                    parse_mode="MarkdownV2"
                )
                
        except Exception as e:
            logger.error(f"Photo handling error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке фото")
    
    @staticmethod
    def request_contest_description(user_id: int):
        """Запрос описания конкурсной работы"""
        bot.send_message(
            user_id,
            safe_markdown_v2(
                "📝 *Описание работы*\n\n"
                "Пожалуйста, добавьте описание к вашей работе\\.\n"
                "Расскажите о технике, материалах, идее и т\\.д\\.\n\n"
                "💡 *Совет:* Чем подробнее описание, тем лучше\\.\n\n"
                "❌ Для отмены отправьте /cancel"
            ),
            parse_mode="MarkdownV2"
        )
    
    @staticmethod
    def handle_contest_text(message):
        """Обработка текста описания конкурсной работы"""
        user_id = message.from_user.id
        submission = user_submissions.get(user_id)
        
        if not submission:
            bot.reply_to(message, "❌ Сессия отправки истекла")
            return
        
        # Обновляем активность
        submission.update_activity()
        
        try:
            # Сохраняем описание
            submission.description = message.text
            
            # Показываем превью
            ContestHandlers.show_submission_preview(user_id)
            
        except Exception as e:
            logger.error(f"Text handling error: {e}")
            bot.reply_to(message, "❌ Ошибка при обработке текста")
    
    @staticmethod
    def show_submission_preview(user_id: int):
        """Показ превью заявки"""
        submission = user_submissions.get(user_id)
        
        if not submission:
            return
        
        # Формируем текст превью
        preview_text = safe_markdown_v2(
            f"📋 *Превью вашей работы*\n\n"
            f"📸 *Фотографий:* {len(submission.photos)}\n"
            f"📝 *Описание:* {submission.description[:100]}{'...' if len(submission.description) > 100 else ''}\n\n"
            f"✅ *Все готово для отправки\\!*\n\n"
            f"Выберите способ отправки:"
        )
        
        # Создаем клавиатуру
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🤖 Отправить через бота",
                callback_data="send_by_bot_contest"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "❌ Отменить",
                callback_data="cancel_submission"
            )
        )
        
        bot.send_message(
            user_id,
            preview_text,
            parse_mode="MarkdownV2",
            reply_markup=markup
        )
    
    @staticmethod
    def handle_submission_send(call):
        """Обработка отправки заявки"""
        user_id = call.from_user.id
        submission = user_submissions.get(user_id)
        
        if not submission:
            bot.answer_callback_query(call.id, "❌ Сессия отправки истекла")
            return
        
        try:
            # Отправляем заявку админам
            ContestHandlers.send_submission_to_admins(user_id, submission)
            
            # Сохраняем в базу данных
            SubmissionManager.create_submission(
                user_id=user_id,
                photos=submission.photos,
                description=submission.description,
                status="pending"
            )
            
            # Очищаем временные данные
            user_submissions.remove(user_id)
            bot.delete_state(user_id)
            
            # Подтверждаем отправку
            bot.answer_callback_query(
                call.id,
                "✅ Работа успешно отправлена на конкурс!",
                show_alert=True
            )
            
            # Показываем главное меню
            from menu.menu import Menu
            main_menu = Menu.user_menu()
            bot.send_message(
                user_id,
                "🎉 *Работа отправлена\\!*\n\nСпасибо за участие в конкурсе\\!",
                parse_mode="MarkdownV2",
                reply_markup=main_menu
            )
            
        except Exception as e:
            logger.error(f"Submission send error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при отправке работы",
                show_alert=True
            )
    
    @staticmethod
    def send_submission_to_admins(user_id: int, submission):
        """Отправка заявки админам"""
        try:
            # Формируем сообщение для админов
            admin_text = safe_markdown_v2(
                f"🎨 *Новая работа на конкурс\\!*\n\n"
                f"👤 *Участник:* {user_id}\n"
                f"📸 *Фотографий:* {len(submission.photos)}\n"
                f"📝 *Описание:* {submission.description}\n\n"
                f"⏰ *Время отправки:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Отправляем текст
            bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="MarkdownV2")
            
            # Отправляем фото
            for i, photo_id in enumerate(submission.photos, 1):
                try:
                    bot.send_photo(
                        ADMIN_CHAT_ID,
                        photo_id,
                        caption=f"📸 Фото {i}/{len(submission.photos)}"
                    )
                except ApiTelegramException as e:
                    logger.error(f"Failed to send photo {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to send submission to admins: {e}")
            raise


# Регистрация обработчиков
@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_INFO,
)
@simple_lock()
@private_chat_only(bot)
def handle_user_contest_info(call):
    """Обработчик информации о конкурсе"""
    ContestHandlers.handle_contest_info(call)


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_SEND,
)
@simple_lock()
@private_chat_only(bot)
def start_contest_submission(call):
    """Обработчик начала отправки работы"""
    ContestHandlers.handle_contest_submission(call)


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == UserState.WAITING_CONTEST_PHOTOS,
)
@media_lock
def handle_contest_photos(message):
    """Обработчик фото конкурсных работ"""
    ContestHandlers.handle_contest_photos(message)


@bot.message_handler(
    content_types=["text"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == UserState.WAITING_CONTEST_TEXT,
)
@simple_lock()
def handle_contest_text(message):
    """Обработчик текста описания конкурсной работы"""
    ContestHandlers.handle_contest_text(message)


@bot.callback_query_handler(func=lambda call: call.data == "send_by_bot_contest")
@simple_lock()
def handle_contest_submission_send(call):
    """Обработчик отправки заявки на конкурс"""
    ContestHandlers.handle_submission_send(call)
