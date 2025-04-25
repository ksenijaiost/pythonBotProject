from datetime import datetime
import logging
import threading
import re
from telebot.apihelper import ApiTelegramException
from collections import defaultdict
from venv import logger
from telebot import types
import time
from database.contest import (
    ContestManager,
    ContestSubmission,
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
from handlers.decorator import private_chat_only
from menu.links import Links
from menu.menu import Menu
from menu.constants import (
    MONTHS_RU,
    ButtonCallback,
    ButtonText,
    ConstantLinks,
    UserState,
)


from threading import Lock
from weakref import WeakValueDictionary

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)


# Глобальный словарь для отслеживания медиагрупп
media_groups = defaultdict(list)
# Временное хранилище для данных
temp_storage = {}


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
        self.locks = defaultdict(Lock)  # Базовые блокировки по user_id
        self.media_group_locks = defaultdict(
            Lock
        )  # Отдельные блокировки для медиагрупп
        self.current_media_groups = {}  # Текущие обрабатываемые медиагруппы
        self.global_lock = Lock()
        self.last_activity = {}  # Добавляем недостающий атрибут

    def acquire(self, user_id: int) -> bool:
        """Пытается захватить блокировку для пользователя"""
        with self.global_lock:
            acquired = self.locks[user_id].acquire(blocking=False)
            if acquired:
                self.last_activity[user_id] = time.time()  # Обновляем время активности
            return acquired

    def release(self, user_id: int) -> None:
        """Освобождает блокировку пользователя"""
        with self.global_lock:
            if user_id in self.locks:
                try:
                    self.locks[user_id].release()
                    self.last_activity[user_id] = time.time()  # Обновляем время
                except RuntimeError:
                    pass  # Игнорируем ошибку повторного освобождения

    def acquire_for_media_group(self, user_id: int, media_group_id: str) -> bool:
        """Захват блокировки для медиагруппы"""
        if media_group_id in self.current_media_groups.get(user_id, set()):
            return True  # Уже обрабатывается
        with self.locks[user_id]:
            self.current_media_groups.setdefault(user_id, set()).add(media_group_id)
            return self.media_group_locks[media_group_id].acquire(blocking=False)

    def release_media_group(self, user_id: int, media_group_id: str):
        """Освобождение блокировки медиагруппы"""
        with self.locks[user_id]:
            if media_group_id in self.current_media_groups.get(user_id, set()):
                self.media_group_locks[media_group_id].release()
                self.current_media_groups[user_id].remove(media_group_id)

    def cleanup(self, max_age=300):
        """Удаляет неактивные блокировки старше max_age секунд"""
        with self.global_lock:
            now = time.time()
            # Создаем копию ключей для безопасной итерации
            for user_id in list(self.last_activity.keys()):
                if now - self.last_activity.get(user_id, 0) > max_age:
                    del self.locks[user_id]
                    del self.last_activity[user_id]


# Инициализируем глобальный экземпляр
user_locks = UserLock()


def lock_input(allow_media_groups: bool = False):
    """Декоратор с поддержкой медиагрупп"""

    def decorator(func):
        def wrapper(message_or_call):
            user_id = message_or_call.from_user.id
            media_group_id = getattr(message_or_call, "media_group_id", None)

            # Для медиагрупп используем специальные блокировки
            if allow_media_groups and media_group_id:
                if not user_locks.acquire_for_media_group(user_id, media_group_id):
                    return
            else:
                if not user_locks.acquire(user_id):
                    error_msg = (
                        "⏳ Пожалуйста, дождитесь завершения предыдущей операции\!"
                    )
                    if hasattr(message_or_call, "message"):
                        bot.answer_callback_query(message_or_call.id, error_msg)
                    else:
                        bot.reply_to(message_or_call, error_msg)
                    return

            try:
                return func(message_or_call)
            finally:
                if allow_media_groups and media_group_id:
                    user_locks.release_media_group(user_id, media_group_id)
                else:
                    user_locks.release(user_id)

        return wrapper

    return decorator


# Функция для фоновой очистки
def run_cleanup():
    while True:
        try:
            user_locks.cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        time.sleep(60)  # Проверка каждую минуту


# Запуск в отдельном потоке
threading.Thread(target=run_cleanup, daemon=True).start()


# Сбор "Юзер инфо"
def get_user_info(user):
    user_info = f"\n\n👤 Отправитель: "
    if user.username:
        user_info += f"@{user.username}"
        if user.first_name:
            user_info += f" ({user.first_name}"
            if user.last_name:
                user_info += f" {user.last_name}"
            user_info += ")"
    else:
        user_info += f"[id:{user.id}]"
        if user.first_name:
            user_info += f" {user.first_name}"
            if user.last_name:
                user_info += f" {user.last_name}"
    return user_info


# ПОМОЩЬ
@bot.message_handler(commands=["help"])
def handle_help(message):
    user_id = message.from_user.id
    current_state = bot.get_state(user_id)

    # Отправляем помощь, НЕ сбрасывая состояние
    help_text = (
        "❓ *Помощь по боту*\n\n\n"
        f"*{ButtonText.USER_GUIDES}*: гайды по Animal Crossing и не только;\n\n"
        f"*{ButtonText.USER_CONTEST}*: всё о конкурсах:\n"
        f"*{ButtonText.USER_CONTEST_INFO}*: информация об актуальном конкурсе, правила и прошлые конкурсы,\n"
        f"*{ButtonText.USER_CONTEST_SEND}*: отправка работы для участия в конкурсе,\n"
        f"*{ButtonText.USER_CONTEST_JUDGE}*: _перешлю Ваше желания админам_;\n\n"
        f"*{ButtonText.USER_TO_ADMIN}*: отправка сообщения админам чата;\n"
        f"*{ButtonText.USER_TO_NEWS}*: отправка новостей и кодов сна, дач, дизайна и PocketCamp;\n"
        f"*{ButtonText.USER_TURNIP}*: находится в разработке, _позже тут будет возможность продать репу админам по субботам_;\n"
        f"*{ButtonText.USER_HEAD_CHAT}*: ссылка на чатик по Animal Crossing;\n"
        f"*{ButtonText.USER_CHANEL}*: ссылка на канал с ежедневными новостями, анонсами, идеями и другими полезностями;\n"
        f"*{ButtonText.USER_CHAT_NINTENDO}*: ссылка на чат, разделённый на темы по играм Nintendo, а также отдельной оффтоп темой"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
            types.InlineKeyboardButton(
                text=ButtonText.USER_HELP_SITE, url=ConstantLinks.HELP_LINK
            )
        )
    # Добавляем кнопку "В главное меню" только если нет активного состояния
    if current_state:
        help_text += "\n\n Можете продолжить выполнение предыдущих действий\n\n"
        help_text += "🚫 Для отмены действия и возврата в главное меню нажмите /cancel\n"
        help_text += "🔄 Для рестарта бота можете нажать команду /start, _сбросится то, что Вы делали, а бот перезапустится_"
    else:
        markup.add(
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            )
        )

    help_text += "\n\n📚 Полная инструкция на нашем сайте доступна по кнопке ниже"

    bot.send_message(
        user_id,
        help_text,
        parse_mode="MarkdownV2",
        reply_markup=markup,
        disable_web_page_preview=True,
    )


# ГАЙДЫ


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_GUIDES)
@private_chat_only(bot)
def handle_user_guides(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню гайдов\nВыберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_FIND_GUIDE,
)
@private_chat_only(bot)
def handle_user_find_guide(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.send_message(
        text="😭 На данный момент поиск недоступен,\nно Вы можете посмотреть все гайды на нашем сайте 🤗",
        chat_id=call.message.chat.id,
        reply_markup=Menu.guides_menu(),
    )


# КОНКУРСЫ


# Общий обработчик отмены
@bot.message_handler(
    commands=["cancel"],
    func=lambda message: bot.get_state(message.from_user.id)
    in [
        UserState.WAITING_CONTEST_PHOTOS,
        UserState.WAITING_CONTEST_TEXT,
        UserState.WAITING_CONTEST_PREVIEW,
    ],
)
def handle_cancel(message):
    user_id = message.from_user.id
    if user_submissions.exists(user_id):
        user_submissions.remove(user_id)
    bot.delete_state(user_id)
    bot.send_message(
        message.chat.id,
        "🚫 Отправка отменена",
        reply_markup=Menu.back_user_only_main_menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST)
@private_chat_only(bot)
def handle_user_guides(call):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов\nВыберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.contests_menu(),
    )


def format_date_ru(date_str: str) -> str:
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        return f"{date_obj.day} {MONTHS_RU[date_obj.month]} {date_obj.year}"
    except:
        return date_str


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_INFO,
)
@lock_input()
@private_chat_only(bot)
def handle_user_contest_info(call):
    try:
        # Получаем данные о текущем конкурсе
        contest = ContestManager.get_current_contest()

        text = ""

        if not contest:
            # Если конкурсов нет в базе
            text = (
                "🎉 В настоящее время активных конкурсов нет\nСледите за обновлениями\!"
            )
            markup = Menu.back_user_contest_menu()
        else:
            current_date = datetime.now().date()
            end_date_obj = datetime.strptime(contest[4], "%d.%m.%Y").date()

            # Основной текст сообщения
            theme = contest[1]
            description = contest[2]
            contest_date = format_date_ru(contest[3])
            end_date_of_admission = format_date_ru(contest[4])

            text = (
                f"🏆 *Актуальный конкурс*\n\n"
                f"📌 *Тема:* {theme}\n"
                f"📝 *Описание:* {description}\n\n"
                f"🗓 *Даты:*\n"
                f"⏳ Приём работ до *{end_date_of_admission}*\n"
                f"🎉 Дата проведения: *{contest_date}*\n\n"
            )

            # Добавляем предупреждение если срок подачи истёк
            if end_date_obj < current_date:
                text += "❗️*Приём работ на конкурс завершён\!* _Следите за обновлениями_\!\n\n"

            text += "Можете ознакомиться с правилами участия _\(и списком предыдущих конкурсов\)_ по ссылке:"

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
            parse_mode="MarkdownV2",
        )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при выводе информации о конкурсе: {e}")
        bot.answer_callback_query(
            call.id, "⚠️ Произошла ошибка при загрузке информации", show_alert=True
        )


SUBMISSION_TIMEOUT = 300  # 5 минут на подтверждение


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_SEND,
)
@lock_input()
@private_chat_only(bot)
def start_contest_submission(call):
    try:
        user_id = call.from_user.id
        if user_id in temp_storage:
            del temp_storage[user_id]

        # Получаем данные о текущем конкурсе
        contest = ContestManager.get_current_contest()
        if not contest:
            # Если конкурсов нет в базе
            bot.answer_callback_query(
                call.id,
                "🎉 В настоящее время активных конкурсов нет\n\nСледите за обновлениями\!",
                show_alert=True,
            )
            return
        else:
            current_date = datetime.now().date()
            end_date_obj = datetime.strptime(contest[4], "%d.%m.%Y").date()
            if end_date_obj < current_date:
                bot.answer_callback_query(
                    call.id,
                    "❗️Приём работ на конкурс завершён\! Следите за обновлениями\!",
                    show_alert=True,
                )
                return

            # Проверка через метод exists
            if user_submissions.exists(user_id) or is_user_approved(user_id):
                bot.answer_callback_query(
                    call.id,
                    "⚠️ Вы уже отправляли работу\n\nЕсли хотите изменить работу, свяжитесь с админами",
                    show_alert=True,
                )
                return

            # Проверяем, состоит ли пользователь в чате
            if not is_user_in_chat(call.from_user.id):
                bot.send_message(
                    call.message.chat.id,
                    "❌ Для участия в конкурсе необходимо состоять в нашем чате\n"
                    + Links.get_chat_url(),
                    reply_markup=Menu.contests_menu(),
                )
                return

            user_id = call.from_user.id
            submission = ContestSubmission()
            bot.set_state(user_id, UserState.WAITING_CONTEST_PHOTOS)
            submission.status = UserState.WAITING_CONTEST_PHOTOS  # Устанавливаем начальный статус
            user_submissions.add(user_id, submission)

            text = "📸 Пришлите работу _до 10 фото без текста, его я попрошу позже_\n"

            if SubmissionManager.delete_judge(user_id):
                text += "\nВы будете удалены из списка судей"

            text += "\n🚫 Для отмены используйте /cancel"

            bot.send_message(
                call.message.chat.id,
                text,
                parse_mode="MarkdownV2",
            )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка начала отправки: {e}")
        handle_submission_error(call.from_user.id, e)


# Обработчик отправки работ
# Обработчик для приёма фото конкурсных работ
@bot.message_handler(
    content_types=["photo"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == UserState.WAITING_CONTEST_PHOTOS,
)
@lock_input(allow_media_groups=True)
def handle_contest_photos(message):
    user_id = message.from_user.id
    submission = user_submissions.get(user_id)
    
    # Обновляем активность
    submission.update_activity()
    user_submissions.update_last_activity(user_id)

    try:
        # Удаляем предыдущее сообщение с прогрессом
        if submission.progress_message_id:
            try:
                bot.delete_message(message.chat.id, submission.progress_message_id)
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")

        # Получаем оригинальное фото (последний элемент всегда наибольший)
        original_photo = message.photo[-1]
        unique_id = original_photo.file_unique_id

        # Проверка дубликатов
        existing_ids = {p["unique_id"] for p in submission.photos}
        if unique_id in existing_ids:
            bot.reply_to(message, "❌ Это фото уже было добавлено!")
            return

        # Проверка лимита
        if len(submission.photos) >= 10:
            bot.reply_to(message, "❌ Достигнут максимум 10 фото!")
            request_contest_description(user_id)
            return

        # Сохраняем данные
        submission.photos.append({
            "file_id": original_photo.file_id,
            "unique_id": unique_id
        })

        # Обновляем таймер последней активности
        submission.last_activity = time.time()

        # Автопереход при достижении лимита
        if len(submission.photos) == 10:
            request_contest_description(user_id)
        else:
            # Формируем прогресс-бар
            progress_bar = "🟪" * len(submission.photos) + "◻️" * (10 - len(submission.photos))
            
            # Отправляем обновлённое сообщение
            sent_msg = bot.reply_to(
                message,
                f"{progress_bar}\n"
                f"✅ Фото добавлено! Всего: {len(submission.photos)}/10\n"
                "Отправьте еще фото или нажмите /done\n\n"
                "🚫 Для отмены используйте /cancel"
            )
            submission.progress_message_id = sent_msg.message_id

    except Exception as e:
        handle_submission_error(user_id, e)

# Обработчик команды /done для завершения загрузки фото
@bot.message_handler(
    commands=["done"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == UserState.WAITING_CONTEST_PHOTOS,
)
@lock_input()
def handle_done_contest_photos(message):
    user_id = message.from_user.id
    submission = user_submissions.get(user_id)
    
    # Обновляем активность
    submission.update_activity()
    user_submissions.update_last_activity(user_id)

    # Проверка минимального количества
    if len(submission.photos) == 0:
        bot.reply_to(message, "❌ Нужно отправить хотя бы одно фото")
        return

    # Удаляем сообщение прогресса
    if submission.progress_message_id:
        try:
            bot.delete_message(message.chat.id, submission.progress_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

    request_contest_description(user_id)

def request_contest_description(user_id):
    submission = user_submissions.get(user_id)
    
    # Обновляем активность
    submission.update_activity()
    user_submissions.update_last_activity(user_id)

    submission.status = UserState.WAITING_CONTEST_TEXT
    bot.set_state(user_id, UserState.WAITING_CONTEST_TEXT)
    
    bot.send_message(
        user_id,
        "📝 Теперь отправьте текст для работы:\n"
        "Можно использовать эмодзи _не премиум_\n"
        "Максимум 1000 символов\n\n"
        "🚫 Для отмены используйте /cancel",
        parse_mode="MarkdownV2",
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: user_submissions.exists(m.from_user.id)
    and user_submissions.get(m.from_user.id).status == UserState.WAITING_CONTEST_TEXT,
)
@lock_input()
def handle_text(message):
    user_id = message.from_user.id
    submission = user_submissions.get(user_id)
    
    # Обновляем активность
    submission.update_activity()
    user_submissions.update_last_activity(user_id)

    try:
        submission.caption = message.text
        submission.status = UserState.WAITING_CONTEST_PREVIEW
        bot.set_state(user_id, UserState.WAITING_CONTEST_PREVIEW)

        # Показываем предпросмотр
        media = [types.InputMediaPhoto(pid['file_id']) for pid in submission.photos]
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
                "🚫 Отменить отправку работы", callback_data="cancel_submission"
            )
        )

        # Отправляем вопрос
        bot.send_message(
            message.chat.id,
            f"Предпросмотр вашей работы\n\nТекст:\n{submission.caption}\n\n\nОтправить работу во время проведения конкурса за Вас?",
            reply_markup=markup,
        )
    except Exception as e:
        handle_submission_error(user_id, e)


# Обработчик ответов
@bot.callback_query_handler(func=lambda call: call.data.startswith("send_by_bot_"))
@lock_input()
def handle_send_method(call):
    user_id = call.from_user.id
    if not user_submissions.exists(user_id):
        bot.answer_callback_query(call.id, "❌ Сессия отправки истекла")
        return

    try:
        submission = user_submissions.get(user_id)
    
        # Обновляем активность
        submission.update_activity()
        user_submissions.update_last_activity(user_id)

        user = bot.get_chat(user_id)
        full_name = (
            f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        )
        username = user.username if user.username else "отсутствует"
        # Сохраняем работу в БД со статусом "pending"
        submission_id = SubmissionManager.create_submission(
            user_id=user_id,
            username=username,
            full_name=full_name,
            photos=submission.photos,
            caption=submission.caption,
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

        user_info = get_user_info(bot.get_chat(user_id))
        # Формируем медиагруппу
        media = [types.InputMediaPhoto(pid['file_id']) for pid in submission.photos]

        # Отправляем в чат конкурса
        try:
            sent_messages = bot.send_media_group(chat_id=CONTEST_CHAT_ID, media=media)
            logger.info(f"Медиа работы отправлены в чат {CONTEST_CHAT_ID}: {sent_messages}")
            sent_messages = bot.send_message(
                chat_id=CONTEST_CHAT_ID,
                text=f"{submission.caption}\n\nОтправка ботом: {'✅ Да' if send_by_bot else '❌ Нет'}{user_info}",
            )
            logger.info(f"Текст работы отправлен в чат {CONTEST_CHAT_ID}: {sent_messages}")
        except Exception as e:
            logger.error(f"Ошибка отправки в чат: {str(e)}")
            raise

        # Уведомление пользователю
        bot.send_message(
            chat_id=user_id,
            text="✅ Работа отправлена админам! После проверки я пришлю номер!",
            reply_markup=Menu.contests_menu(),
        )
        bot.delete_state(user_id)

    except Exception as e:
        handle_submission_error(user_id, e)
        bot.answer_callback_query(call.id, "⚠️ Ошибка при отправке работы админам")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_submission")
@lock_input()
def handle_cancel_submission(call):
    user_id = call.from_user.id
    try:
        if user_submissions.exists(user_id):
            user_submissions.remove(user_id)
            bot.delete_state(user_id)
            bot.answer_callback_query(call.id, "❌ Отправка отменена")

            # Удаляем сообщения с предпросмотром
            for _ in range(2):  # Удаляем предпросмотр и кнопки
                try:
                    bot.delete_message(
                        call.message.chat.id, call.message.message_id - _
                    )
                except:
                    pass
            bot.send_message(
                user_id,
                "Вернуться в главное меню?",
                reply_markup=Menu.back_user_only_main_menu(),
            )
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
                            "⌛ Время на отправку истекло\! Начните заново",
                            reply_markup=Menu.contests_menu(),
                        )
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {str(e)}")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка таймера: {str(e)}", exc_info=True)


threading.Thread(target=check_timeout, daemon=True).start()


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_CONTEST_JUDGE
)
@private_chat_only(bot)
def handle_contest_judje(call):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(text="🧑‍⚖️ Записаться", callback_data="new_judge"),
        types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
        ),
    )
    bot.edit_message_text(
        f"Вы хотите записаться на судейство ближайшего конкурса?\n\n"
        "❗Напоминаю, что нельзя быть одновременно и судьёй, и участником: _при записи участником, запись на судейство аннулируется_\n\n"
        '⚠️Заявки рассматриваются админами вручную ближе к дате проведения конкурса: 🚫_для отмены ранее поданной заявки напишите выберите "сообщение админам" в главном меню_',
        call.message.chat.id,
        call.message.message_id,
        parse_mode="MarkdownV2",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "new_judge")
def handle_new_judge(call):
    user_id = call.from_user.id

    try:
        # Проверяем существующую запись
        if SubmissionManager.is_judge(user_id):
            bot.answer_callback_query(
                call.id, "❌ Вы уже подавали заявку на судейство\!", show_alert=True
            )
            return
        # Провекряем на участие
        if is_user_approved(user_id):
            bot.answer_callback_query(
                call.id, "❌ Вы уже записаны в качестве участника\!", show_alert=True
            )
            return
        # Добавляем в БД
        user = bot.get_chat(user_id)
        full_name = (
            f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        )
        username = user.username if user.username else "отсутствует"
        if SubmissionManager.add_judge(
            user_id=user_id, username=username, full_name=full_name
        ):
            user_info = get_user_info(bot.get_chat(user_id))
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "💬 Ответить", callback_data=f"reply_to_{user_id}"
                )
            )
            full_text = f"Новая заявка на судейство!\n{user_info}"
            bot.send_message(CONTEST_CHAT_ID, full_text, reply_markup=markup)

            bot.send_message(
                user_id,
                "✅ Заявка успешно отправлена!",
                reply_markup=Menu.back_user_only_main_menu(),
            )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ Не удалось отправить заявку, свяжитесь с админами",
                show_alert=True,
            )
    except Exception as e:
        logger.error(f"handle_new_judge error: {e}")
        bot.answer_callback_query(
            call.id,
            "⚠️ Произошла ошибка при отправке, свяжитесь с админами",
            show_alert=True,
        )


# РЕПКА


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_TURNIP)
@private_chat_only(bot)
def handle_user_turnip(call):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
        ),
    )
    bot.edit_message_text(
        f"На данный момент работа с репой отключена, но скоро мы её возобновим\!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )


# Общий обработчик отмены для сообщения админам и новостей
@bot.message_handler(
    commands=["cancel"],
    func=lambda message: bot.get_state(message.from_user.id)
    in [
        UserState.WAITING_ADMIN_CONTENT,
        UserState.WAITING_ADMIN_CONTENT_PHOTO,
        UserState.WAITING_NEWS_SCREENSHOTS,
        UserState.WAITING_NEWS_DESCRIPTION,
        UserState.WAITING_NEWS_SPEAKER,
        UserState.WAITING_NEWS_ISLAND,
        UserState.WAITING_CODE_VALUE,
        UserState.WAITING_CODE_SCREENSHOTS,
        UserState.WAITING_CODE_SPEAKER,
        UserState.WAITING_CODE_ISLAND,
        UserState.WAITING_POCKET_SCREEN,
        UserState.WAITING_DESIGN_CODE,
        UserState.WAITING_DESIGN_DESIGN_SCREEN,
        UserState.WAITING_DESIGN_GAME_SCREENS,
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


# СООБЩЕНИЕ АДМИНАМ


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_TO_ADMIN)
@lock_input()
@private_chat_only(bot)
def handle_user_to_admin(call):
    user_id = call.from_user.id
    if user_id in temp_storage:
        del temp_storage[user_id]
    user_content_storage.init_content(user_id)

    bot.set_state(
        user_id,
        UserState.WAITING_ADMIN_CONTENT,
    )

    bot.send_message(
        call.message.chat.id,
        "📤 Пришлите текст, который хотели бы отправить админам \(о фото я спрошу позже\)\n_Пишите текст тут в чате_\n"
        "🚫 Для отмены используйте /cancel",
        parse_mode="MarkdownV2",
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda message: (
        bot.get_state(message.from_user.id) == UserState.WAITING_ADMIN_CONTENT
        and not message.text.startswith("/")
    ),
)
@lock_input()
def handle_user_text(message):
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id, "content")
    content_data["text"] = message.text
    bot.set_state(user_id, UserState.WAITING_ADMIN_CONTENT_PHOTO)
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            "✅ Да", callback_data=f"confirm_admphoto:{user_id}"
        ),
        types.InlineKeyboardButton("❌ Нет", callback_data=f"skip_admphoto:{user_id}"),
    )
    markup.row(
        types.InlineKeyboardButton(
            "🚫 Отменить отправку", callback_data=f"cancel_admphoto:{user_id}"
        )
    )
    bot.send_message(
        message.chat.id,
        "Хотите добавить фото?",
        reply_markup=markup,
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(
        ("confirm_admphoto", "skip_admphoto", "cancel_admphoto")
    ),
)
@lock_input()
def handle_confirmation(call):
    try:
        # Проверка и парсинг данных
        if ":" not in call.data:
            raise ValueError("Некорректный формат callback данных")

        action, user_id_str = call.data.split(":", 1)
        user_id = int(user_id_str)

        # Верификация пользователя
        if call.from_user.id != user_id:
            bot.answer_callback_query(
                call.id, "❌ Неавторизованный доступ", show_alert=True
            )
            return

        # Удаление сообщения с кнопками
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.warning(f"Ошибка удаления сообщения: {str(e)}")

        # Получение данных
        content_data = user_content_storage.get_data(user_id, "content")

        # Проверка наличия данных
        if not content_data:
            bot.answer_callback_query(call.id, "❌ Сессия истекла, начните заново")
            return

        # Обработка действий
        if action == "confirm_admphoto":
            bot.send_message(
                user_id,
                "📸 Отправьте фото или нажмите /skip\n 🚫 Для отмены используйте /cancel",
                reply_markup=types.ReplyKeyboardRemove(),
            )

        elif action == "skip_admphoto":
            # Проверка обязательных полей
            if "text" not in content_data or not content_data["text"].strip():
                bot.send_message(user_id, "❌ Текст сообщения обязателен\!")
                return

            try:
                preview_to_admin_chat(user_id, content_data)
            except KeyError as e:
                logger.error(f"Missing key in content_data: {str(e)}")
                bot.send_message(user_id, "❌ Ошибка данных, начните заново")
            except Exception as e:
                logger.error(f"Preview error: {str(e)}")
                bot.send_message(user_id, "⚠️ Ошибка формирования предпросмотра")

        elif action == "cancel_admphoto":
            handle_cancel(call.message)

    except ValueError as ve:
        logger.error(f"Invalid callback data: {call.data} - {str(ve)}")
        handle_submission_error(call.from_user.id, e)

    except Exception as e:
        logger.error(f"Critical error in confirmation: {str(e)}", exc_info=True)
        handle_submission_error(call.from_user.id, e)


@bot.message_handler(
    content_types=["photo"],
    func=lambda message: bot.get_state(message.from_user.id)
    in [UserState.WAITING_ADMIN_CONTENT_PHOTO],
)
@lock_input(allow_media_groups=True)
def handle_adm_photo(message):
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id, "content")
    try:
        if message.photo:
            # Берем самое высокое разрешение (последний элемент в списке)
            photo_id = message.photo[-1].file_id

            if len(content_data["photos"]) > 10:
                bot.send_message(message.chat.id, "Максимум 10 скриншотов\!")
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
                "Отправьте ещё фото или нажмите /done\n\n🚫 Для отмены используйте /cancel",
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
        handle_submission_error(message.from_user.id, e)


@bot.message_handler(
    commands=["done"],
    func=lambda message: bot.get_state(message.from_user.id)
    in [UserState.WAITING_ADMIN_CONTENT_PHOTO],
)
@lock_input()
def handle_done(message):
    user_id = message.from_user.id
    content_data = user_content_storage.get_data(user_id, "content")
    # Удаляем последнее сообщение-счетчик
    if content_data.get("counter_msg_id"):
        try:
            bot.delete_message(message.chat.id, content_data["counter_msg_id"])
        except Exception as e:
            logger.debug(f"Ошибка удаления сообщения: {e}")

    preview_to_admin_chat(user_id, content_data)

    # Очищаем данные
    user_content_storage.clear(user_id)


def preview_to_admin_chat(user_id, content_data):
    # Сохраняем данные во временное хранилище
    temp_storage[user_id] = content_data

    # Показываем предпросмотр
    if content_data["photos"]:
        media = [types.InputMediaPhoto(pid) for pid in content_data["photos"]]
        bot.send_media_group(user_id, media)

    # Создаем клавиатуру
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            "✅ Отправить", callback_data=f"confirm_send:{user_id}"
        ),
        types.InlineKeyboardButton(
            "🚫 Отменить", callback_data=f"cancel_send:{user_id}"
        ),
    )
    bot.send_message(
        user_id,
        f"Предпросмотр:\n{content_data['text']}\n\nОтправить сообщение админам?",
        reply_markup=markup,
    )


# Обработчик кнопок подтверждения
@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("confirm_send", "cancel_send")),
)
@lock_input()
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
        logger.debug("send_to_admin_chat: ", content_data)
        target_chat = ADMIN_CHAT_ID
        text = content_data["text"]
        photos = content_data["photos"]

        user_info = get_user_info(bot.get_chat(user_id))

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
            "✅ Контент успешно отправлен\!",
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
@lock_input()
@private_chat_only(bot)
def handle_user_to_news(call):
    # Проверяем, состоит ли пользователь в чате
    if not is_user_in_chat(call.from_user.id):
        bot.send_message(
            call.message.chat.id,
            "❌ Для отправки новостей необходимо состоять в нашем чате\!\n"
            + Links.get_chat_url(),
            reply_markup=Menu.back_user_only_main_menu(),
        )
        return

    bot.edit_message_text(
        text="Что Вы хотите прислать в новостную колонку?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=Menu.news_menu(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_NEWS
)
@lock_input()
def handle_user_news_news(call):
    user_id = call.from_user.id
    if user_id in temp_storage:
        del temp_storage[user_id]
    user_content_storage.init_news(user_id)
    bot.set_state(user_id, UserState.WAITING_NEWS_SCREENSHOTS)
    # Сначала редактируем сообщение БЕЗ ForceReply
    bot.edit_message_text(
        text="📸 Пришлите до 10 скриншотов для новости\n 🚫 Для отмены используйте /cancel",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_CODE_DREAM
)
@lock_input()
def handle_news_code(call):
    user_id = call.from_user.id
    if user_id in temp_storage:
        del temp_storage[user_id]
    user_content_storage.init_code(user_id)
    bot.set_state(user_id, UserState.WAITING_CODE_VALUE)
    bot.edit_message_text(
        text="🔢 Пришлите код\n"
        "*Формат*: `DA-0000-0000-0000` _\(вместо 0 ваши цифры\)_\n"
        "🚫 Для отмены используйте /cancel",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="MarkdownV2",
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_CODE_DLC
)
@lock_input()
def handle_news_code(call):
    user_id = call.from_user.id
    if user_id in temp_storage:
        del temp_storage[user_id]
    user_content_storage.init_code(user_id)
    bot.set_state(user_id, UserState.WAITING_CODE_VALUE)
    bot.edit_message_text(
        text="🔢 Пришлите код\n"
        "*Формат*: `RA-0000-0000-0000` _\(вместо 0 ваши цифры\)_\n"
        "🚫 Для отмены используйте /cancel",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="MarkdownV2",
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_POCKET,
)
@lock_input()
def handle_news_pocket(call):
    user_id = call.from_user.id
    if user_id in temp_storage:
        del temp_storage[user_id]
    user_content_storage.init_pocket(user_id)
    bot.set_state(user_id, UserState.WAITING_POCKET_SCREEN)
    bot.edit_message_text(
        text="📸 Вам необходимо подготовить 2 скриншота карточки дружбы: лицевую и обратную стороны\n"
        'Лучше всего это сделать через кнопку "SAVE"\!\n\n'
        "⬇️ Отправьте оба скриншота в чат\n"
        "🚫 Для отмены используйте /cancel",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )


@bot.callback_query_handler(
    func=lambda call: call.data == ButtonCallback.USER_NEWS_DESIGN,
)
@lock_input()
def handle_news_design(call):
    user_id = call.from_user.id
    if user_id in temp_storage:
        del temp_storage[user_id]
    user_content_storage.init_design(user_id)
    bot.set_state(user_id, UserState.WAITING_DESIGN_CODE)
    bot.edit_message_text(
        text="🎨 Введите код дизайна в формате:\n`MA-0000-0000-0000`\n🚫 Для отмены используйте /cancel",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )


def validate_code(pattern, code):
    return re.match(pattern, code.strip(), re.IGNORECASE) is not None


def parse_speaker_info(text):
    parts = [p.strip() for p in text.split(",", 1)]
    return parts[0], parts[1] if len(parts) > 1 else None


# Обработчики для USER_NEWS_NEWS
@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_NEWS_SCREENSHOTS,
)
@lock_input(allow_media_groups=True)
def handle_news_screenshots(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "news")

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
        bot.reply_to(message, "❌ Это изображение уже было добавлено\!")
        return

    # 4. Проверяем лимит
    if len(data.get("photos", [])) > 10:
        bot.reply_to(message, "❌ Достигнут максимум 10 скриншотов\!")
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
            f"✅ Скриншот добавлен\! Всего: {len(data['photos'])}/10\n"
            "Отправьте еще или нажмите /done\n\n🚫 Для отмены используйте /cancel",
        )
        # Сохраняем ID сообщения для последующего удаления
        data["progress_message_id"] = sent_msg.message_id
        user_content_storage.update_data(user_id, data)


def request_description(user_id):
    bot.set_state(user_id, UserState.WAITING_NEWS_DESCRIPTION)
    bot.send_message(
        user_id,
        "📝 Напишите описание новости \(или /skip\)\n🚫 Для отмены используйте /cancel",
    )


@bot.message_handler(
    commands=["done"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_NEWS_SCREENSHOTS,
)
@lock_input()
def handle_done_news_photos(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "news")

    # Удаляем сообщение прогресса
    if data.get("progress_msg_id"):
        try:
            bot.delete_message(message.chat.id, data["progress_msg_id"])
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

    if len(data.get("photos", [])) == 0:
        bot.reply_to(message, "❌ Вы не отправили ни одного фото\!")
        return

    request_description(user_id)


@bot.message_handler(
    commands=["skip"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_NEWS_DESCRIPTION,
)
@lock_input()
def skip_news_description(message):
    user_id = message.from_user.id
    bot.set_state(user_id, UserState.WAITING_NEWS_SPEAKER)
    bot.send_message(
        message.chat.id, "👤 Введите имя спикера:\n🚫 Для отмены используйте /cancel"
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_NEWS_DESCRIPTION,
)
@lock_input()
def handle_news_description(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "news")
    data["description"] = message.text
    bot.set_state(user_id, UserState.WAITING_NEWS_SPEAKER)
    bot.send_message(
        message.chat.id, "👤 Введите имя спикера:\n🚫 Для отмены используйте /cancel"
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_NEWS_SPEAKER,
)
@lock_input()
def handle_news_speaker(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "news")
    data["speaker"] = message.text
    bot.set_state(user_id, UserState.WAITING_NEWS_ISLAND)
    bot.send_message(
        message.chat.id,
        "🏝️ Введите название острова:\n🚫 Для отмены используйте /cancel",
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_NEWS_ISLAND,
)
@lock_input()
def handle_news_island(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "news")
    data["island"] = message.text
    preview_send_to_news_chat(user_id)


# Обработчики для USER_NEWS_CODE
@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_CODE_VALUE,
)
@lock_input()
def handle_code_value(message):
    user_id = message.from_user.id
    code = message.text.upper()

    if not validate_code(r"^[DR]A-\d{4}-\d{4}-\d{4}$", code):
        bot.reply_to(message, "❌ Неверный формат кода\! Пример: DA-1234-5678-9012")
        return

    user_content_storage.get_data(user_id, "code")["code"] = code
    bot.set_state(user_id, UserState.WAITING_CODE_SCREENSHOTS)
    bot.send_message(
        message.chat.id,
        "📸 Пришлите до 10 скриншотов:\n🚫 Для отмены используйте /cancel",
    )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_CODE_SCREENSHOTS,
)
@lock_input(allow_media_groups=True)
def handle_code_screenshots(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "code")

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
        bot.reply_to(message, "❌ Это изображение уже было добавлено\!")
        return

    # 4. Проверяем лимит
    if len(data.get("photos", [])) > 10:
        bot.reply_to(message, "❌ Достигнут максимум 10 скриншотов\!")
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
            f"✅ Скриншот добавлен\! Всего: {len(data['photos'])}/10\n"
            "Отправьте еще или нажмите /done\n\n🚫 Для отмены используйте /cancel",
        )
        # Сохраняем ID сообщения для последующего удаления
        data["progress_message_id"] = sent_msg.message_id
        user_content_storage.update_data(user_id, data)


def request_speaker(user_id):
    bot.set_state(user_id, UserState.WAITING_CODE_SPEAKER)
    bot.send_message(
        user_id, "👤 Введите имя спикера:\n🚫 Для отмены используйте /cancel"
    )


@bot.message_handler(
    commands=["done"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_CODE_SCREENSHOTS,
)
@lock_input()
def handle_done_news_photos(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "code")

    # Удаляем сообщение прогресса
    if data.get("progress_msg_id"):
        try:
            bot.delete_message(message.chat.id, data["progress_msg_id"])
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

    if len(data.get("photos", [])) == 0:
        bot.reply_to(message, "❌ Вы не отправили ни одного фото\!")
        return

    request_speaker(user_id)


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_CODE_SPEAKER,
)
@lock_input()
def handle_code_speaker(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "code")
    data["speaker"] = message.text
    bot.set_state(user_id, UserState.WAITING_CODE_ISLAND)
    bot.send_message(
        message.chat.id,
        "🏝️ Введите название острова:\n🚫 Для отмены используйте /cancel",
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_CODE_ISLAND,
)
@lock_input()
def handle_code_island(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "code")
    data["island"] = message.text
    preview_send_to_news_chat(user_id)


pocket_media_groups = {}
pocket_user_locks = {}
# Добавляем кэш для отслеживания отправленных ошибок
error_media_groups = {}


# Обработчики для USER_NEWS_POCKET
@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_POCKET_SCREEN,
)
@lock_input(allow_media_groups=True)
def handle_pocket_screens(message):
    user_id = message.from_user.id

    try:
        data = user_content_storage.get_data(user_id, "pocket")

        # Обработка медиагруппы
        if message.media_group_id:
            return handle_media_group(message, data, user_id)

        # Обработка одиночного фото
        handle_single_photo(message, data, user_id)

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        handle_pocket_error(user_id)


def handle_media_group(message, data, user_id):
    media_group_id = message.media_group_id
    # Проверяем, была ли уже обработана эта группа
    if media_group_id in error_media_groups:
        return  # Пропускаем повторную обработку

    # Проверяем, есть ли уже сохраненные фото
    existing_photos = user_content_storage.get_data(user_id, "pocket").get("photos", [])
    if len(existing_photos) > 0:
        # Помечаем группу как обработанную с ошибкой
        error_media_groups[media_group_id] = True
        bot.send_message(
            user_id,
            "❌ _Вы уже отправили 1 фото ранее, а сейчас отправляете ещё несколько\!_\nПришлите второе фото заново\!",
            parse_mode="MarkdownV2",
        )
        # Устанавливаем таймер для очистки кэша (5 минут)
        threading.Timer(
            300, lambda: error_media_groups.pop(media_group_id, None)
        ).start()
        return

    largest_photo = max(message.photo, key=lambda p: p.file_size)
    mg_id = message.media_group_id

    # Если группа новая - сбрасываем предыдущие данные
    if mg_id not in pocket_media_groups:
        pocket_media_groups[mg_id] = {
            "user_id": user_id,
            "photos": [],
            "timer": threading.Timer(3.0, process_pocket_group, [mg_id]),
        }
        pocket_media_groups[mg_id]["timer"].start()
    else:
        # Если в группе уже 2+ фото - отменяем обработку
        if len(pocket_media_groups[mg_id]["photos"]) >= 2:
            pocket_media_groups[mg_id]["timer"].cancel()
            del pocket_media_groups[mg_id]
            handle_pocket_error(user_id, "❌ Можно отправить только 2 фото\!")
            return

    # Добавляем уникальные фото
    if not any(
        p["unique_id"] == largest_photo.file_unique_id
        for p in pocket_media_groups[mg_id]["photos"]
    ):
        pocket_media_groups[mg_id]["photos"].append(
            {
                "file_id": largest_photo.file_id,
                "unique_id": largest_photo.file_unique_id,
            }
        )

        # Если превысили лимит - сразу отменяем
        if len(pocket_media_groups[mg_id]["photos"]) > 2:
            handle_pocket_error(user_id, "❌ Можно отправить только 2 фото\!")
            pocket_media_groups[mg_id]["timer"].cancel()
            del pocket_media_groups[mg_id]


def handle_single_photo(message, data, user_id):
    # Проверка инициализации
    if "photos" not in data:
        user_content_storage.init_pocket(user_id)
        data = user_content_storage.get_data(user_id)

    largest_photo = max(message.photo, key=lambda p: p.file_size)

    # Добавление фото
    data["photos"].append(
        {"file_id": largest_photo.file_id, "unique_id": largest_photo.file_unique_id}
    )

    # Лимит фото
    if len(data["photos"]) > 2:
        handle_pocket_error(user_id, "❌ Максимум 2 фото\!")
        return

    user_content_storage.update_data(user_id, data)

    # Логика переходов
    if len(data["photos"]) == 1:
        bot.send_message(user_id, "📸 Отправьте второе фото")
    elif len(data["photos"]) == 2:
        finish_pocket_submission(user_id)


def process_pocket_group(media_group_id):
    group_data = pocket_media_groups.pop(media_group_id, None)
    if not group_data:
        return

    user_id = group_data["user_id"]
    try:
        # Проверяем окончательное количество
        if len(group_data["photos"]) != 2:
            handle_pocket_error(user_id, "❌ Нужно отправить ровно 2 фото\!")
            return

        # Сохраняем и обрабатываем
        data = user_content_storage.get_data(user_id, "pocket")
        data["photos"] = group_data["photos"]
        user_content_storage.update_data(user_id, data)
        finish_pocket_submission(user_id)

    except Exception as e:
        handle_pocket_error(user_id, f"❌ Ошибка: {str(e)}")


def handle_pocket_error(user_id, message="❌ Ошибка обработки"):
    user_content_storage.clear(user_id)
    bot.delete_state(user_id)
    bot.send_message(user_id, message, reply_markup=Menu.news_menu())
    # Отменяем все таймеры для пользователя
    for mg_id, group in list(pocket_media_groups.items()):
        if group["user_id"] == user_id:
            group["timer"].cancel()
            del pocket_media_groups[mg_id]


def finish_pocket_submission(user_id):
    try:
        bot.delete_state(user_id)
        preview_send_to_news_chat(user_id)
    finally:
        user_content_storage.clear(user_id)
        pocket_user_locks.pop(user_id, None)


# Обработчик неверного контента
@bot.message_handler(
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_POCKET_SCREEN
    and m.content_type != "photo",
)
@lock_input()
def handle_invalid_content(message):
    bot.send_message(
        message.chat.id,
        "❌ Пожалуйста, отправьте фото\n🚫 Для отмены используйте /cancel",
    )


# Обработчики для USER_NEWS_DESIGN
@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_DESIGN_CODE,
)
@lock_input()
def handle_design_code(message):
    user_id = message.from_user.id
    code = message.text.upper()

    if not validate_code(r"^MA-\d{4}-\d{4}-\d{4}$", code):
        bot.reply_to(message, "❌ Неверный формат\! Пример: MA-1234-5678-9012")
        return

    user_content_storage.get_data(user_id, "design")["code"] = code
    bot.set_state(user_id, UserState.WAITING_DESIGN_DESIGN_SCREEN)
    bot.send_message(
        message.chat.id,
        "📸 Пришлите скриншот из приложения дизайнера:\n🚫 Для отмены используйте /cancel",
    )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id)
    == UserState.WAITING_DESIGN_DESIGN_SCREEN,
)
@lock_input(allow_media_groups=True)
def handle_design_screen(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "design")

    # Проверяем, что это не альбом
    if message.media_group_id:
        bot.reply_to(message, "❌ Отправьте одно фото\!")
        return

    # Сохраняем последний (наибольший) размер фото
    photo_data = {
        "file_id": message.photo[-1].file_id,
        "unique_id": message.photo[-1].file_unique_id,
    }

    data["design_screen"].append(photo_data)
    user_content_storage.update_data(user_id, data)

    bot.set_state(user_id, UserState.WAITING_DESIGN_GAME_SCREENS)
    bot.send_message(
        message.chat.id,
        "🎮 Пришлите до 9 \(НЕ 10\) скриншотов с применением рисунка в игре:\n🚫 Для отмены используйте /cancel",
    )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: bot.get_state(m.from_user.id)
    == UserState.WAITING_DESIGN_GAME_SCREENS,
)
@lock_input(allow_media_groups=True)
def handle_game_screens(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "design")

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
        bot.reply_to(message, "❌ Это изображение уже было добавлено\!")
        return

    # 4. Проверяем лимит
    if len(data.get("game_screens", [])) >= 9:
        bot.reply_to(message, "❌ Достигнут максимум 9 скриншотов\!")
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
        f"✅ Скриншот добавлен\! Всего: {len(data['game_screens'])}/9\n"
        "Отправьте еще или нажмите /done\n\n🚫 Для отмены используйте /cancel",
    )
    # Сохраняем ID сообщения для последующего удаления
    data["progress_message_id"] = sent_msg.message_id
    user_content_storage.update_data(user_id, data)


@bot.message_handler(
    commands=["done"],
    func=lambda message: bot.get_state(message.from_user.id)
    == UserState.WAITING_DESIGN_GAME_SCREENS,
)
@lock_input()
def handle_done(message):
    user_id = message.from_user.id
    data = user_content_storage.get_data(user_id, "design")

    try:
        if data.get("progress_message_id"):
            bot.delete_message(message.chat.id, data["progress_message_id"])
    except Exception as e:
        logger.warning(f"Ошибка удаления прогресса: {e}")

    preview_send_to_news_chat(user_id)


def preview_send_to_news_chat(user_id):
    try:
        # Получаем данные из хранилища
        data = user_content_storage.get_data(user_id, "design")
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
            text = f"Отправка кода (сон или курорт)\n"
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
        temp_storage[user_id] = {
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
                "🚫 Отменить", callback_data=f"news_cancel_{user_id}"
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
            "❌ Произошла ошибка\nПопробуйте начать заново.",
            reply_markup=Menu.back_user_only_main_menu(),
        )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("news_confirm_", "news_cancel_")),
)
@lock_input()
def handle_preview_actions_send_to_news_chat(call):
    user_id = call.from_user.id
    action, target_user_id = call.data.split("_")[-2:]
    target_user_id = int(target_user_id)
    target_chat = NEWSPAPER_CHAT_ID

    try:
        if action == "confirm":
            # Получаем данные из хранилища
            data = temp_storage.get(target_user_id)

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
                logger.debug(f"Отправка медиагруппы из {len(data['media'])} элементов")
                bot.send_media_group(target_chat, data["media"])
                bot.send_message(
                    target_chat,
                    text=f"Текст:\n{data['text']}\n\nИнфо о пользователе:\n{data['user_info']}\n\nХотите ответить?",
                    reply_markup=markup,
                )

            bot.answer_callback_query(
                call.id,
                "✅ Публикация отправлена\!",
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
        if user_id in temp_storage:
            del temp_storage[user_id]
        user_content_storage.clear(user_id)
        bot.delete_state(user_id)
        logger.debug("Данные пользователя очищены")