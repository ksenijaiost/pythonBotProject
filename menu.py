import telebot
from telebot import types

from constants import ButtonText


class Menu:
    @staticmethod
    def back_menu():
        back_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        menu_button1 = types.KeyboardButton(ButtonText.BACK)
        menu_button2 = types.KeyboardButton(ButtonText.MAIN_MENU)
        back_menu.add(menu_button1, menu_button2)
        return back_menu

    @staticmethod
    def user_menu():
        user_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        menu_button1 = types.KeyboardButton(ButtonText.USER_GUIDES)
        menu_button2 = types.KeyboardButton(ButtonText.USER_CONTEST)
        user_menu.add(menu_button1, menu_button2)
        return user_menu

    @staticmethod
    def guides_menu():
        guides_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        guides_button1 = types.KeyboardButton(ButtonText.USER_GUIDE_SITE)
        guides_button2 = types.KeyboardButton(ButtonText.USER_FIND_GUIDE)
        guides_button3 = types.KeyboardButton(ButtonText.MAIN_MENU)
        guides_menu.add(guides_button1, guides_button2, guides_button3)
        return guides_menu

    @staticmethod
    def contests_menu():
        contests_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        contests_button1 = types.KeyboardButton(ButtonText.USER_CONTEST_INFO)
        contests_button2 = types.KeyboardButton(ButtonText.USER_CONTEST_SEND)
        contests_button3 = types.KeyboardButton(ButtonText.USER_CONTEST_JUDGE)
        contests_button4 = types.KeyboardButton(ButtonText.MAIN_MENU)
        contests_menu.add(contests_button1, contests_button2, contests_button3, contests_button4)
        return contests_menu

    @staticmethod
    def adm_menu():
        adm_menu = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        adm_button1 = types.KeyboardButton(ButtonText.ADM_CONTEST)
        adm_menu.add(adm_button1)
        return adm_menu

    @staticmethod
    def guide_link_keyboard():
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(
            text="Открыть сайт с гайдами",
            url="https://acnh.tilda.ws"
        )
        button2 = types.InlineKeyboardButton(
            text="В главное меню",
            callback_data="back_to_user_menu"
        )
        keyboard.add(button1, button2)
        return keyboard
