"""
Утилиты для работы с MarkdownV2 в Telegram
"""
import re
from typing import Optional


def escape_markdown_v2(text: str) -> str:
    """
    Экранирует специальные символы для MarkdownV2
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    if not text:
        return text
    
    # Символы, которые нужно экранировать в MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    
    # Экранируем каждый символ
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_markdown_v2_with_preserved_formatting(text: str) -> str:
    """
    Форматирует текст для MarkdownV2 с сохранением форматирования
    
    Args:
        text: Исходный текст с MarkdownV2 разметкой
        
    Returns:
        Безопасный текст для MarkdownV2 с сохраненным форматированием
    """
    if not text:
        return ""
    
    # Сначала экранируем все символы
    escaped_text = escape_markdown_v2(text)
    
    # Затем восстанавливаем нужное форматирование
    # Восстанавливаем жирный текст *текст*
    escaped_text = re.sub(r'\\\*([^\\*]+)\\\*', r'*\1*', escaped_text)
    
    # Восстанавливаем курсив _текст_
    escaped_text = re.sub(r'\\_([^\\_]+)\\_', r'_\1_', escaped_text)
    
    # Восстанавливаем моноширинный `текст`
    escaped_text = re.sub(r'\\`([^\\`]+)\\\`', r'`\1`', escaped_text)
    
    return escaped_text


def safe_markdown_v2(text: str, max_length: Optional[int] = None) -> str:
    """
    Безопасно подготавливает текст для MarkdownV2
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина (обрезает если нужно)
        
    Returns:
        Безопасный текст для MarkdownV2
    """
    if not text:
        return ""
    
    # Обрезаем если нужно
    if max_length and len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    # Экранируем
    return escape_markdown_v2(text)


def format_user_info_markdown_v2(user_id: int, username: str, full_name: str) -> str:
    """
    Форматирует информацию о пользователе для MarkdownV2
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя
        full_name: Полное имя
        
    Returns:
        Отформатированная строка
    """
    safe_username = safe_markdown_v2(username) if username else "отсутствует"
    safe_full_name = safe_markdown_v2(full_name) if full_name else "не указано"
    
    return f"👤 *Пользователь:* {safe_full_name}\n🆔 *ID:* `{user_id}`\n📝 *Username:* @{safe_username}"


def format_contest_info_markdown_v2(theme: str, description: str, contest_date: str, end_date: str) -> str:
    """
    Форматирует информацию о конкурсе для MarkdownV2
    
    Args:
        theme: Тема конкурса
        description: Описание
        contest_date: Дата проведения
        end_date: Дата окончания приема работ
        
    Returns:
        Отформатированная строка
    """
    safe_theme = safe_markdown_v2(theme)
    safe_description = safe_markdown_v2(description)
    safe_contest_date = safe_markdown_v2(contest_date)
    safe_end_date = safe_markdown_v2(end_date)
    
    return f"""📋 *Текущие данные конкурса:*

🎯 *Тема:* {safe_theme}
📝 *Описание:* {safe_description}
📅 *Дата проведения:* {safe_contest_date}
⏰ *Окончание приема работ:* {safe_end_date}"""


def format_submission_info_markdown_v2(submission_id: int, user_id: int, username: str, full_name: str, status: str) -> str:
    """
    Форматирует информацию о заявке для MarkdownV2
    
    Args:
        submission_id: ID заявки
        user_id: ID пользователя
        username: Имя пользователя
        full_name: Полное имя
        status: Статус заявки
        
    Returns:
        Отформатированная строка
    """
    safe_username = safe_markdown_v2(username) if username else "отсутствует"
    safe_full_name = safe_markdown_v2(full_name) if full_name else "не указано"
    safe_status = safe_markdown_v2(status)
    
    return f"""📄 *Заявка #{submission_id}*

👤 *Пользователь:* {safe_full_name}
🆔 *ID:* `{user_id}`
📝 *Username:* @{safe_username}
📊 *Статус:* {safe_status}"""


def is_markdown_v2_safe(text: str) -> bool:
    """
    Проверяет, безопасен ли текст для MarkdownV2
    
    Args:
        text: Текст для проверки
        
    Returns:
        True если текст безопасен
    """
    if not text:
        return True
    
    # Проверяем наличие неэкранированных специальных символов
    unsafe_pattern = r'(?<!\\)[_*\[\]()~`>#+\-=|{}.!]'
    return not bool(re.search(unsafe_pattern, text))


def clean_markdown_v2_errors(text: str) -> str:
    """
    Очищает текст от проблемных символов MarkdownV2
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return text
    
    # Заменяем проблемные символы на безопасные аналоги
    replacements = {
        '!': '❗',
        '.': '•',
        '-': '—',
        '|': '│',
        '>': '▶',
        '#': '№',
        '+': '➕',
        '=': '═',
        '{': '❴',
        '}': '❵',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text
