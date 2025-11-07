class ButtonText:
    # Кнопки назад
    BACK = "🔙 Назад"
    MAIN_MENU = "🏠 В главное меню"

    # Пользовательские
    USER_HELP = "🆘 Помощь"
    USER_HELP_SITE = "🆘 Инструкция по боту"
    # Главное меню
    USER_GUIDES = "📚 Гайды"
    USER_CONTEST = "🏆 Конкурсы"
    USER_TO_ADMIN = "📨 Сообщение админам"
    USER_TO_NEWS = "📰 Новости в газету"
    USER_TURNIP = "🥕 Репка, в разработке"
    USER_HEAD_CHAT = "🐻 Чат по Animal Crossing"
    USER_CHANEL = "📢 Канал по Animal Crossing"
    USER_CHAT_NINTENDO = "🎮 Чат по Nintendo играм, оффтоп"
    # Меню гайдов
    USER_GUIDE_SITE = "🌐 Перейти на сайт"
    USER_FIND_GUIDE = "🔍 Поиск гайдов, в разработке"
    # Меню конкурсов
    USER_CONTEST_INFO = "ℹ️ Узнать про конкурс"
    USER_CONTEST_SEND = "🎨 Отправить работу"
    USER_CONTEST_JUDGE = "⚖️ Записаться на судейство"
    # Меню новостей
    USER_NEWS_SITE = "🌐 Посмотреть прошлые выпуски"
    USER_NEWS_NEWS = "📰 Отправить новость в газету"
    USER_NEWS_CODE_DREAM = "🛏️ Отправить код сна"
    USER_NEWS_CODE_DLC = "🏡 Отправить код курортного бюро"
    USER_NEWS_POCKET = "👋 Отправить код дружбы PocketCamp"
    USER_NEWS_DESIGN = "🎨 Отправить код кастомного дизайна"

    # Администраторские
    # Главное меню
    ADM_CONTEST = "🏆 Конкурс"
    ADM_TURNIP = "🥕 Репка"
    ADM_ADD_GUIDE = "📚 Добавить гайд"
    ADM_BLOCK = "🚫 Список блокировок"
    # Меню конкурсов
    ADM_CONTEST_INFO = "ℹ️ Информация"
    ADM_REVIEW_WORKS = "👁️ Проверить работы"
    ADM_CONTEST_STATS = "📊 Статистика"
    ADM_SHOW_PARTICIPANTS = "👥 Список участников"
    ADM_SHOW_JUDGES = "⚖️ Список судей"
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
    USER_MAIN_MENU = "user_main_menu"
    # Меню гайдов
    USER_FIND_GUIDE = "user_find_guide"
    # Меню конкурсов
    USER_CONTEST_INFO = "user_contest_info"
    USER_CONTEST_SEND = "user_contest_send"
    USER_CONTEST_JUDGE = "user_contest_judge"
    # Меню новостей
    USER_NEWS = "user_news"
    USER_NEWS_SEND = "user_news_send"
    USER_NEWS_NEWS = "user_news_news"
    USER_NEWS_CODE_DREAM = "user_news_code_dream"
    USER_NEWS_CODE_DLC = "user_news_code_dlc"
    USER_NEWS_POCKET = "user_news_pocket"
    USER_NEWS_DESIGN = "user_news_design"
    # Администраторские
    # Главное меню
    ADM_CONTEST = "adm_contest"
    ADM_TURNIP = "adm_turnip"
    ADM_ADD_GUIDE = "adm_add_guide"
    ADM_BLOCK = "adm_show_blocked_users"
    ADM_MAIN_MENU = "adm_main_menu"
    ADM_USERS = "adm_users"
    # Меню конкурсов
    ADM_CONTEST_INFO = "adm_contest_info"
    ADM_CONTEST_CURRENT = "adm_contest_current"
    ADM_CONTEST_CREATE = "adm_contest_create"
    ADM_CONTEST_SUBMISSIONS = "adm_contest_submissions"
    ADM_CONTEST_RESET = "adm_consest_reset"
    ADM_REVIEW_WORKS = "adm_review_works"
    ADM_CONTEST_STATS = "adm_stats"
    ADM_SHOW_PARTICIPANTS = "adm_show_participants"
    ADM_SHOW_JUDGES = "adm_show_judges"
    ADM_APPROVE = "adm_approve_"
    ADM_REJECT = "adm_reject_"
    # Меню пользователей
    ADM_USERS_BLOCKED = "adm_users_blocked"
    ADM_USERS_APPROVED = "adm_users_approved"
    ADM_USERS_JUDGES = "adm_users_judges"
    ADM_USERS_STATS = "adm_users_stats"


class ConstantLinks:
    # Сайт
    SITE = "https://acnh.tilda.ws"
    # Конкурсы
    CONTEST_LINK = "https://acnh.tilda.ws/contest#rules"
    # Конкурсы
    NEWS_LINK = "https://acnh.tilda.ws/newspaper"
    # Помощь
    HELP_LINK = "http://acnh.tilda.ws/bot_guide"


class UserState:
    WAITING_CONTEST_PHOTOS = "waiting_contest_photos"
    WAITING_CONTEST_TEXT = "waiting_contest_text"
    WAITING_CONTEST_PREVIEW = "waiting_contest_preview"

    WAITING_ADMIN_CONTENT = "waiting_admin_content"
    WAITING_ADMIN_CONTENT_PHOTO = "waiting_admin_content_photo"
    
    WAITING_NEWS_SCREENSHOTS = 'waiting_news_screens'
    WAITING_NEWS_DESCRIPTION = 'waiting_news_desc'
    WAITING_NEWS_SPEAKER = 'waiting_news_speaker'
    WAITING_NEWS_ISLAND = 'waiting_news_island'
    
    WAITING_CODE_VALUE = 'waiting_code_value'
    WAITING_CODE_SCREENSHOTS = 'waiting_code_screens'
    WAITING_CODE_SPEAKER = 'waiting_code_speaker'
    WAITING_CODE_ISLAND = 'waiting_code_island'
    
    WAITING_POCKET_SCREEN = 'waiting_pocket_screen'

    WAITING_DESIGN_CODE = 'waiting_design_code'
    WAITING_DESIGN_DESIGN_SCREEN = 'waiting_design_design_screen'
    WAITING_DESIGN_GAME_SCREENS = 'waiting_design_game_screens'
    
    WAITING_GUIDE_SEARCH = 'waiting_guide_search'
    ADMIN_CREATING_CONTEST = 'admin_creating_contest'
    WAITING_NEWS_TEXT = 'waiting_news_text'
    WAITING_NEWS_PHOTO = 'waiting_news_photo'

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}