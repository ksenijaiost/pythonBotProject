import logging
from datetime import datetime

from database.contest import ContestManager
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

# Обработчик кнопки "Обновить информацию" в админ-меню
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.ADM_CONTEST_INFO)
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
