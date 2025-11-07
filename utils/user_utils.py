#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Общие утилиты для работы с пользователями и сообщениями
"""

import logging
from typing import Optional, Dict, Any, List
import telebot.types as types
from bot_instance import bot


def create_user_info_text(user_id: int) -> str:
    """Создает текст с информацией о пользователе"""
    try:
        user = bot.get_chat(user_id)
        user_info = "\n👤 Отправитель: "
        
        if user.username:
            user_info += f"@{user.username}"
            name_parts = []
            if user.first_name:
                name_parts.append(user.first_name)
            if user.last_name:
                name_parts.append(user.last_name)
            if name_parts:
                user_info += f" ({' '.join(name_parts)})"
        else:
            name_parts = []
            if user.first_name:
                name_parts.append(user.first_name)
            if user.last_name:
                name_parts.append(user.last_name)
            user_info += (
                f"{' '.join(name_parts)} [ID: {user_id}]"
                if name_parts
                else f"[ID: {user_id}]"
            )
        
        return user_info
    except Exception as e:
        logging.error(f"Error creating user info: {e}")
        return f"\n👤 Отправитель: [ID: {user_id}]"


def create_confirmation_markup(user_id: int, action: str = "send") -> types.InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Отправить", callback_data=f"confirm_{action}_{user_id}"),
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{action}_{user_id}"),
    )
    return markup


def create_reply_markup(user_id: int) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для ответа пользователю"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💬 Ответить", callback_data=f"reply_to_{user_id}")
    )
    return markup


def deduplicate_photos(photos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Удаляет дублирующиеся фотографии по unique_id"""
    seen_ids = set()
    unique_photos = []
    for photo in photos:
        if photo.get("unique_id") not in seen_ids:
            seen_ids.add(photo.get("unique_id"))
            unique_photos.append(photo)
    return unique_photos


def format_media_group(photos: List[Dict[str, Any]], caption: str = "", 
                      parse_mode: str = "MarkdownV2") -> List[types.InputMediaPhoto]:
    """Создает медиагруппу из фотографий"""
    if not photos:
        return []
    
    media = []
    for i, photo in enumerate(photos):
        if i == 0 and caption:
            media.append(types.InputMediaPhoto(
                photo["file_id"], 
                caption=caption, 
                parse_mode=parse_mode
            ))
        else:
            media.append(types.InputMediaPhoto(photo["file_id"]))
    
    return media


def send_media_with_preview(target_chat: int, photos: List[Dict[str, Any]], 
                           text: str, user_id: int, chat_name: str) -> None:
    """Отправляет медиа с предварительным просмотром"""
    try:
        user_info = create_user_info_text(user_id)
        full_text = f"{text}{user_info}"
        
        if not photos:
            # Только текст
            markup = create_confirmation_markup(user_id)
            bot.send_message(target_chat, full_text, 
                           parse_mode="MarkdownV2", reply_markup=markup)
        elif len(photos) == 1:
            # Одна фотография
            markup = create_confirmation_markup(user_id)
            bot.send_photo(target_chat, photos[0]["file_id"], 
                         caption=full_text, parse_mode="MarkdownV2", 
                         reply_markup=markup)
        else:
            # Медиагруппа
            media = format_media_group(photos, full_text)
            bot.send_media_group(target_chat, media)
            
            # Отправляем кнопки отдельно
            markup = create_confirmation_markup(user_id)
            bot.send_message(target_chat, "📤 *Предварительный просмотр*", 
                           parse_mode="MarkdownV2", reply_markup=markup)
    except Exception as e:
        logging.error(f"Error sending media with preview: {e}")


def log_user_action(user_id: int, action: str, details: str = "") -> None:
    """Логирует действия пользователя"""
    logger = logging.getLogger(__name__)
    logger.info(f"User {user_id} performed action: {action}. {details}")
