import logging
from datetime import datetime
import traceback
from telebot import types

from database.contest import ContestManager, SubmissionManager, get_submission
from handlers.envParams import admin_ids
from bot_instance import bot
from menu.constants import ButtonCallback
from menu.menu import Menu

logging.basicConfig(level=logging.DEBUG)

# storage.py
from threading import Lock

class TempStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()

    def get_user_step(self, user_id):
        with self.lock:
            return self.data.get(user_id, {}).get('step')

    def set_user_step(self, user_id, step):
        with self.lock:
            if user_id not in self.data:
                self.data[user_id] = {}
            self.data[user_id]['step'] = step

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
    'theme': 'Введите тему конкурса:',
    'description': 'Введите описание:',
    'contest_date': 'Введите дату проведения конкурса (ДД.ММ.ГГГГ):',
    'end_date_of_admission': 'Введите дату окончания приёма работ (ДД.ММ.ГГГГ):'
}


# Меню конкурсов для админа
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST)
def handle_adm_contest(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    bot.edit_message_text(
        "Меню конкурсов (адм). Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=Menu.adm_contests_menu()
    )


# Обработчик кнопки "Обновить информацию" в админ-меню
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_INFO)
def start_contest_update(call):
    try:
        # Получаем текущий конкурс
        contest = ContestManager.get_current_contest()
        
        # Формируем сообщение с текущими данными
        text = "📋 *Текущие данные конкурса:*\n\n"
        markup = types.InlineKeyboardMarkup()
        
        if contest:
            theme = contest[1]
            description = contest[2]
            contest_date = contest[3]
            end_date_of_admission = contest[4]
            
            text += (
                f"🏷 Тема: {theme}\n"
                f"📝 Описание: {description}\n"
                f"🗓 Дата проведения: {contest_date}\n"
                f"⏳ Приём работ до: {end_date_of_admission}\n\n"
                "Хотите изменить данные?"
            )
            
            markup.row(
                types.InlineKeyboardButton("✅ Да, обновить", callback_data="confirm_update"),
                types.InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_update")
            )
        else:
            text += "⚠️ Активных конкурсов не найдено.\nХотите создать новый?"
            markup.row(
                types.InlineKeyboardButton("➕ Создать новый", callback_data="confirm_update"),
                types.InlineKeyboardButton("🔙 Назад", callback_data="cancel_update")
            )

        # Отправляем сообщение с подтверждением
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=markup
        )

    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка загрузки данных", show_alert=True)

# Обработчик отмены
@bot.callback_query_handler(func=lambda call: call.data == "cancel_update")
def handle_cancel_update(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Действие отменено", reply_markup=Menu.back_adm_contest_menu())

# Обработчик подтверждения обновления
@bot.callback_query_handler(func=lambda call: call.data == "confirm_update")
def start_contest_update(call):
    print(f"Received callback: {call.data}, chat_id: {call.message.chat.id}")
    if call.message.chat.id not in admin_ids:
        return
    storage.set_user_step(call.from_user.id, 'theme')
    bot.send_message(call.message.chat.id, ADMIN_STEPS['theme'])

@bot.message_handler(func=lambda m: storage.get_user_step(m.from_user.id) in ADMIN_STEPS)
def handle_admin_input(message):
    user_id = message.from_user.id
    current_step = storage.get_user_step(user_id)
    
    # Обработка отмены
    if message.text.lower() == '/cancel':
        storage.clear(user_id)
        bot.send_message(message.chat.id, "❌ Операция отменена")
        return

    # Валидация даты
    if current_step in ['contest_date', 'end_date_of_admission']:
        try:
            datetime.strptime(message.text, "%d.%m.%Y")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат даты!")
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
            data['theme'],
            data['description'],
            data['contest_date'],
            data['end_date_of_admission']
        )
        storage.clear(user_id)
        bot.send_message(message.chat.id, "✅ Данные обновлены!", reply_markup=Menu.back_adm_contest_menu())

def process_approval(message, submission_id):
    try:
        # Только здесь генерируем номер
        number = SubmissionManager.approve_submission(submission_id)
        
        submission = get_submission(submission_id)
        user_id = submission['user_id']
        
        bot.send_message(
            user_id,
            f"✅ Ваша работа одобрена!\nНомер работы: #{number}",
            reply_markup=Menu.main_menu()
        )
        
        bot.send_message(message.chat.id, f"Работа #{submission_id} одобрена как №{number}!")

    except Exception as e:
        handle_admin_error(message.chat.id, e)

def process_rejection(message, submission_id):
    try:
        SubmissionManager.update_submission(submission_id, 'rejected', message.text)
        
        submission = get_submission(submission_id)
        user_id = submission['user_id']
        bot.send_message(
            submission[1],
            f"❌ Работа отклонена!\nПричина: {message.text}",
            reply_markup=Menu.main_menu()
        )
        
        bot.send_message(message.chat.id, f"Работа #{submission_id} отклонена!")
        
    except Exception as e:
        handle_admin_error(message.chat.id, e)


def handle_admin_error(chat_id, error):
    """Обработка ошибок в админских функциях"""
    error_msg = (
        "⚠️ *Ошибка администратора*\n"
        f"```{str(error)}```\n"
        "Пожалуйста, проверьте логи для деталей."
    )
    
    try:
        bot.send_message(
            chat_id, 
            error_msg, 
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Не удалось отправить сообщение об ошибке: {e}")
    
    # Логирование в консоль
    print(f"\n❌ ADMIN ERROR [{datetime.now()}]:")
    traceback.print_exc()
    
    # Логирование в файл (опционально)
    with open("admin_errors.log", "a") as f:
        f.write(f"\n[{datetime.now()}] {traceback.format_exc()}\n")


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_RESET)
def handle_adm_contest_reset(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить сброс", callback_data="confirm_reset"),
        types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_reset")
    )
    
    current_count = SubmissionManager.get_current_number()
    bot.send_message(
        call.message.chat.id,
        f"⚠️ Текущее количество участников: {current_count}\n"
        "Вы уверены, что хотите сбросить счетчик?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "confirm_reset")
def confirm_reset(call):
    SubmissionManager.reset_counter()
    bot.send_message(call.message.chat.id, "✅ Счетчик участников сброшен!", reply_markup=Menu.adm_contests_menu())