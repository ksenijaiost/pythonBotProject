from datetime import datetime
import threading
from telebot import types
import time
from database.contest import ContestManager
from bot_instance import bot
from handlers.envParams import ADMIN_USERNAME, CONTEST_CHAT_ID
from menu.menu import Menu
from menu.constants import ButtonCallback, ButtonText, ConstantLinks


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_GUIDES)
def handle_user_guides(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню гайдов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_FIND_GUIDE)
def handle_user_find_guide(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "На данный момент поиск недоступен, но Вы можете посмотреть все гайды на нашем сайте",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.guides_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST)
def handle_user_guides(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов. Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.contests_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST_INFO)
def handle_user_contest_info(call):
    try:
        # Получаем данные о текущем конкурсе
        contest = ContestManager.get_current_contest()
        
        if not contest:
            # Если конкурсов нет в базе
            text = "🎉 В настоящее время активных конкурсов нет.\nСледите за обновлениями!"
            markup = Menu.back_to_main_menu()
        else:
            current_date = datetime.now().date()
            end_date_obj = datetime.strptime(contest[4], "%d.%m.%Y").date()

            if end_date_obj < current_date:
                text += "\n\n❗️ *Приём работ на конкурс завершён! Следите за обновлениями!*"

            # Парсим данные из базы
            theme = contest[1]
            description = contest[2]
            contest_date = datetime.strptime(contest[3], "%d.%m.%Y").strftime("%d %B %Y")
            end_date_of_admission = datetime.strptime(contest[4], "%d.%m.%Y").strftime("%d %B %Y")

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
                    text="📜 Правила участия", 
                    url=ConstantLinks.CONTEST_LINK
                )
            )
            markup.row(
                types.InlineKeyboardButton(ButtonText.BACK, callback_data=ButtonCallback.USER_CONTEST),
                types.InlineKeyboardButton(ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU)
            )

        # Редактируем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Ошибка при выводе информации о конкурсе: {e}")
        bot.answer_callback_query(
            call.id,
            "⚠️ Произошла ошибка при загрузке информации",
            show_alert=True
        )


SUBMISSION_TIMEOUT = 300  # 5 минут на подтверждение

# Временное хранилище
user_submissions = {}

class ContestSubmission:
    def __init__(self):
        self.photos = []
        self.caption = ""
        self.send_by_bot = None  # True/False
        self.submission_time = time.time()

@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_CONTEST_SEND)
def start_contest_submission(call):
    try:
        user_id = call.from_user.id
        user_submissions[user_id] = ContestSubmission()
        
        bot.send_message(
            call.message.chat.id,
            "📸 Пришлите работу (до 10 фото с текстом или без):",
            reply_markup=types.ForceReply()
        )
        
    except Exception as e:
        print(f"Ошибка начала отправки: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка начала отправки", show_alert=True)

@bot.message_handler(content_types=['photo', 'text'], func=lambda m: m.from_user.id in user_submissions)
def handle_work_submission(message):
    user_id = message.from_user.id
    submission = user_submissions[user_id]
    
    try:
        if message.photo:
            largest_photo = max(message.photo, key=lambda p: p.file_size)
            submission.photos.append(largest_photo.file_id)
        
        if message.caption:
            submission.caption = message.caption
        elif message.text:
            submission.caption = message.text
            
        # Проверяем наличие хотя бы одного фото
        if not submission.photos:
            raise ValueError("Требуется хотя бы одно фото")
        
        # Сохраняем фото
        if message.photo:
            if len(submission.photos) >= 10:
                bot.reply_to(message, "❌ Максимум 10 фото!")
                return
            largest_photo = max(message.photo, key=lambda p: p.file_size)
            submission.photos.append(largest_photo.file_id)
        
        # Сохраняем текст
        if message.caption:
            submission.caption = message.caption
        elif message.text:
            submission.caption = message.text
            
        # Задаем вопрос
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Да", callback_data="send_by_bot_yes"),
            types.InlineKeyboardButton("❌ Нет, отправлю сам(а)", callback_data="send_by_bot_no")
        )
        
        bot.send_message(
            message.chat.id,
            "Отправить работу во время проведения конкурса за Вас?",
            reply_markup=markup
        )
        
    except ValueError as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}")
        del user_submissions[user_id]
    except Exception as e:
        handle_submission_error(user_id, e)

@bot.callback_query_handler(func=lambda call: call.data.startswith('send_by_bot_'))
def handle_send_method(call):
    user_id = call.from_user.id
    if user_id not in user_submissions:
        return
    
    try:
        submission = user_submissions[user_id]
        submission.send_by_bot = call.data == 'send_by_bot_yes'
        
        # Отправляем работу в чат конкурса
        caption = f"{submission.caption}\n\n"
        caption += f"Автор: @{call.from_user.username}\n"
        caption += f"Отправка админами: {'✅ Да' if submission.send_by_bot else '❌ Нет'}"
        
        if submission.photos:
            if len(submission.photos) == 1:
                bot.send_photo(
                    CONTEST_CHAT_ID,
                    submission.photos[0],
                    caption=caption
                )
            else:
                media = [types.InputMediaPhoto(pid) for pid in submission.photos]
                media[0].caption = caption
                bot.send_media_group(CONTEST_CHAT_ID, media)
        else:
            bot.send_message(CONTEST_CHAT_ID, caption)
            
        # Уведомление пользователю
        bot.send_message(
            user_id,
            "✅ Работа принята на проверку! После проверки Вам пришлют номер.",
            reply_markup=Menu.main_menu()
        )
        
        del user_submissions[user_id]
        
    except Exception as e:
        handle_submission_error(user_id, e)

def handle_submission_error(user_id, error):
    print(f"Ошибка отправки: {error}")
    if user_id in user_submissions:
        del user_submissions[user_id]
    
    bot.send_message(
        user_id,
        f"⚠️ Произошла ошибка! Свяжитесь с @{ADMIN_USERNAME}",
        reply_markup=Menu.main_menu()
    )

# Таймаут 10 минут
def check_timeout():
    while True:
        try:
            current_time = time.time()
            for user_id in list(user_submissions.keys()):
                if current_time - user_submissions[user_id].submission_time > 600:
                    del user_submissions[user_id]
                    bot.send_message(
                        user_id, 
                        "⌛ Время на отправку истекло! Начните заново.",
                        reply_markup=Menu.main_menu()
                    )
            time.sleep(60)
        except Exception as e:
            print(f"Ошибка таймера: {e}")

threading.Thread(target=check_timeout, daemon=True).start()
