from datetime import datetime
from telebot import types
from database.contest import ContestManager
from bot_instance import bot
from menu.menu import Menu
from menu.constants import ButtonCallback, ButtonText, ConstantLinks

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