class ButtonText:
    # Кнопки назад
    BACK = "🔙 Назад"
    MAIN_MENU = "🏠 В главное меню"

    # Пользовательские
    # Главное меню
    USER_GUIDES = "📚 Гайды"
    USER_CONTEST = "🏆 Конкурсы"
    USER_TO_ADMIN = "📨 Сообщение админам"
    USER_TO_NEWS = "📰 Новости в газету"
    USER_TURNIP = "🥕 Репка"
    USER_HEAD_CHAT = "🐻 Наш чат Animal Crossing"
    USER_CHANEL = "📢 Наш канал"
    USER_CHAT_NINTENDO = "🎮 Чат с темами"
    # Меню гайдов
    USER_GUIDE_SITE = "🌐 Перейти на сайт"
    USER_FIND_GUIDE = "🔍 Поиск по ключевым словам"
    # Меню конкурсов
    USER_CONTEST_INFO = "ℹ️ Узнать про конкурс"
    USER_CONTEST_SEND = "🎨 Отправить работу"
    USER_CONTEST_JUDGE = "⚖️ Записаться на судейство"

    # Администраторские
    # Главное меню
    ADM_CONTEST = "Конкурс"
    ADM_TURNIP = "Репка"
    ADM_ADD_GUIDE = "Добавить гайд"
    # Меню конкурсов
    ADM_CONTEST_INFO = "Информация о конкурсе"
    ADM_REVIEW_WORKS = "👁 Проверить работы"
    ADM_CONTEST_STATS = "Статистика по конкурсу"
    ADM_APPROVE = "✅ Одобрить"
    ADM_REJECT = "❌ Отклонить"
    ADM_CONTEST_RESET = "Сбросить счётчик работ"


class ButtonCallback:
    # Назад
    BACK_CONTEST = "back_contest"
    BACK_GUIDE = "back_guide"
    MAIN_MENU = "main_menu"
    # Пользовательские
    # Главное меню
    USER_GUIDES = "user_guides"
    USER_CONTEST = "user_contest"
    USER_TO_ADMIN = "user_to_admin"
    USER_TO_NEWS = "user_to_news"
    USER_TURNIP = "user_turnip"
    # Меню гайдов
    USER_FIND_GUIDE = "find_guide"
    # Меню конкурсов
    USER_CONTEST_INFO = "user_contest_info"
    USER_CONTEST_SEND = "user_contest_send"
    USER_CONTEST_JUDGE = "user_contest_judge"
    # Администраторские
    # Главное меню
    ADM_CONTEST = "adm_contest"
    ADM_TURNIP = "adm_turnip"
    ADM_ADD_GUIDE = "adm_add_guide"
    # Меню конкурсов
    ADM_CONTEST_INFO = "adm_contest_info"
    ADM_CONTEST_RESET = "adm_consest_reset"
    ADM_REVIEW_WORKS = "adm_review_works"
    ADM_CONTEST_STATS = "stats"
    ADM_APPROVE = "adm_approve_"
    ADM_REJECT = "adm_reject_"


class ConstantLinks:
    # Сайт
    SITE = "https://acnh.tilda.ws"
    # Конкурсы
    CONTEST_LINK = "https://acnh.tilda.ws/contest#rules"


class UserState:
    WAITING_ADMIN_CONTENT = "waiting_admin_content"
    WAITING_NEWS_CONTENT = "waiting_news_content"
