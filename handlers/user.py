from datetime import datetime
import logging
import threading
from threading import Lock
import re
from collections import defaultdict
from venv import logger
from telebot import types
from telebot.handler_backends import State, StatesGroup
import time
from database.contest import (
    ContestManager,
    SubmissionManager,
    is_user_approved,
    user_submissions,
    user_content_storage,
)
from bot_instance import bot
from handlers.envParams import (
    ADMIN_CHAT_ID,
    NEWSPAPER_CHAT_ID,
    ADMIN_USERNAME,
    CHAT_ID,
    CONTEST_CHAT_ID,
    CHAT_USERNAME,
)
from handlers.states import UserState
from menu.links import Links
from menu.menu import Menu
from menu.constants import ButtonCallback, ButtonText, ConstantLinks


from threading import Lock
from weakref import WeakValueDictionary

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)


# Глобальный словарь для отслеживания медиагрупп
media_groups = defaultdict(list)


def is_user_in_chat(user_id):
    try:
        chat_member = bot.get_chat_member(CHAT_ID, user_id)
        return chat_member.status not in ["left", "kicked"]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка проверки участника чата: {e}")
        return False


# Система блокировки ввода
class UserLock:
    def __init__(self):
        self.locks = {}
        self.global_lock = Lock()

    def acquire(self, user_id):
        with self.global_lock:
            if user_id not in self.locks:
                self.locks[user_id] = Lock()
            return self.locks[user_id].acquire(blocking=False)

    def release(self, user_id):
        with self.global_lock:
            if user_id in self.locks:
                self.locks[user_id].release()


user_locks = UserLock()


# Декоратор для обработчиков
def lock_input(func):
    def wrapper(message):
        user_id = message.from_user.id
        if not user_locks.acquire(user_id):
            bot.reply_to(
                message, "⏳ Пожалуйста, дождитесь завершения предыдущей операции!"
            )
            return
        try:
            return func(message)
        finally:
            user_locks.release(user_id)

    return wrapper


class UserStates(StatesGroup):
    idle = State()  # Состояние по умолчанию
    waiting_photos = State()
    waiting_description = State()


# Декоратор для проверки состояния
def check_state(*states):
    def decorator(func):
        def wrapper(message):
            current_state = bot.get_state(message.from_user.id)
            if current_state not in states:
                bot.reply_to(message, "❌ Это действие сейчас недоступно")
                return
            return func(message)

        return wrapper

    return decorator


# ГАЙДЫ


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


# КОНКУРСЫ


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
@lock_input
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
@lock_input
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
@lock_input
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

    except Exception as e:
        handle_submission_error(user_id, e)
        bot.answer_callback_query(call.id, "⚠️ Ошибка при отправке работы админам!")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_submission")
@lock_input
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

# РЕПКА


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


# Общий обработчик отмены для сообщения админам и новостей
@bot.message_handler(
    commands=["cancel"],
    func=lambda message: bot.get_state(message.from_user.id)
    in [
        UserState.admin.waiting_content,
        UserState.admin.waiting_content_photo,
        UserState.news.waiting_screenshots,
        UserState.news.waiting_description,
        UserState.news.waiting_speaker,
        UserState.news.waiting_island,
        UserState.code.waiting_value,
        UserState.code.waiting_screenshots,
        UserState.code.waiting_speaker,
        UserState.code.waiting_island,
        UserState.pocket.waiting_screen_1,
        UserState.pocket.waiting_screen_2,
        UserState.design.waiting_code,
        UserState.design.waiting_design_screen,
        UserState.design.waiting_game_screens,
    ],
)
def handle_cancel(message):
    user_id = message.from_user.id
    user_content_storage.clear(user_id)
    bot.delete_state(user_id)
    bot.send_message(
        message.chat.id,
        "🚫 Отправка отменена",
        reply_markup=Menu.back_user_only_main_menu(),
    )
    if user_id in temp_storage:
        del temp_storage[user_id]
    if user_id in temp_storage_news:
        del temp_storage_news[user_id]


# Общий обработчик неверного контента для сообщения админам и новостей
@bot.message_handler(
    func=lambda m: bot.get_state(m.from_user.id)
    in [
        UserState.admin.waiting_content,
        UserState.admin.waiting_content_photo,
        UserState.news.waiting_screenshots,
        UserState.news.waiting_description,
        UserState.news.waiting_speaker,
        UserState.news.waiting_island,
        UserState.code.waiting_value,
        UserState.code.waiting_screenshots,
        UserState.code.waiting_speaker,
        UserState.code.waiting_island,
        UserState.pocket.waiting_screen_1,
        UserState.pocket.waiting_screen_2,
        UserState.design.waiting_code,
        UserState.design.waiting_design_screen,
        UserState.design.waiting_game_screens,
    ]
    and m.content_type != "photo"
)
@lock_input
def handle_invalid_content(message):
    bot.send_message(
        message.chat.id,
        "❌ Пожалуйста, отправьте фото\n ❌ Для отмены используйте /cancel",
    )


# СООБЩЕНИЕ АДМИНАМ


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_TO_ADMIN)
def handle_user_to_admin(call):
    user_id = call.from_user.id
    user_content_storage.init_content(user_id, ADMIN_CHAT_ID)

    bot.set_state(
        user_id,
        UserState.admin.waiting_content,
    )

    bot.send_message(
        call.message.chat.id,
        "📤 Пришлите текст, который хотели бы отправить админам (о фото я спрошу позже)\n"
        "❌ Для отмены используйте /cancel",
        reply_markup=types.ForceReply(),
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.admin.waiting_content
        and not message.text.startswith("/")
    ),
)
@lock_input
def handle_user_text(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "⚠️ Используйте /cancel для отмены")
        return
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id)
    content_data["text"] = message.text
    bot.set_state(user_id, UserState.admin.waiting_content_photo)
    bot.send_message(
        message.chat.id,
        "Теперь можете прислать фото.\nЕсли их нет, нажмите /skip",
        reply_markup=types.ForceReply(),
    )


@bot.message_handler(
    commands=["skip"],
    func=lambda m: bot.get_state(m.from_user.id)
    == UserState.admin.waiting_content_photo,
)
@lock_input
def skip_news_description(message):
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id)
    preview_to_admin_chat(user_id, content_data)


@bot.message_handler(
    content_types=["photo"],
    func=lambda message: bot.get_state(message.from_user.id)
    == UserState.admin.waiting_content_photo,
)
@lock_input
def handle_user_content(message):
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id)
    try:
        if message.photo:
            # Берем самое высокое разрешение (последний элемент в списке)
            photo_id = message.photo[-1].file_id

            if len(content_data["photos"]) > 10:
                bot.send_message(message.chat.id, "Максимум 10 скриншотов!")
                return

            content_data["photos"].append(photo_id)
            new_count = len(content_data["photos"])
            # Удаляем предыдущее сообщение-счетчик если есть
            if content_data.get("counter_msg_id"):
                try:
                    bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=content_data["counter_msg_id"],
                    )
                except Exception as delete_error:
                    logger.debug(f"Не удалось удалить сообщение: {delete_error}")

            # Отправляем новое сообщение с актуальным счетчиком
            msg = bot.send_message(
                message.chat.id,
                f"📸 Принято скриншотов: {new_count}/10\n"
                "Отправьте ещё фото или нажмите /done",
            )

            # Обновляем ID последнего сообщения в хранилище
            content_data["counter_msg_id"] = msg.message_id
            user_content_storage.update_data(user_id, content_data)

            if new_count == 10:
                preview_to_admin_chat(user_id, content_data)
                # Удаляем сообщение-счетчик
                bot.delete_message(message.chat.id, content_data["counter_msg_id"])

        else:
            bot.send_message(message.chat.id, "Пожалуйста, отправляйте только фото")

    except Exception as e:
        logger.error(f"Content sending error: {e}")
        bot.reply_to(message, "❌ Ошибка обработки контента")


@bot.message_handler(
    commands=["done"],
    func=lambda message: bot.get_state(message.from_user.id)
    == UserState.admin.waiting_content_photo,
)
@lock_input
def handle_done(message):
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id)
    # Удаляем последнее сообщение-счетчик
    if content_data.get("counter_msg_id"):
        try:
            bot.delete_message(message.chat.id, content_data["counter_msg_id"])
        except Exception as e:
            logger.debug(f"Ошибка удаления сообщения: {e}")

    preview_to_admin_chat(user_id, content_data)

    # Очищаем данные
    user_content_storage.clear(user_id)


# Временное хранилище для данных перед отправкой
temp_storage = {}


def preview_to_admin_chat(user_id, content_data):
    # Сохраняем данные во временное хранилище
    temp_storage[user_id] = content_data

    # Показываем предпросмотр
    media = [types.InputMediaPhoto(pid) for pid in content_data["photos"]]

    bot.send_media_group(user_id, media)

    # Создаем клавиатуру
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            "✅ Отправить", callback_data=f"confirm_send:{user_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Отменить", callback_data=f"cancel_send:{user_id}"
        ),
    )
    bot.send_message(
        user_id,
        f"Предпросмотр:\n{content_data["text"]}\n\nОтправить сообщение админам?",
        reply_markup=markup,
    )


# Обработчик кнопок подтверждения
@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("confirm_send", "cancel_send"))
)
@lock_input
def handle_confirmation(call):
    try:
        action, user_id = call.data.split(":")
        user_id = int(user_id)

        # Удаляем сообщение с кнопками
        bot.delete_message(call.message.chat.id, call.message.message_id)

        if action == "confirm_send":
            # Получаем данные из хранилища
            content_data = temp_storage.get(user_id)

            if content_data:
                # Вызываем функцию отправки
                send_to_admin_chat(user_id, content_data)
                bot.answer_callback_query(call.id, "✅ Отправлено администраторам")
            else:
                bot.answer_callback_query(call.id, "❌ Данные устарели")

        elif action == "cancel_send":
            bot.answer_callback_query(call.id, "❌ Отправка отменена")

    except Exception as e:
        logger.error(f"Confirmation error: {e}")

    finally:
        # Очищаем хранилище
        if user_id in temp_storage:
            del temp_storage[user_id]


def send_to_admin_chat(user_id, content_data):
    try:
        logger.debug("send_to_admin_chat - ", content_data)
        target_chat = content_data["target_chat"]
        text = content_data["text"]
        photos = content_data["photos"]

        user = bot.get_chat(user_id)
        user_info = f"\n\n👤 Отправитель: "
        if user.username:
            user_info += f"@{user.username}"
            if user.first_name:
                user_info += f" ({user.first_name}"
                if user.last_name:
                    user_info += f" {user.last_name}"
                user_info += ")"
        else:
            user_info += f"[id:{user_id}]"
            if user.first_name:
                user_info += f" {user.first_name}"
                if user.last_name:
                    user_info += f" {user.last_name}"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "💬 Ответить", callback_data=f"reply_to_{user_id}"
            )
        )

        if photos:
            media = [
                types.InputMediaPhoto(
                    media=photo_id, caption=content_data["text"] if i == 0 else ""
                )
                for i, photo_id in enumerate(content_data["photos"])
            ]

            # Отправляем медиагруппу БЕЗ reply_markup
            bot.send_media_group(target_chat, media)

            bot.send_message(
                target_chat,
                text=f"{user_info}\nХотите ответить?",
                reply_markup=markup,
            )

        elif text:
            full_text = f"{text}{user_info}"
            bot.send_message(target_chat, full_text, reply_markup=markup)

        bot.send_message(
            user_id,
            "✅ Контент успешно отправлен!",
            reply_markup=Menu.back_user_only_main_menu(),
        )

    except Exception as e:
        logger.error(f"Forward error: {e}")
        bot.send_message(
            user_id,
            "❌ Ошибка при отправке контента",
            reply_markup=Menu.back_user_only_main_menu(),
        )
    finally:
        # Очищаем хранилище
        if user_id in temp_storage:
            del temp_storage[user_id]


# ОТПРАВКА НОВОСТЕЙ


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_TO_NEWS)
def handle_user_to_news(call):
    # Проверяем, состоит ли пользователь в чате
    if not is_user_in_chat(call.from_user.id):
        bot.send_message(
            call.message.chat.id,
            "❌ Для отправки новостей необходимо состоять в нашем чате!\n"
            + Links.get_chat_url(),
            reply_markup=Menu.back_user_only_main_menu(),
        )
        return

    bot.edit_message_text(
        text="Что вы хотите прислать в новостную колонку?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.news_menu(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_NEWS
)
def handle_user_news_news(call):
    user_id = call.from_user.id
    user_content_storage.init_news(user_id)
    bot.set_state(user_id, UserState.news.waiting_screenshots)
    # Сначала редактируем сообщение БЕЗ ForceReply
    bot.edit_message_text(
        text="📸 Пришлите до 10 скриншотов для новости (отправьте все одним сообщением).",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )

    # Затем отправляем новое сообщение с ForceReply
    bot.send_message(
        call.message.chat.id,
        "⬇️ Отправьте скриншоты в этом чате:",
        reply_markup=types.ForceReply(selective=True),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_CODE
)
def handle_news_code(call):
    user_id = call.from_user.id
    user_content_storage.init_code(user_id)
    bot.set_state(user_id, UserState.code.waiting_value)
    bot.edit_message_text(
        text="🔢 Пришлите код\nФормат (важен!): код сна DA-0000-0000-0000, код курортного бюро RA-0000-0000-0000 (вместо 0 ваши цифры)",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.send_message(
        call.message.chat.id,
        "⬇️ Отправьте код в этом чате:",
        reply_markup=types.ForceReply(selective=True),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_POCKET
)
def handle_news_pocket(call):
    user_id = call.from_user.id
    user_content_storage.init_pocket(user_id)
    bot.set_state(user_id, UserState.pocket.waiting_screen_1)
    bot.edit_message_text(
        text="📸 Вам необходимо подготовить 2 скриншота карточки дружбы - лицевую и обратную стороны.\n"
        'Лучше всего это сделать через кнопку "SAVE"!\n'
        "❌ Для отмены используйте /cancel",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.send_message(
        call.message.chat.id,
        "⬇️ Отправьте скриншот лицевой стороны (с персонажем):",
        reply_markup=types.ForceReply(selective=True),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_DESIGN
)
def handle_news_design(call):
    user_id = call.from_user.id
    user_content_storage.init_design(user_id)
    bot.set_state(user_id, UserState.design.waiting_code)
    bot.edit_message_text(
        text="🎨 Введите код дизайна в формате:\n`MA-0000-0000-0000`",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.send_message(
        call.message.chat.id,
        "⬇️ Отправьте код в этом чате:",
        reply_markup=types.ForceReply(selective=True),
    )


def validate_code(pattern, code):
    return re.match(pattern, code.strip(), re.IGNORECASE) is not None


def parse_speaker_info(text):
    parts = [p.strip() for p in text.split(",", 1)]
    return parts[0], parts[1] if len(parts) > 1 else None


# Обработчики для USER_NEWS_NEWS
@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.news.waiting_screenshots,
)
@lock_input
def handle_news_screenshots(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    try:
        # Удаляем предыдущее сообщение с прогрессом
        if data.get("progress_message_id"):
            bot.delete_message(message.chat.id, data["progress_message_id"])
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # 1. Определяем оригинальное изображение (последний элемент всегда наибольший)
    original_photo = message.photo[-1]

    # 2. Группируем все превью этого изображения по уникальному ID оригинала
    unique_id = original_photo.file_unique_id

    # 3. Проверяем дубликаты
    existing_ids = {p["unique_id"] for p in data.get("photos", [])}
    if unique_id in existing_ids:
        bot.reply_to(message, "❌ Это изображение уже было добавлено!")
        return

    # 4. Проверяем лимит
    if len(data.get("photos", [])) > 10:
        bot.reply_to(message, "❌ Достигнут максимум 10 скриншотов!")
        request_description(user_id)

    # 5. Сохраняем только оригинал
    data.setdefault("photos", []).append(
        {"file_id": original_photo.file_id, "unique_id": unique_id}
    )

    # 6. Обновляем хранилище
    user_content_storage.update_data(user_id, data)

    if len(data["photos"]) == 10:
        request_description(user_id)
    else:
        # Добавим графический индикатор
        progress_bar = "🟪" * len(data["photos"]) + "⬜" * (10 - len(data["photos"]))

        # 7. Отправляем подтверждение
        sent_msg = bot.reply_to(
            message,
            f"{progress_bar}\n"
            f"✅ Скриншот добавлен! Всего: {len(data['photos'])}/10\n"
            "Отправьте еще или нажмите /done",
        )
        # Сохраняем ID сообщения для последующего удаления
        data["progress_message_id"] = sent_msg.message_id
        user_content_storage.update_data(user_id, data)


def request_description(user_id):
    bot.set_state(user_id, UserState.news.waiting_description)
    bot.send_message(user_id, "📝 Напишите описание новости (или /skip):")


@bot.message_handler(
    commands=["done"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.news.waiting_description,
)
@lock_input
def handle_done_news_photos(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    # Удаляем сообщение прогресса
    if data.get("progress_msg_id"):
        try:
            bot.delete_message(message.chat.id, data["progress_msg_id"])
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

    if len(data.get("photos", [])) == 0:
        bot.reply_to(message, "❌ Вы не отправили ни одного фото!")
        return

    request_description(user_id)


@bot.message_handler(
    commands=["skip"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.news.waiting_description,
)
@lock_input
def skip_news_description(message):
    user_id = message.from_user.id
    bot.set_state(user_id, UserState.news.waiting_speaker)
    bot.send_message(message.chat.id, "👤 Введите имя спикера:")


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.news.waiting_description,
)
def handle_news_description(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)
    data["description"] = message.text
    bot.set_state(user_id, UserState.news.waiting_speaker)
    bot.send_message(message.chat.id, "👤 Введите имя спикера:")


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.news.waiting_speaker,
)
@lock_input
def handle_news_speaker(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)
    data["speaker"] = message.text
    bot.set_state(user_id, UserState.news.waiting_island)
    bot.send_message(message.chat.id, "🏝️ Введите название острова:")


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.news.waiting_island,
)
@lock_input
def handle_news_island(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)
    data["island"] = message.text
    preview_send_to_news_chat(user_id)


# Обработчики для USER_NEWS_CODE
@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.code.waiting_value,
)
@lock_input
def handle_code_value(message):
    user_id = message.from_user.id
    code = message.text.upper()

    if not validate_code(r"^[DR]A-\d{4}-\d{4}-\d{4}$", code):
        bot.reply_to(message, "❌ Неверный формат кода! Пример: DA-1234-5678-9012")
        return

    user_content_storage.get_data(user_id)["code"] = code
    bot.set_state(user_id, UserState.code.waiting_screenshots)
    bot.send_message(message.chat.id, "📸 Пришлите до 10 скриншотов:")


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.code.waiting_screenshots,
)
@lock_input
def handle_code_screenshots(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    try:
        # Удаляем предыдущее сообщение с прогрессом
        if data.get("progress_message_id"):
            bot.delete_message(message.chat.id, data["progress_message_id"])
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # 1. Определяем оригинальное изображение (последний элемент всегда наибольший)
    original_photo = message.photo[-1]

    # 2. Группируем все превью этого изображения по уникальному ID оригинала
    unique_id = original_photo.file_unique_id

    # 3. Проверяем дубликаты
    existing_ids = {p["unique_id"] for p in data.get("photos", [])}
    if unique_id in existing_ids:
        bot.reply_to(message, "❌ Это изображение уже было добавлено!")
        return

    # 4. Проверяем лимит
    if len(data.get("photos", [])) > 10:
        bot.reply_to(message, "❌ Достигнут максимум 10 скриншотов!")
        request_speaker(user_id)

    # 5. Сохраняем только оригинал
    data.setdefault("photos", []).append(
        {"file_id": original_photo.file_id, "unique_id": unique_id}
    )

    # 6. Обновляем хранилище
    user_content_storage.update_data(user_id, data)

    if len(data["photos"]) == 10:
        request_speaker(user_id)
    else:
        # Добавим графический индикатор
        progress_bar = "🟪" * len(data["photos"]) + "⬜" * (10 - len(data["photos"]))

        # 7. Отправляем подтверждение
        sent_msg = bot.reply_to(
            message,
            f"{progress_bar}\n"
            f"✅ Скриншот добавлен! Всего: {len(data['photos'])}/10\n"
            "Отправьте еще или нажмите /done",
        )
        # Сохраняем ID сообщения для последующего удаления
        data["progress_message_id"] = sent_msg.message_id
        user_content_storage.update_data(user_id, data)


def request_speaker(user_id):
    bot.set_state(user_id, UserState.code.waiting_speaker)
    bot.send_message(user_id, "👤 Введите имя спикера:")


@bot.message_handler(
    commands=["done"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.code.waiting_screenshots,
)
@lock_input
def handle_done_news_photos(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    # Удаляем сообщение прогресса
    if data.get("progress_msg_id"):
        try:
            bot.delete_message(message.chat.id, data["progress_msg_id"])
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

    if len(data.get("photos", [])) == 0:
        bot.reply_to(message, "❌ Вы не отправили ни одного фото!")
        return

    request_speaker(user_id)


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.code.waiting_speaker,
)
@lock_input
def handle_code_speaker(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)
    data["speaker"] = message.text
    bot.set_state(user_id, UserState.code.waiting_island)
    bot.send_message(message.chat.id, "🏝️ Введите название острова:")


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.code.waiting_island,
)
@lock_input
def handle_code_island(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)
    data["island"] = message.text
    preview_send_to_news_chat(user_id)


# Обработчики для USER_NEWS_POCKET
@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.pocket.waiting_screen_1,
)
@lock_input
def handle_pocket_screens(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    # Сохраняем последний (наибольший) размер фото
    photo_data = {
        "file_id": message.photo[-1].file_id,
        "unique_id": message.photo[-1].file_unique_id,
    }
    data["photos"].append(photo_data)
    user_content_storage.update_data(user_id, data)

    # Меняем состояние на ожидание второго фото
    bot.set_state(user_id, UserState.pocket.waiting_screen_2)

    bot.send_message(
        message.chat.id,
        "✅ Первый скриншот принят!\n"
        "Теперь отправьте второй скриншот - обратную сторону с QR-кодом.\n"
        "❌ Для отмены используйте /cancel",
        reply_markup=types.ForceReply(),
    )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.pocket.waiting_screen_2,
)
@lock_input
def handle_pocket_screens(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    # Сохраняем последний размер фото
    new_photo_data = {
        "file_id": message.photo[-1].file_id,
        "unique_id": message.photo[-1].file_unique_id,
    }
    data["photos"].append(new_photo_data)

    # Проверяем что собрано 2 фото
    if len(data["photos"]) != 2:
        bot.send_message(message.chat.id, "❌ Ошибка обработки, начните заново")
        return

    # Завершаем процесс
    bot.delete_state(user_id)

    preview_send_to_news_chat(user_id)


# Обработчики для USER_NEWS_DESIGN
@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.design.waiting_code,
)
@lock_input
def handle_design_code(message):
    user_id = message.from_user.id
    code = message.text.upper()

    if not validate_code(r"^MA-\d{4}-\d{4}-\d{4}$", code):
        bot.reply_to(message, "❌ Неверный формат! Пример: MA-1234-5678-9012")
        return

    user_content_storage.get_data(user_id)["code"] = code
    bot.set_state(user_id, UserState.design.waiting_design_screen)
    bot.send_message(message.chat.id, "📸 Пришлите скриншот из приложения дизайнера:")


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id)
    == UserState.design.waiting_design_screen,
)
@lock_input
def handle_design_screen(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    # Проверяем, что это не альбом
    if message.media_group_id:
        bot.reply_to(message, "❌ Отправьте одно фото!")
        return

    # Сохраняем последний (наибольший) размер фото
    photo_data = {
        "file_id": message.photo[-1].file_id,
        "unique_id": message.photo[-1].file_unique_id,
    }

    data["design_screen"].append(photo_data)
    user_content_storage.update_data(user_id, data)

    bot.set_state(user_id, UserState.design.waiting_game_screens)
    bot.send_message(
        message.chat.id,
        "🎮 Пришлите до 9 (НЕ 10) скриншотов с применением рисунка в игре:",
    )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id)
    == UserState.design.waiting_game_screens,
)
@lock_input
def handle_game_screens(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    try:
        # Удаляем предыдущее сообщение с прогрессом
        if data.get("progress_message_id"):
            bot.delete_message(message.chat.id, data["progress_message_id"])
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # 1. Определяем оригинальное изображение (последний элемент всегда наибольший)
    original_photo = message.photo[-1]

    # 2. Группируем все превью этого изображения по уникальному ID оригинала
    unique_id = original_photo.file_unique_id

    # 3. Проверяем дубликаты
    existing_ids = {p["unique_id"] for p in data.get("game_screens", [])}
    if unique_id in existing_ids:
        bot.reply_to(message, "❌ Это изображение уже было добавлено!")
        return

    # 4. Проверяем лимит
    if len(data.get("game_screens", [])) >= 9:
        bot.reply_to(message, "❌ Достигнут максимум 9 скриншотов!")
        return

    # 5. Сохраняем только оригинал
    data.setdefault("game_screens", []).append(
        {"file_id": original_photo.file_id, "unique_id": unique_id}
    )

    # 6. Обновляем хранилище
    user_content_storage.update_data(user_id, data)

    # Добавим графический индикатор
    progress_bar = "🟪" * len(data["game_screens"]) + "⬜" * (
        9 - len(data["game_screens"])
    )

    # 7. Отправляем подтверждение
    sent_msg = bot.reply_to(
        message,
        f"{progress_bar}\n"
        f"✅ Скриншот добавлен! Всего: {len(data['game_screens'])}/9\n"
        "Отправьте еще или нажмите /done",
    )
    # Сохраняем ID сообщения для последующего удаления
    data["progress_message_id"] = sent_msg.message_id
    user_content_storage.update_data(user_id, data)


@bot.message_handler(
    commands=["done"],
    func=lambda message: bot.get_state(message.from_user.id)
    == UserState.design.waiting_game_screens,
)
@lock_input
def handle_done(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id)

    try:
        if data.get("progress_message_id"):
            bot.delete_message(message.chat.id, data["progress_message_id"])
    except Exception as e:
        logger.warning(f"Ошибка удаления прогресса: {e}")

    preview_send_to_news_chat(user_id)


temp_storage_news = {}


def preview_send_to_news_chat(user_id):
    try:
        # Получаем данные из хранилища
        data = user_content_storage.get_data(user_id)
        user = bot.get_chat(user_id)
        logger = logging.getLogger(__name__)

        # Формируем информацию об отправителе
        user_info = "\n👤 Отправитель: "
        if user.username:
            user_info += f"@{user.username}"
            name_parts = []
            if user.first_name:
                name_parts.append(user.first_name)
            if user.last_name:
                name_parts.append(user.last_name)
            if name_parts:
                user_info += f" ({' '.join(name_parts)})"
        else:
            name_parts = []
            if user.first_name:
                name_parts.append(user.first_name)
            if user.last_name:
                name_parts.append(user.last_name)
            user_info += (
                f"{' '.join(name_parts)} [ID: {user_id}]"
                if name_parts
                else f"[ID: {user_id}]"
            )

        # Формируем медиагруппу
        media = []
        text = ""

        # Обработка для каждого типа контента
        if data["type"] == "news":
            text = f"{ButtonText.USER_NEWS_NEWS}\n"
            if data.get("description"):
                text += f"\n📝 {data['description']}"
            text += f"\n👤 Спикер: {data.get('speaker', 'Не указан')}"
            text += f"\n🏝️ Остров: {data.get('island', 'Не указан')}"

            # Формируем медиагруппу с дедупликацией
            seen_ids = set()
            unique_photos = []
            for photo in data["photos"]:
                if photo["unique_id"] not in seen_ids:
                    seen_ids.add(photo["unique_id"])
                    unique_photos.append(photo)

            # Формируем медиагруппу
            media = [types.InputMediaPhoto(p["file_id"]) for p in unique_photos[:10]]

        elif data["type"] == "code":
            text = f"{ButtonText.USER_NEWS_CODE}\n"
            text += f"\nКод: {data.get('code', 'Не указан')}"
            text += f"\n👤 Спикер: {data.get('speaker', 'Не указан')}"
            text += f"\n🏝️ Остров: {data.get('island', 'Не указан')}"

            # Дедупликация фото
            seen_ids = set()
            unique_photos = []
            for photo in data["photos"]:
                if photo["unique_id"] not in seen_ids:
                    seen_ids.add(photo["unique_id"])
                    unique_photos.append(photo)

            # Формируем медиагруппу
            media = [types.InputMediaPhoto(p["file_id"]) for p in unique_photos[:10]]

        elif data["type"] == "pocket":
            text = f"{ButtonText.USER_NEWS_POCKET}"

            # Проверка уникальности
            seen_ids = set()
            unique_photos = []
            for photo in data["photos"]:
                if photo["unique_id"] not in seen_ids:
                    seen_ids.add(photo["unique_id"])
                    unique_photos.append(photo)

            if len(unique_photos) != 2:
                raise ValueError("Требуется ровно 2 уникальных фото")

            media = [
                types.InputMediaPhoto(unique_photos[0]["file_id"]),
                types.InputMediaPhoto(unique_photos[1]["file_id"]),
            ]

        elif data["type"] == "design":
            text = f"{ButtonText.USER_NEWS_DESIGN}\n"
            text += f"\nКод: {data.get('code', 'Не указан')}"

            # Основной скриншот
            if not data.get("design_screen"):
                raise ValueError("Отсутствует скриншот дизайна")

            media = [types.InputMediaPhoto(data["design_screen"][0]["file_id"])]

            # Игровые скриншоты
            seen_ids = set()
            for photo in data.get("game_screens", []):
                if photo["unique_id"] not in seen_ids:
                    media.append(types.InputMediaPhoto(photo["file_id"]))
                    seen_ids.add(photo["unique_id"])
                    if len(media) >= 10:  # Общий лимит медиагруппы
                        break

        # Сохраняем ВСЕ данные для отправки, включая сформированную media
        temp_storage_news[user_id] = {
            "media": media,
            "text": text,
            "user_info": user_info,
        }

        # Отправляем превью пользователю
        if media:
            bot.send_media_group(user_id, media)
        bot.send_message(user_id, text)
        confirm_markup = types.InlineKeyboardMarkup()
        confirm_markup.row(
            types.InlineKeyboardButton(
                "✅ Подтвердить отправку", callback_data=f"news_confirm_{user_id}"
            ),
            types.InlineKeyboardButton(
                "❌ Отменить", callback_data=f"news_cancel_{user_id}"
            ),
        )
        bot.send_message(
            user_id,
            "Это предпросмотр вашей публикации. Все верно?",
            reply_markup=confirm_markup,
        )

    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.send_message(
            user_id,
            f"{error_msg}\nПопробуйте начать заново.",
            reply_markup=Menu.back_user_only_main_menu(),
        )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("news_confirm_", "news_cancel_"))
)
@lock_input
def handle_preview_actions_send_to_news_chat(call):
    user_id = call.from_user.id
    action, target_user_id = call.data.split("_")[-2:]
    target_user_id = int(target_user_id)
    target_chat = NEWSPAPER_CHAT_ID

    try:
        if action == "confirm":
            # Получаем данные из хранилища
            data = temp_storage_news.get(target_user_id)

            # Отправка контента
            if not data:
                bot.answer_callback_query(call.id, "❌ Данные устарели")
                bot.send_message(
                    user_id,
                    "Вернуться в главное меню?",
                    reply_markup=Menu.back_user_only_main_menu(),
                )
                return

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "💬 Ответить", callback_data=f"reply_to_{user_id}"
                )
            )

            # Отправка в целевой чат
            # Отправка медиагруппы
            if data["media"]:
                logger.debug(f"Отправка медиагруппы из {len(data["media"])} элементов")
                bot.send_media_group(target_chat, data["media"])
                bot.send_message(
                    target_chat,
                    text=f"Текст:\n{data['text']}\n\nИнфо о пользователе:\n{data["user_info"]}\n\nХотите ответить?",
                    reply_markup=markup,
                )

            bot.answer_callback_query(
                call.id,
                "✅ Публикация отправлена!",
            )
            bot.send_message(
                user_id,
                "Вернуться в главное меню?",
                reply_markup=Menu.back_user_only_main_menu(),
            )
        else:
            bot.answer_callback_query(
                call.id,
                "🚫 Отправка отменена",
            )
            bot.send_message(
                user_id,
                "Вернуться в главное меню?",
                reply_markup=Menu.back_user_only_main_menu(),
            )

        # Удаляем сообщение с кнопками
        bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        logger.error(f"handle_preview_actions_send_to_news_chat error:\n{e}")
        bot.send_message(
            user_id,
            "❌ Произошла ошибка\nПопробуйте начать заново.",
            reply_markup=Menu.news_menu(),
        )
    finally:
        # Гарантированная очистка данных
        # Очищаем хранилище
        if user_id in temp_storage_news:
            del temp_storage_news[user_id]
        user_content_storage.clear(user_id)
        bot.delete_state(user_id)
        logger.debug("Данные пользователя очищены")
