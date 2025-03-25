from datetime import datetime
import logging
import threading
from venv import logger
from telebot import types
import time
from database.contest import (
    ContestManager,
    SubmissionManager,
    is_user_approved,
    user_submissions,
)
from bot_instance import bot
from handlers.envParams import ADMIN_USERNAME, CHAT_ID, CONTEST_CHAT_ID, CHAT_USERNAME
from menu.links import Links
from menu.menu import Menu
from menu.constants import ButtonCallback, ButtonText, ConstantLinks


from threading import Lock
from weakref import WeakValueDictionary

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def is_user_in_chat(user_id):
    try:
        chat_member = bot.get_chat_member(CHAT_ID, user_id)
        return chat_member.status not in ["left", "kicked"]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка проверки участника чата: {e}")
        return False


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_GUIDES)
def handle_user_guides(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню гайдов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_FIND_GUIDE
)
def handle_user_find_guide(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "На данный момент поиск недоступен, но Вы можете посмотреть все гайды на нашем сайте",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST)
def handle_user_guides(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.contests_menu(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_INFO
)
def handle_user_contest_info(call):
    try:
        # Получаем данные о текущем конкурсе
        contest = ContestManager.get_current_contest()

        if not contest:
            # Если конкурсов нет в базе
            text = (
                "🎉 В настоящее время активных конкурсов нет.\nСледите за обновлениями!"
            )
            markup = Menu.back_to_main_menu()
        else:
            current_date = datetime.now().date()
            end_date_obj = datetime.strptime(contest[4], "%d.%m.%Y").date()

            if end_date_obj < current_date:
                text += (
                    "\n\n❗️ *Приём работ на конкурс завершён! Следите за обновлениями!*"
                )

            # Парсим данные из базы
            theme = contest[1]
            description = contest[2]
            contest_date = datetime.strptime(contest[3], "%d.%m.%Y").strftime(
                "%d %B %Y"
            )
            end_date_of_admission = datetime.strptime(contest[4], "%d.%m.%Y").strftime(
                "%d %B %Y"
            )

            # Форматируем сообщение
            text = (
                f"🏆 *Актуальный конкурс!*\n\n"
                f"📌 *Тема:* {theme}\n"
                f"📝 *Описание:* {description}\n\n"
                f"🗓 *Даты проведения:*\n"
                f"➡️ Дата проведения конкурса: {contest_date}\n"
                f"➡️ Приём работ до: {end_date_of_admission}\n\n"
                f"Можете ознакомиться с правилами участия (и списком предыдущих конкурсов) по ссылке:"
            )

            # Создаем клавиатуру
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton(
                    text="📜 Правила участия", url=ConstantLinks.CONTEST_LINK
                )
            )
            markup.row(
                types.InlineKeyboardButton(
                    ButtonText.BACK, callback_data=ButtonCallback.USER_CONTEST
                ),
                types.InlineKeyboardButton(
                    ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
                ),
            )

        # Редактируем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=markup,
        )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при выводе информации о конкурсе: {e}")
        bot.answer_callback_query(
            call.id, "⚠️ Произошла ошибка при загрузке информации", show_alert=True
        )


SUBMISSION_TIMEOUT = 300  # 5 минут на подтверждение


class ContestSubmission:
    def __init__(self):
        self.photos = []  # Список ID фотографий
        self.caption = ""  # Подпись к работе
        self.media_group_id = None  # ID медиагруппы (для альбомов)
        self.submission_time = time.time()  # Время начала отправки
        self.status = "collecting_photos"  # collecting_photos → waiting_text → preview
        self.send_by_bot = None  # True/False
        self.last_media_time = time.time()  # Время последнего фото в группе
        self.group_check_timer = None  # Таймер проверки завершения группы

    def cancel_timer(self):
        if self.group_check_timer:
            self.group_check_timer.cancel()


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_SEND
)
def start_contest_submission(call):
    try:
        user_id = call.from_user.id
        # Проверка через метод exists
        if user_submissions.exists(user_id) or is_user_approved(user_id):
            bot.answer_callback_query(
                call.id,
                "⚠️ Вы уже отправляли работу! Если хотите изменить работу, свяжитесь с админами.",
                show_alert=True,
            )
            return

        # Проверяем, состоит ли пользователь в чате
        if not is_user_in_chat(call.from_user.id):
            bot.send_message(
                call.message.chat.id,
                "❌ Для участия в конкурсе необходимо состоять в нашем чате!\n"
                + Links.get_chat_url(),
                reply_markup=Menu.contests_menu(),
            )
            return

        user_id = call.from_user.id
        user_submissions.add(user_id, ContestSubmission())

        bot.send_message(
            call.message.chat.id,
            "📸 Пришлите работу (до 10 фото без текста - его я попрошу позже):",
            reply_markup=types.ForceReply(),
        )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка начала отправки: {e}")
        handle_submission_error(call.from_user.id, e)


# Обработчик отправки работ
# Обработчик для приёма фото
@bot.message_handler(
    content_types=["photo"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == "collecting_photos",
)
def handle_work_submission(message):
    user_id = message.from_user.id
    submission = user_submissions.get(user_id)

    try:
        # Обработка медиагруппы
        if message.media_group_id:
            submission.cancel_timer()

            if submission.media_group_id != message.media_group_id:
                submission.media_group_id = message.media_group_id
                submission.photos = []

            largest_photo = max(message.photo, key=lambda p: p.file_size)
            submission.photos.append(largest_photo.file_id)
            submission.last_media_time = time.time()

            # Запускаем новый таймер
            submission.group_check_timer = threading.Timer(
                1.5, handle_group_completion, args=[user_id]  # 1.5 секунды ожидания
            )
            submission.group_check_timer.start()

            return

        # Одиночное фото
        else:
            largest_photo = max(message.photo, key=lambda p: p.file_size)
            submission.photos.append(largest_photo.file_id)

        # Проверка лимита
        if len(submission.photos) > 10:
            bot.reply_to(message, "❌ Максимум 10 фото!")
            user_submissions.remove(user_id)
            return

        # Переходим к получению текста
        submission.status = "waiting_text"
        bot.send_message(
            user_id,
            "📝 Теперь отправьте текст для работы (описание, название и т.д.):",
            reply_markup=types.ForceReply(),
        )
    except Exception as e:
        handle_submission_error(user_id, e)


def handle_group_completion(user_id):
    submission = user_submissions.get(user_id)
    if not submission or submission.status != "collecting_photos":
        return

    # Проверяем, что с момента последнего фото прошло достаточно времени
    if (time.time() - submission.last_media_time) >= 1.5:
        # Проверка лимита фото
        if len(submission.photos) == 0:
            bot.send_message(user_id, "❌ Вы не отправили ни одного фото!")
            user_submissions.remove(user_id)
            return

        if len(submission.photos) > 10:
            bot.send_message(user_id, "❌ Максимум 10 фото!")
            user_submissions.remove(user_id)
            return

        # Переход к запросу текста
        submission.status = "waiting_text"
        bot.send_message(
            user_id,
            "📝 Теперь отправьте текст для работы:",
            reply_markup=types.ForceReply(),
        )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == "waiting_text",
)
def handle_text(message):
    user_id = message.from_user.id
    submission = user_submissions.get(user_id)

    try:
        submission.caption = message.text
        submission.status = "preview"

        # Показываем предпросмотр
        media = [types.InputMediaPhoto(pid) for pid in submission.photos]
        media[0].caption = f"Предпросмотр:\n{submission.caption}"
        bot.send_media_group(user_id, media)

        # Создаем клавиатуру
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                "Да, отправить за меня", callback_data="send_by_bot_yes"
            ),
            types.InlineKeyboardButton(
                "Нет, отправлю сам(а)", callback_data="send_by_bot_no"
            ),
        )
        markup.row(
            types.InlineKeyboardButton(
                "❌ Отменить отправку работы", callback_data="cancel_submission"
            )
        )

        # Отправляем вопрос
        bot.send_message(
            message.chat.id,
            "Отправить работу во время проведения конкурса за Вас?",
            reply_markup=markup,
        )
    except Exception as e:
        handle_submission_error(user_id, e)


# Обработчик ответов
@bot.callback_query_handler(func=lambda call: call.data.startswith("send_by_bot_"))
def handle_send_method(call):
    user_id = call.from_user.id
    if not user_submissions.exists(user_id):
        bot.answer_callback_query(call.id, "❌ Сессия отправки истекла")
        return

    try:
        submission = user_submissions.get(user_id)
        # Сохраняем работу в БД со статусом "pending"
        submission_id = SubmissionManager.create_submission(
            user_id=user_id, photos=submission.photos, caption=submission.caption
        )
        # Обновляем статус в БД
        SubmissionManager.update_submission(submission_id, status="pending")

        send_by_bot = call.data == "send_by_bot_yes"

        # Логирование перед отправкой
        logger.info(f"Отправка работы для {user_id}: {len(submission.photos)} фото")

        # Проверяем доступность чата
        try:
            chat_info = bot.get_chat(CONTEST_CHAT_ID)
        except Exception as e:
            raise Exception(f"Чат {CONTEST_CHAT_ID} недоступен: {str(e)}")

        # Формируем медиагруппу
        media = [types.InputMediaPhoto(pid) for pid in submission.photos]
        media[0].caption = (
            f"{submission.caption}\n\nОтправка ботом: {'✅ Да' if send_by_bot else '❌ Нет'}"
        )

        # Отправляем в чат конкурса
        try:
            sent_messages = bot.send_media_group(chat_id=CONTEST_CHAT_ID, media=media)
            logger.info(f"Работа отправлена в чат {CONTEST_CHAT_ID}: {sent_messages}")
        except Exception as e:
            logger.error(f"Ошибка отправки в чат: {str(e)}")
            raise

        # Уведомление пользователю
        bot.send_message(
            chat_id=user_id,
            text="✅ Работа отправлена админам! После проверки я пришлю номер!",
            reply_markup=Menu.contests_menu(),
        )

        # Очистка данных
        user_submissions.remove(user_id)

    except Exception as e:
        handle_submission_error(user_id, e)
        bot.answer_callback_query(call.id, "⚠️ Ошибка при отправке работы админам!")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_submission")
def handle_cancel_submission(call):
    user_id = call.from_user.id
    try:
        if user_submissions.exists(user_id):
            user_submissions.remove(user_id)
            bot.answer_callback_query(call.id, "❌ Отправка отменена")

            # Удаляем сообщения с предпросмотром
            for _ in range(2):  # Удаляем предпросмотр и кнопки
                try:
                    bot.delete_message(
                        call.message.chat.id, call.message.message_id - _
                    )
                except:
                    pass

    except Exception as e:
        handle_submission_error(user_id, e)


# Функция обработки ошибок
def handle_submission_error(user_id, error):
    logger.error(f"[User {user_id}] Ошибка: {str(error)}", exc_info=True)
    bot.send_message(
        user_id,
        f"⚠️ Произошла ошибка! Свяжитесь с @{ADMIN_USERNAME}",
        reply_markup=Menu.contests_menu(),
    )


# Таймаут
def check_timeout():
    while True:
        try:
            current_time = time.time()
            for user_id in user_submissions.get_all_users():
                submission = user_submissions.get(user_id)
                if current_time - submission.submission_time > 600:
                    user_submissions.remove(user_id)
                    try:
                        bot.send_message(
                            user_id,
                            "⌛ Время на отправку истекло! Начните заново.",
                            reply_markup=Menu.contests_menu(),
                        )
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {str(e)}")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка таймера: {str(e)}", exc_info=True)


threading.Thread(target=check_timeout, daemon=True).start()


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_TURNIP)
def handle_user_turnip(call):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
        ),
    )
    bot.edit_message_text(
        f"На данный момент работа с репой отключена, но скоро мы её возобновим!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )
