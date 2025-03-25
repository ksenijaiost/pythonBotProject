from telebot import types

from menu.constants import ButtonText, ButtonCallback, ConstantLinks
from menu.links import Links


class Menu:
    @staticmethod
    def back_user_contest_menu():
        """Пользовательское меню - назад к конкурсам"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        menu_button1 = types.InlineKeyboardButton(
            text=ButtonText.BACK,
            callback_data=ButtonCallback.USER_CONTEST
        )
        menu_button2 = types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU,
            callback_data=ButtonCallback.MAIN_MENU
        )
        back_menu.add(menu_button1, menu_button2)
        return back_menu

    @staticmethod
    def back_user_guide_menu():
        """Пользовательское меню - назад к гайдам"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        menu_button1 = types.InlineKeyboardButton(
            text=ButtonText.BACK,
            callback_data=ButtonCallback.USER_GUIDE
        )
        menu_button2 = types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU,
            callback_data=ButtonCallback.MAIN_MENU
        )
        back_menu.add(menu_button1, menu_button2)
        return back_menu

    @staticmethod
    def back_adm_contest_menu():
        """Административное меню - назад к конкурсам"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        menu_button1 = types.InlineKeyboardButton(
            text=ButtonText.BACK,
            callback_data=ButtonCallback.ADM_CONTEST
        )
        menu_button2 = types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU,
            callback_data=ButtonCallback.MAIN_MENU
        )
        back_menu.add(menu_button1, menu_button2)
        return back_menu

    @staticmethod
    def user_menu():
        """Пользовательское меню - главное"""
        user_menu = types.InlineKeyboardMarkup(row_width=1)
        menu_button1 = types.InlineKeyboardButton(
            text=ButtonText.USER_GUIDES,
            callback_data=ButtonCallback.USER_GUIDES,
        )
        menu_button2 = types.InlineKeyboardButton(
            text=ButtonText.USER_CONTEST,
            callback_data=ButtonCallback.USER_CONTEST,
        )
        menu_button3 = types.InlineKeyboardButton(
            text=ButtonText.USER_TO_ADMIN,
            callback_data=ButtonCallback.USER_TO_ADMIN,
        )
        menu_button4 = types.InlineKeyboardButton(
            text=ButtonText.USER_TO_NEWS,
            callback_data=ButtonCallback.USER_TO_NEWS,
        )
        menu_button5 = types.InlineKeyboardButton(
            text=ButtonText.USER_TURNIP,
            callback_data=ButtonCallback.USER_TURNIP,
        )
        menu_button6 = types.InlineKeyboardButton(
            text=ButtonText.USER_HEAD_CHAT,
            url=Links.get_chat_url()
        )
        menu_button7 = types.InlineKeyboardButton(
            text=ButtonText.USER_CHANEL,
            url=Links.get_channel_url()
        )
        menu_button8 = types.InlineKeyboardButton(
            text=ButtonText.USER_CHAT_NINTENDO,
            url=Links.get_nin_chat_url()
        )
        user_menu.add(menu_button1, menu_button2)
        user_menu.add(menu_button3, menu_button4, menu_button5)
        user_menu.add(menu_button6, menu_button7, menu_button8)
        return user_menu

    @staticmethod
    def guides_menu():
        """Пользовательское меню гайдов"""
        guides_menu = types.InlineKeyboardMarkup(row_width=1)
        guides_button1 = types.InlineKeyboardButton(
            text=ButtonText.USER_GUIDE_SITE,
            url=ConstantLinks.SITE
        )
        guides_button2 = types.InlineKeyboardButton(
            text=ButtonText.USER_FIND_GUIDE,
            callback_data=ButtonCallback.USER_FIND_GUIDE,
        )
        guides_button3 = types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU,
            callback_data=ButtonCallback.MAIN_MENU
        )
        guides_menu.add(guides_button1, guides_button2, guides_button3)
        return guides_menu

    # Меню конкурсов
    @staticmethod
    def contests_menu():
        """Пользовательское меню конкурсов"""
        contests_menu = types.InlineKeyboardMarkup(row_width=1)
        contests_button1 = types.InlineKeyboardButton(
            text=ButtonText.USER_CONTEST_INFO,
            callback_data=ButtonCallback.USER_CONTEST_INFO
        )
        contests_button2 = types.InlineKeyboardButton(
            text=ButtonText.USER_CONTEST_SEND,
            callback_data=ButtonCallback.USER_CONTEST_SEND
        )
        contests_button3 = types.InlineKeyboardButton(
            text=ButtonText.USER_CONTEST_JUDGE,
            callback_data=ButtonCallback.USER_CONTEST_JUDGE
        )
        contests_button4 = types.InlineKeyboardButton(
            text=ButtonText.MAIN_MENU,
            callback_data=ButtonCallback.MAIN_MENU
        )
        contests_menu.add(contests_button1, contests_button2, contests_button3, contests_button4)
        return contests_menu

    # Административное меню
    # Главное меню
    @staticmethod
    def adm_menu():
        """Административное меню"""
        adm_menu = types.InlineKeyboardMarkup(row_width=1)
        adm_button1 = types.InlineKeyboardButton(
            text=ButtonText.ADM_CONTEST,
            callback_data=ButtonCallback.ADM_CONTEST
        )
        adm_menu.add(adm_button1)
        return adm_menu

    # Меню конкурсов (адм)
    @staticmethod
    def adm_contests_menu():
        menu = types.InlineKeyboardMarkup()
        menu.add(
            types.InlineKeyboardButton(ButtonText.ADM_CONTEST_INFO, callback_data=ButtonCallback.ADM_CONTEST_INFO),
            types.InlineKeyboardButton(ButtonText.ADM_REVIEW_WORKS, callback_data=ButtonCallback.ADM_REVIEW_WORKS)
        )
        menu.add(
            types.InlineKeyboardButton(ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU)
        )
        return menu
