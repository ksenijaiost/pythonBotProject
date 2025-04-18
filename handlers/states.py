from telebot.handler_backends import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_content = State()
    waiting_content_photo = State()

class ContestStates(StatesGroup):
    collecting_photos = State()
    waiting_text = State()


class NewsStates(StatesGroup):
    waiting_screenshots = State()
    waiting_description = State()
    waiting_speaker = State()
    waiting_island = State()


class CodeStates(StatesGroup):
    waiting_value = State()
    waiting_screenshots = State()
    waiting_speaker = State()
    waiting_island = State()


class PocketStates(StatesGroup):
    waiting_screen_1 = State()
    waiting_screen_2 = State()


class DesignStates(StatesGroup):
    waiting_code = State()
    waiting_design_screen = State()
    waiting_game_screens = State()


# Объединяем все состояния в одном пространстве имен
class UserState:
    admin = AdminStates
    contest = ContestStates
    news = NewsStates
    code = CodeStates
    pocket = PocketStates
    design = DesignStates
