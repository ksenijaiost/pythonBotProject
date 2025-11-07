"""
Обработчики гайдов
"""
import logging
from typing import Optional, Dict, Any
import telebot.types as types

from bot_instance import bot
from utils.simple_locks import simple_lock
from utils.markdown_utils import safe_markdown_v2
from handlers.decorator import private_chat_only
from menu.constants import ButtonCallback, UserState
from menu.links import Links

logger = logging.getLogger(__name__)


class GuideHandlers:
    """Класс для обработки гайдов"""
    
    @staticmethod
    def handle_guides_menu(call):
        """Обработка меню гайдов"""
        try:
            text = safe_markdown_v2(
                "📚 *Гайды по Animal Crossing*\n\n"
                "Здесь вы найдете полезные гайды и советы по игре\\.\n\n"
                "Выберите действие:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🌐 Перейти на сайт",
                    url=Links.GUIDES_SITE
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🔍 Поиск гайдов",
                    callback_data=ButtonCallback.USER_FIND_GUIDE
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 В главное меню",
                    callback_data=ButtonCallback.USER_MAIN_MENU
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Guides menu error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при открытии меню гайдов",
                show_alert=True
            )
    
    @staticmethod
    def handle_find_guide(call):
        """Обработка поиска гайдов"""
        try:
            text = safe_markdown_v2(
                "🔍 *Поиск гайдов*\n\n"
                "Введите ключевое слово для поиска гайда\\.\n"
                "Например: \"рыбалка\", \"цветы\", \"мебель\"\\.\n\n"
                "❌ Для отмены отправьте /cancel"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=ButtonCallback.USER_GUIDES
                )
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
            # Устанавливаем состояние ожидания поискового запроса
            bot.set_state(call.from_user.id, UserState.WAITING_GUIDE_SEARCH)
            
        except Exception as e:
            logger.error(f"Find guide error: {e}")
            bot.answer_callback_query(
                call.id,
                "❌ Ошибка при открытии поиска",
                show_alert=True
            )
    
    @staticmethod
    def handle_guide_search(message):
        """Обработка поискового запроса"""
        try:
            user_id = message.from_user.id
            search_query = message.text.strip().lower()
            
            # Здесь должна быть логика поиска в базе данных
            # Пока что возвращаем заглушку
            results = GuideHandlers.search_guides(search_query)
            
            if results:
                text = safe_markdown_v2(
                    f"🔍 *Результаты поиска по запросу: \"{search_query}\"*\n\n"
                    f"Найдено гайдов: {len(results)}\n\n"
                    "📚 *Доступные гайды:*\n"
                )
                
                for i, guide in enumerate(results[:5], 1):  # Показываем первые 5
                    text += f"{i}\\. {guide['title']}\n"
                
                if len(results) > 5:
                    text += f"\n\\.\\.\\. и еще {len(results) - 5} гайдов"
                
                text += "\n\n🌐 *Для просмотра перейдите на сайт:*"
                text += f"\n{Links.GUIDES_SITE}"
                
            else:
                text = safe_markdown_v2(
                    f"🔍 *Поиск по запросу: \"{search_query}\"*\n\n"
                    "😔 К сожалению, по вашему запросу ничего не найдено\\.\n\n"
                    "💡 *Попробуйте:*\n"
                    "• Изменить ключевые слова\n"
                    "• Использовать более общие термины\n"
                    "• Перейти на сайт для просмотра всех гайдов\n\n"
                    f"🌐 *Сайт с гайдами:*\n{Links.GUIDES_SITE}"
                )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🌐 Перейти на сайт",
                    url=Links.GUIDES_SITE
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🔍 Новый поиск",
                    callback_data=ButtonCallback.USER_FIND_GUIDE
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🔙 В главное меню",
                    callback_data=ButtonCallback.USER_MAIN_MENU
                )
            )
            
            bot.send_message(
                user_id,
                text,
                parse_mode="MarkdownV2",
                reply_markup=markup
            )
            
            # Сбрасываем состояние
            bot.delete_state(user_id)
            
        except Exception as e:
            logger.error(f"Guide search error: {e}")
            bot.reply_to(
                message,
                "❌ Ошибка при поиске гайдов. Попробуйте еще раз."
            )
    
    @staticmethod
    def search_guides(query: str) -> list:
        """
        Поиск гайдов по запросу
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список найденных гайдов
        """
        # Заглушка для поиска гайдов
        # В реальном проекте здесь должен быть поиск в базе данных
        
        mock_guides = [
            {"title": "Рыбалка в Animal Crossing", "keywords": ["рыбалка", "рыба", "удочка"]},
            {"title": "Выращивание цветов", "keywords": ["цветы", "сад", "растения"]},
            {"title": "Создание мебели", "keywords": ["мебель", "крафт", "создание"]},
            {"title": "Торговля с NPC", "keywords": ["торговля", "npc", "продажа"]},
            {"title": "Дизайн острова", "keywords": ["дизайн", "остров", "украшение"]},
        ]
        
        # Простой поиск по ключевым словам
        results = []
        for guide in mock_guides:
            if any(keyword in query for keyword in guide["keywords"]):
                results.append(guide)
        
        return results


# Регистрация обработчиков
@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_GUIDES)
@simple_lock()
@private_chat_only(bot)
def handle_user_guides(call):
    """Обработчик меню гайдов"""
    GuideHandlers.handle_guides_menu(call)


@bot.callback_query_handler(func=lambda call: call.data == ButtonCallback.USER_FIND_GUIDE)
@simple_lock()
@private_chat_only(bot)
def handle_user_find_guide(call):
    """Обработчик поиска гайдов"""
    GuideHandlers.handle_find_guide(call)


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bot.get_state(m.from_user.id) == UserState.WAITING_GUIDE_SEARCH
)
@simple_lock()
def handle_guide_search_message(message):
    """Обработчик поискового запроса гайдов"""
    GuideHandlers.handle_guide_search(message)
