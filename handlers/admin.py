import logging
import re
from venv import logger
from datetime import datetime
import telebot.types as types
from telebot.apihelper import ApiTelegramException
from utils.markdown_utils import escape_markdown_v2, safe_markdown_v2

from database.db_classes import (
    ContestManager,
    SubmissionManager,
    get_submission,
    user_submissions,
)
from handlers.decorator import private_chat_only
from handlers.envParams import admin_ids, news_ids
from bot_instance import bot
from menu.constants import ButtonCallback, ButtonText
from menu.menu import Menu

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)

# storage.py
from threading import Lock

bot_username = bot.get_me().username


class TempStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()

    def get_user_step(self, user_id):
        with self.lock:
            return self.data.get(user_id, {}).get("step")

    def set_user_step(self, user_id, step):
        with self.lock:
            if user_id not in self.data:
                self.data[user_id] = {}
            self.data[user_id]["step"] = step

    def update_data(self, user_id, **kwargs):
        with self.lock:
            if user_id not in self.data:
                self.data[user_id] = {}
            self.data[user_id].update(kwargs)

    def clear(self, user_id):
        with self.lock:
            if user_id in self.data:
                del self.data[user_id]


storage = TempStorage()

ADMIN_STEPS = {
    "theme": "Введите тему конкурса:",
    "description": "Введите описание:",
    "contest_date": "Введите дату проведения конкурса, через точку ДД ММ ГГГГ:",
    "end_date_of_admission": "Введите дату окончания приёма работ, через точку ДД ММ ГГГГ:",
}


def check_admin(call):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(
            call.id,
            "⚠️ Вы не являетесь админом\n\nВы вообще как сюда попали???",
            show_alert=True,
        )
        return False
    return True

def check_admin_or_news(call):
    if call.from_user.id not in admin_ids and call.from_user.id not in news_ids:
        bot.answer_callback_query(
            call.id,
            "⚠️ Вы не являетесь админом\n\nВы вообще как сюда попали???",
            show_alert=True,
        )
        return False
    return True


# Меню конкурсов для админа
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST)
@private_chat_only(bot)
def handle_adm_contest(call):
    if not check_admin(call):
        return
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов администратора\nВыберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.adm_contests_menu(),
    )


# Обработчик кнопки "Обновить информацию" в админ-меню
@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.ADM_CONTEST_INFO
)
def start_contest_update(call):
    if not check_admin(call):
        return
    try:
        storage.clear
        # Получаем текущий конкурс
        contest = ContestManager.get_current_contest()

        # Формируем сообщение с текущими данными
        text = "📋 *Текущие данные конкурса:*\n\n"
        markup = types.InlineKeyboardMarkup()

        if contest:
            # Экранируем все динамические данные
            theme = escape_markdown_v2(contest[1])
            description = escape_markdown_v2(contest[2])

            # Экранируем даты с точками
            contest_date = escape_markdown_v2(contest[3])
            end_date_of_admission = escape_markdown_v2(contest[4])

            text += (
                f"🏷 Тема: {theme}\n"
                f"📝 Описание: {description}\n\n"
                f"⏳ Приём работ до: {end_date_of_admission}\n"
                f"🗓 Дата проведения: {contest_date}\n\n"
                "Хотите изменить данные?"
            )

            markup.row(
                types.InlineKeyboardButton(
                    "✅ Да, обновить", callback_data="confirm_update"
                ),
                types.InlineKeyboardButton(
                    "🗑 Очистить данные", callback_data="reset_info"
                ),
            )
            markup.row(
                types.InlineKeyboardButton(
                    text=ButtonText.BACK, callback_data=ButtonCallback.ADM_CONTEST
                ),
                types.InlineKeyboardButton(
                    text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
                ),
            )
        else:
            text += safe_markdown_v2("⚠️ Активных конкурсов не найдено\nХотите создать новый?")
            markup.row(
                types.InlineKeyboardButton(
                    "➕ Создать новый", callback_data="confirm_update"
                ),
                types.InlineKeyboardButton("🔙 Назад", callback_data="cancel_update"),
            )

        # Отправляем сообщение с подтверждением
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=markup,
        )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при получении данных: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка загрузки данных", show_alert=True)


# Обработчик отмены
@bot.callback_query_handler(func=lambda call: call.data == "cancel_update")
def handle_cancel_update(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        "Действие отменено",
        reply_markup=Menu.back_adm_contest_menu(),
    )


# Обработчик сброса данных
@bot.callback_query_handler(func=lambda call: call.data == "reset_info")
def handle_reset_info(call):
    markup = types.InlineKeyboardMarkup()
    text = safe_markdown_v2("Точно очистить данные с информацией о текущем конкурсе?")
    markup.row(
        types.InlineKeyboardButton(
            "✅ Да, очистить", callback_data="confirm_reset_info"
        ),
        types.InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_update"),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode="MarkdownV2",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_reset_info")
def handle_reset_info(call):
    storage.clear
    bot.edit_message_text(
        "Данные очищены",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.back_adm_contest_menu(),
    )


# Обработчик подтверждения обновления
@bot.callback_query_handler(func=lambda call: call.data == "confirm_update")
def start_contest_update(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    storage.set_user_step(call.from_user.id, "theme")
    bot.send_message(call.message.chat.id, ADMIN_STEPS["theme"])


@bot.message_handler(
    func=lambda m: storage.get_user_step(m.from_user.id) in ADMIN_STEPS
)
def handle_admin_input(message):
    user_id = message.from_user.id
    current_step = storage.get_user_step(user_id)

    # Обработка отмены
    if message.text.lower() == "/cancel":
        storage.clear(user_id)
        bot.send_message(message.chat.id, "❌ Операция отменена")
        return

    # Валидация даты
    if current_step in ["contest_date", "end_date_of_admission"]:
        try:
            datetime.strptime(message.text, "%d.%m.%Y")
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Неверный формат! Используйте через точку ДД ММ ГГГГ",
            )
            return

    # Сохраняем данные
    storage.update_data(user_id, **{current_step: message.text})

    # Переход к следующему шагу
    steps = list(ADMIN_STEPS.keys())
    next_step_index = steps.index(current_step) + 1

    if next_step_index < len(steps):
        next_step = steps[next_step_index]
        storage.set_user_step(user_id, next_step)
        bot.send_message(message.chat.id, ADMIN_STEPS[next_step])
    else:
        # Все данные собраны
        data = storage.data[user_id]
        ContestManager.update_contest(
            data["theme"],
            data["description"],
            data["contest_date"],
            data["end_date_of_admission"],
        )
        storage.clear(user_id)
        bot.send_message(
            message.chat.id,
            "✅ Данные обновлены!",
            reply_markup=Menu.back_adm_contest_menu(),
        )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.ADM_CONTEST_STATS
)
def show_stats(call):
    if not check_admin(call):
        return
    try:
        pending = SubmissionManager.get_pending_count()
        approved = SubmissionManager.get_approved_count()
        rejected = SubmissionManager.get_rejected_count()
        judges = SubmissionManager.get_judges_count()

        bot.edit_message_text(
            text=(
                f"📊 *Статистика конкурса:*\n\n"
                f"⏳ Ожидают проверки: `{pending}`\n"
                f"✅ Одобрено работ: `{approved}`\n"
                f"❌ Отклонено работ: `{rejected}`\n"
                f"⚖️ Подали заявку на судейство: `{judges}`"
            ),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="MarkdownV2",
            reply_markup=Menu.adm_stat_menu(),
        )

    except Exception as e:
        handle_admin_error(call.message.chat.id, e)


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.ADM_SHOW_PARTICIPANTS
)
def handle_show_participants(call):
    participants = SubmissionManager.get_all_submissions_with_info()
    if not participants:
        bot.edit_message_text(
            text=safe_markdown_v2("❌ Нет данных об участниках"),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="MarkdownV2",
            reply_markup=Menu.adm_stat_menu(),
        )
        return

    text = "📋 Список участников:\n\n"
    for p in participants:
        text += (
            f"👤 {p[0]}\n"
            f"🗨️ @{p[1]}\n"
            f"🔄 Статус: {p[2]}\n"
            f"🔢 Номер: {p[3] or 'не присвоен'}\n"
            f"────────────────\n"
        )

    bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.adm_stat_menu(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.ADM_SHOW_JUDGES
)
def handle_show_judges(call):
    judges = SubmissionManager.get_all_judges_with_info()
    if not judges:
        bot.edit_message_text(
            text=safe_markdown_v2("❌ Нет данных о судьях"),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="MarkdownV2",
            reply_markup=Menu.adm_stat_menu(),
        )
        return

    text = "📋 Список судей:\n\n"
    for j in judges:
        text += f"👤 {j[0]}\n🗨️ @{j[1]}\n────────────────\n"

    bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.adm_stat_menu(),
    )


def process_rejection(message, submission_id):
    try:
        SubmissionManager.update_submission(submission_id, "rejected", message.text)

        submission = get_submission(submission_id)
        user_id = submission["user_id"]
        user_notified = False  # Флаг успешности уведомления

        try:
            bot.send_message(
                user_id,
                f"❌ Работа отклонена\nПричина: {message.text}",
                reply_markup=Menu.back_user_contest_menu(),
            )
            user_notified = True
        except Exception as user_error:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {user_error}")

        # Формируем текст для админа
        status_text = (
            "✅ Пользователь уведомлён"
            if user_notified
            else "⚠️ Не удалось уведомить пользователя"
        )

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=(f"Работа #{submission_id} отклонена\n{status_text}"),
            reply_markup=Menu.adm_menu(),
        )

        logger.info(
            f"REJECTION: submission={submission_id} "
            f"admin={message.from_user.id} "
            f"user_notified={user_notified} "
            f"reason={message.text}"
        )

    except Exception as e:
        handle_admin_error(message.chat.id, e)


def handle_admin_error(chat_id, error):
    """Обработка ошибок в админских функциях"""
    error_msg = safe_markdown_v2(
        f"⚠️ *Ошибка администратора*\n"
        f"```{str(error)}```\n"
        f"Пожалуйста, проверьте логи для деталей"
    )

    try:
        bot.send_message(chat_id, error_msg, parse_mode="MarkdownV2")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

    # Логирование в консоль
    logger = logging.getLogger(__name__)
    logger.error(f"\n❌ ADMIN ERROR [{datetime.now()}]: {error}")


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.ADM_CONTEST_RESET
)
def handle_adm_contest_reset(call):
    if not check_admin(call):
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить сброс", callback_data="confirm_reset"
        ),
        types.InlineKeyboardButton("🚫 Отменить", callback_data="cancel_reset"),
    )

    current_count = SubmissionManager.get_current_number()
    bot.edit_message_text(
        text=(  # Явное указание текста
            f"⚠️ Текущее количество участников: {current_count}\n"
            f"количество подавших заявку на судейство: {SubmissionManager.get_judges_count()}\n\n"
            "Вы уверены, что хотите сбросить счетчик?"
        ),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_reset")
def confirm_reset(call):
    if not check_admin(call):
        return
    # Очищаем БД через менеджер
    SubmissionManager.reset_counter()

    logger = logging.getLogger(__name__)
    logger.debug("Обнуление данных - сброс счётчика")
    logger.debug(
        f"количество работ на модерации: {SubmissionManager.get_pending_count()}/0"
    )
    logger.debug(
        f"количество одобренных работ: {SubmissionManager.get_approved_count()}/0"
    )
    logger.debug(
        f"количество отвергнутых работ: {SubmissionManager.get_rejected_count()}/0"
    )
    logger.debug(
        f"текущее количество участников всего: {SubmissionManager.get_current_number()}/0"
    )
    logger.debug(
        f"количество подавших заявку на судейство: {SubmissionManager.get_judges_count()}/0"
    )

    # Очищаем временное хранилище
    user_submissions.clear()

    logger.debug(
        f"Временных данных в хранилище: {len(user_submissions.get_all_users())}/0"
    )

    bot.edit_message_text(
        text="✅ Счетчик участников сброшен",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.adm_contests_menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "cancel_reset")
def handle_cancel_reset(call):
    if not check_admin(call):
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.edit_message_text(
        text="🚫 Сброс счетчика отменен",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.back_adm_contest_menu,
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.ADM_REVIEW_WORKS
)
def show_pending_submissions(call):
    if not check_admin(call):
        return
    try:
        submissions = SubmissionManager.get_pending_submissions()

        if not submissions:
            bot.answer_callback_query(call.id, "Нет работ на проверке")
            return

        markup = types.InlineKeyboardMarkup()
        for sub in submissions:
            btn_text = f"Работа #{sub[0]} от пользователя {sub[1]}"
            markup.add(
                types.InlineKeyboardButton(
                    btn_text, callback_data=f"submission_{sub[0]}"
                )
            )
        markup.add(
            types.InlineKeyboardButton(
                text=ButtonText.BACK, callback_data=ButtonCallback.ADM_CONTEST
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        bot.edit_message_text(
            "Выберите работу для модерации:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
        )

    except Exception as e:
        handle_admin_error(call.message.chat.id, e)


@bot.callback_query_handler(func=lambda call: call.data.startswith("submission_"))
def show_submission_details(call):
    if not check_admin(call):
        return
    try:
        submission_id = int(call.data.split("_")[1])
        submission = get_submission(submission_id)

        if not submission:
            bot.answer_callback_query(call.id, "❌ Работа не найдена")
            return

        media_group = []
        # Проходим по списку словарей и извлекаем file_id
        for i, photo_dict in enumerate(submission["photos"]):
            file_id = photo_dict.get("file_id")
            if not file_id:
                continue  # Пропускаем некорректные записи
            media = types.InputMediaPhoto(
                media=file_id,  # Передаём строку, а не словарь
                caption=(
                    f"Работа #{submission_id}\n\n{submission['caption']}"
                    if i == 0
                    else None
                ),
            )
            media_group.append(media)

        if media_group:
            bot.send_media_group(call.message.chat.id, media_group)
        else:
            bot.answer_callback_query(call.id, "❌ Нет доступных фотографий")

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                ButtonText.ADM_APPROVE,
                callback_data=f"{ButtonCallback.ADM_APPROVE}{submission_id}",
            ),
            types.InlineKeyboardButton(
                ButtonText.ADM_REJECT,
                callback_data=f"{ButtonCallback.ADM_REJECT}{submission_id}",
            ),
        )

        bot.send_message(
            call.message.chat.id,
            f"Действия для работы #{submission_id}:",
            reply_markup=markup,
        )

    except Exception as e:
        handle_admin_error(call.message.chat.id, e)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(ButtonCallback.ADM_APPROVE)
)
def approve_work(call):
    if not check_admin(call):
        return
    try:
        submission_id = int(call.data.replace(ButtonCallback.ADM_APPROVE, ""))
        number = SubmissionManager.approve_submission(submission_id)

        submission = get_submission(submission_id)  # Получаем данные работы
        user_id = submission["user_id"]  # Извлекаем ID пользователя

        # Удаляем пользователя из временного хранилища
        user_submissions.remove(user_id)

        user_notified = False  # Флаг успешности уведомления
        # Пытаемся уведомить пользователя
        try:
            bot.send_message(
                user_id,
                f"✅ Ваша работа одобрена!\nНомер работы: #{number}",
                reply_markup=Menu.back_user_contest_menu(),
            )
            user_notified = True
        except Exception as user_error:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {user_error}")
        # Формируем текст для админа
        status_text = (
            "✅ Пользователь уведомлён"
            if user_notified
            else "⚠️ Не удалось уведомить пользователя"
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Работа #{submission_id} одобрена как №{number}\n{status_text}",
            reply_markup=Menu.adm_menu(),
        )

    except Exception as e:
        handle_admin_error(call.message.chat.id, e)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(ButtonCallback.ADM_REJECT)
)
def reject_work(call):
    if not check_admin(call):
        return
    try:
        submission_id = int(call.data.replace(ButtonCallback.ADM_REJECT, ""))
        msg = bot.send_message(
            call.message.chat.id,
            "Введите причину отклонения в ответ на это сообщение, то есть реплаем:",
        )
        bot.register_for_reply(msg, lambda m: process_rejection(m, submission_id))

    except Exception as e:
        handle_admin_error(call.message.chat.id, e)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_TURNIP)
@private_chat_only(bot)
def handle_adm_turnip(call):
    if not check_admin(call):
        return
    bot.edit_message_text(
        f"На данный момент работа с репой отключена",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.adm_menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_ADD_GUIDE)
@private_chat_only(bot)
def handle_adm_add_guide(call):
    if not check_admin(call):
        return
    bot.edit_message_text(
        f"На данный момент работа с гайдами через бота отключена",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.adm_menu(),
    )


# Глобальное хранилище для ответов
admin_replies = {}


@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to_"))
def handle_reply_button(call):
    if not check_admin_or_news(call):
        return
    try:
        user_id = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)

        # Сохраняем связь админ -> пользователь !с привязкой к chat.id админа
        admin_replies[call.message.chat.id] = user_id  # <-- Ключом выступает chat.id!

        msg = bot.send_message(
            call.message.chat.id,  # Отвечаем в тот же чат
            f"✍️ Введите ответ для пользователя в ответ на это сообщение, то есть реплаем:\n🚫 Для отмены используйте /cancel_adm",
            reply_markup=types.ForceReply(selective=True),
        )

        # Регистрируем следующий шаг с явным указанием чата
        bot.register_next_step_handler(
            msg, lambda m: process_admin_reply(m) if m.content_type == "text" else None
        )

    except Exception as e:
        logger.error(f"Reply error: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка", show_alert=True)


@bot.message_handler(
    commands=["cancel_adm"],
    regexp=re.compile(rf"^/cancel_adm(?:@{re.escape(bot_username)})?$", re.IGNORECASE).pattern,
)
def cancel_reply(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Проверка прав администратора
        if user_id not in admin_ids and user_id not in news_ids:
            bot.reply_to(message, "❌ У вас нет прав для этой команды")
            return

        # Удаление состояния ответа
        if chat_id in admin_replies:
            del admin_replies[chat_id]

        # Удаляем сообщение с командой /cancel_adm
        bot.delete_message(chat_id, message.message_id)

        # Отправляем подтверждение
        bot.send_message(chat_id, "✅ Ответ отменён", reply_markup=Menu.adm_menu())

    except Exception as e:
        logger.error(f"Ошибка в cancel_reply: {e}")
        bot.send_message(chat_id, "⚠️ Ошибка при отмене ответа")


def process_admin_reply(message):
    try:
        chat_id = message.chat.id

        # Если это команда /cancel_adm - игнорируем, она обрабатывается отдельно
        if message.text and message.text.startswith("/cancel_adm"):
            cancel_reply(message)
            return

        # Проверяем наличие активной сессии
        if chat_id not in admin_replies:
            bot.send_message(chat_id, "❌ Сессия ответа устарела")
            return

        # Получаем user_id из хранилища по chat_id
        user_id = admin_replies.get(chat_id)

        if not user_id:
            bot.send_message(chat_id, "❌ Сессия ответа устарела")
            return

        user_notified = False  # Флаг успешности уведомления

        # Пытаемся уведомить пользователя
        try:
            bot.send_message(
                user_id,
                f"📨 Сообщение от администратора:\n{message.text}",
                reply_markup=Menu.user_to_admin_or_main_menu(),
            )
            user_notified = True
        except Exception as user_error:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {user_error}")
        # Формируем текст для админа
        status_text = (
            "✅ Ответ отправлен пользователю"
            if user_notified
            else "⚠️ Не удалось отправить ответ пользователю"
        )

        # Удаляем служебные сообщения
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.delete_message(chat_id, message.reply_to_message.message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщения: {e}")

        bot.send_message(
            chat_id=chat_id,
            text=status_text,
            reply_markup=Menu.adm_menu(),
        )

        # Очищаем хранилище после отправки
        if chat_id in admin_replies:
            del admin_replies[chat_id]

    except ApiTelegramException as e:
        logger.error(f"Process reply error: {e}")
        if e.description == "Forbidden: bot was blocked by the user":
            bot.send_message(chat_id, "❌ Пользователь заблокировал бота")
        else:
            raise


@bot.callback_query_handler(func=lambda call: call.data.startswith("block_user_"))
def handle_block_user(call):
    user_id = int(call.data.split("_")[2])
    user = bot.get_chat(user_id)

    try:
        SubmissionManager.insert_replace_blocked(
            user_id, user.username, user.first_name, user.last_name
        )

        bot.answer_callback_query(call.id, "✅ Пользователь заблокирован")

    except Exception as e:
        logger.error(f"Ошибка блокировки пользователя: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка блокировки")


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_BLOCK)
def handle_show_blocked_users(call):
    try:
        users = SubmissionManager.select_blocked()

        markup = types.InlineKeyboardMarkup()

        text = "🚫 Заблокированные пользователи:\n\n"
        for user in users:
            text += f"👤 {user[2]}\n"
            text += f"🔗 @{user[1] if user[1] else 'нет'}\n"
            text += f"🆔 ID: `{user[0]}`\n"
            text += f"⏱ {user[3]}\n"
            markup.add(
                types.InlineKeyboardButton(
                    f"Разблокировать {user[2]}", callback_data=f"unblock_{user[0]}"
                )
            )

        markup.row(
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            )
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
        )

    except Exception as e:
        logger.error(f"Ошибка получения списка блокировок: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки списка")


@bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_"))
def handle_unblock_user(call):
    user_id = int(call.data.split("_")[1])

    try:
        SubmissionManager.delete_blocked(user_id)

        bot.answer_callback_query(call.id, "✅ Пользователь разблокирован")
        handle_show_blocked_users(call)  # Обновляем список

    except Exception as e:
        logger.error(f"Ошибка разблокировки: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка разблокировки")
