class ButtonText:
    # Кнопки назад
    BACK = "🔙 Назад"
    MAIN_MENU = "🏠 В главное меню"

    # Пользовательские
    USER_HELP = "🆘 Помощь"
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
    # Меню новостей
    USER_NEWS_NEWS = "📰 Отправить новость в газету"
    USER_NEWS_CODE = "🔢 Отправить код сна или курортного-бюро"
    USER_NEWS_POCKET = "👋 Отправить код дружбы в PocketCamp"
    USER_NEWS_DESIGN = "🎨 Отправить код кастомного дизайна"

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
    # Меню новостей
    USER_NEWS_NEWS = "user_news_news"
    USER_NEWS_CODE = "user_news_code"
    USER_NEWS_POCKET = "user_news_pocket"
    USER_NEWS_DESIGN = "user_news_design"
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
    
    WAITING_POCKET_SCREEN_1 = 'waiting_pocket_screen_1'
    WAITING_POCKET_SCREEN_2 = 'waiting_pocket_screen_2'

    WAITING_DESIGN_CODE = 'waiting_design_code'
    WAITING_DESIGN_DESIGN_SCREEN = 'waiting_design_design_screen'
    WAITING_DESIGN_GAME_SCREENS = 'waiting_design_game_screens'
