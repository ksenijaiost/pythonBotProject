from telebot import types

from menu.constants import ButtonText, ButtonCallback, ConstantLinks
from menu.links import Links


class Menu:
    @staticmethod
    def back_user_only_main_menu():
        """Пользовательское меню - назад в главное"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        back_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return back_menu

    @staticmethod
    def user_to_admin_or_main_menu():
        """Пользовательское меню - написать админам или назад в главное"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        back_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.USER_TO_ADMIN,
                callback_data=ButtonCallback.USER_TO_ADMIN,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return back_menu

    @staticmethod
    def back_user_contest_menu():
        """Пользовательское меню - назад к конкурсам"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        back_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.BACK, callback_data=ButtonCallback.USER_CONTEST
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return back_menu

    @staticmethod
    def back_user_guide_menu():
        """Пользовательское меню - назад к гайдам"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        back_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.BACK, callback_data=ButtonCallback.USER_GUIDES
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return back_menu

    @staticmethod
    def back_adm_contest_menu():
        """Административное меню - назад к конкурсам"""
        back_menu = types.InlineKeyboardMarkup(row_width=1)
        back_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.BACK, callback_data=ButtonCallback.ADM_CONTEST
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return back_menu

    @staticmethod
    def user_menu():
        """Пользовательское меню - главное"""
        user_menu = types.InlineKeyboardMarkup(row_width=1)
        user_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.USER_GUIDES,
                callback_data=ButtonCallback.USER_GUIDES,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_CONTEST,
                callback_data=ButtonCallback.USER_CONTEST,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_TO_ADMIN,
                callback_data=ButtonCallback.USER_TO_ADMIN,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_TO_NEWS,
                callback_data=ButtonCallback.USER_TO_NEWS,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_TURNIP,
                callback_data=ButtonCallback.USER_TURNIP,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_HEAD_CHAT, url=Links.get_chat_url()
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_CHANEL, url=Links.get_channel_url()
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_CHAT_NINTENDO, url=Links.get_nin_chat_url()
            ),
        )

        return user_menu

    @staticmethod
    def guides_menu():
        """Пользовательское меню гайдов"""
        guides_menu = types.InlineKeyboardMarkup(row_width=1)
        guides_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.USER_GUIDE_SITE, url=ConstantLinks.SITE
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_FIND_GUIDE,
                callback_data=ButtonCallback.USER_FIND_GUIDE,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return guides_menu

    # Меню конкурсов
    @staticmethod
    def contests_menu():
        """Пользовательское меню конкурсов"""
        contests_menu = types.InlineKeyboardMarkup(row_width=1)
        contests_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.USER_CONTEST_INFO,
                callback_data=ButtonCallback.USER_CONTEST_INFO,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_CONTEST_SEND,
                callback_data=ButtonCallback.USER_CONTEST_SEND,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_CONTEST_JUDGE,
                callback_data=ButtonCallback.USER_CONTEST_JUDGE,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return contests_menu

    @staticmethod
    def news_menu():
        """Пользовательское меню отправки новостей"""
        news_menu = types.InlineKeyboardMarkup(row_width=1)
        news_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.USER_NEWS_NEWS,
                callback_data=ButtonCallback.USER_NEWS_NEWS,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_NEWS_CODE_DREAM,
                callback_data=ButtonCallback.USER_NEWS_CODE,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_NEWS_CODE_DLC,
                callback_data=ButtonCallback.USER_NEWS_CODE,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_NEWS_DESIGN,
                callback_data=ButtonCallback.USER_NEWS_DESIGN,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.USER_NEWS_POCKET,
                callback_data=ButtonCallback.USER_NEWS_POCKET,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )
        return news_menu

    # Административное меню
    # Главное меню
    @staticmethod
    def adm_menu():
        """Административное меню"""
        adm_menu = types.InlineKeyboardMarkup(row_width=1)
        adm_menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.ADM_CONTEST, callback_data=ButtonCallback.ADM_CONTEST
            ),
            types.InlineKeyboardButton(
                text=ButtonText.ADM_TURNIP, callback_data=ButtonCallback.ADM_TURNIP
            ),
            types.InlineKeyboardButton(
                text=ButtonText.ADM_ADD_GUIDE,
                callback_data=ButtonCallback.ADM_ADD_GUIDE,
            ),
        )

        return adm_menu

    # Меню конкурсов (адм)
    @staticmethod
    def adm_contests_menu():
        """Административное меню конкурсов"""
        menu = types.InlineKeyboardMarkup()
        menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.ADM_CONTEST_INFO,
                callback_data=ButtonCallback.ADM_CONTEST_INFO,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.ADM_REVIEW_WORKS,
                callback_data=ButtonCallback.ADM_REVIEW_WORKS,
            ),
        )
        menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.ADM_CONTEST_STATS,
                callback_data=ButtonCallback.ADM_CONTEST_STATS,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return menu

    @staticmethod
    def adm_stat_menu():
        menu = types.InlineKeyboardMarkup()
        menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.ADM_SHOW_PARTICIPANTS,
                callback_data=ButtonCallback.ADM_SHOW_PARTICIPANTS,
            ),
            types.InlineKeyboardButton(
                text=ButtonText.ADM_SHOW_JUDGES,
                callback_data=ButtonCallback.ADM_SHOW_JUDGES,
            ),
        )
        menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.ADM_CONTEST_RESET,
                callback_data=ButtonCallback.ADM_CONTEST_RESET,
            ),
        )
        menu.add(
            types.InlineKeyboardButton(
                text=ButtonText.BACK, callback_data=ButtonCallback.ADM_CONTEST
            ),
            types.InlineKeyboardButton(
                text=ButtonText.MAIN_MENU, callback_data=ButtonCallback.MAIN_MENU
            ),
        )

        return menu
