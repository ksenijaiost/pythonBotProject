#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Общие утилиты для обработки медиа и сообщений
"""

import threading
import time
from typing import Dict, List, Any, Optional
import telebot.types as types
from bot_instance import bot
from menu.menu import Menu


class MediaGroupHandler:
    """Обработчик медиагрупп с таймером"""
    
    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
        self.media_groups: Dict[str, Dict[str, Any]] = {}
    
    def add_media(self, message, data: Dict[str, Any], user_id: int) -> bool:
        """Добавляет медиа в группу"""
        mg_id = message.media_group_id
        
        if mg_id in self.media_groups:
            # Группа уже существует
            if message.message_id in self.media_groups[mg_id]["processed"]:
                return False  # Уже обработано
            
            self.media_groups[mg_id]["processed"].add(message.message_id)
            self.media_groups[mg_id]["photos"].append({
                "file_id": message.photo[-1].file_id,
                "unique_id": message.photo[-1].file_unique_id,
                "message_id": message.message_id
            })
            
            # Сбрасываем таймер
            self.media_groups[mg_id]["timer"].cancel()
            self.media_groups[mg_id]["timer"] = threading.Timer(
                self.timeout, self._process_group, [mg_id]
            )
            self.media_groups[mg_id]["timer"].start()
            return True
        
        # Создаем новую группу
        self.media_groups[mg_id] = {
            "photos": [{
                "file_id": message.photo[-1].file_id,
                "unique_id": message.photo[-1].file_unique_id,
                "message_id": message.message_id
            }],
            "processed": {message.message_id},
            "timer": threading.Timer(self.timeout, self._process_group, [mg_id])
        }
        self.media_groups[mg_id]["timer"].start()
        return True
    
    def _process_group(self, mg_id: str):
        """Обрабатывает завершенную медиагруппу"""
        if mg_id not in self.media_groups:
            return
        
        group = self.media_groups[mg_id]
        photos = group["photos"]
        
        # Здесь можно добавить логику обработки
        # Например, сохранение в data или отправка уведомления
        
        # Очищаем группу
        del self.media_groups[mg_id]


def create_progress_bar(current: int, total: int, filled_char: str = "🟪", empty_char: str = "◻️") -> str:
    """Создает прогресс-бар"""
    return filled_char * current + empty_char * (total - current)


def send_progress_message(chat_id: int, message_id: int, current: int, total: int, 
                         text: str = "Обработка фото...") -> Optional[int]:
    """Отправляет сообщение с прогрессом"""
    try:
        progress_bar = create_progress_bar(current, total)
        sent_msg = bot.reply_to(
            bot.get_chat(chat_id).pinned_message or bot.get_chat(chat_id),
            f"{progress_bar}\n{text}\n✅ Фото добавлено, всего: {current}/{total}"
        )
        return sent_msg.message_id
    except Exception:
        return None


def validate_photo_limit(photos: List[Dict], max_photos: int, user_id: int) -> bool:
    """Проверяет лимит фотографий"""
    if len(photos) >= max_photos:
        bot.send_message(user_id, f"❌ Достигнут максимум {max_photos} фото!")
        return False
    return True


def check_duplicate_photo(photos: List[Dict], new_photo_id: str) -> bool:
    """Проверяет дублирование фотографии"""
    existing_ids = {p.get("unique_id") for p in photos if p.get("unique_id")}
    return new_photo_id in existing_ids


def handle_media_group_processing(message, data: Dict[str, Any], user_id: int, 
                                 max_photos: int = 10, progress_text: str = "Обработка фото...") -> bool:
    """Обрабатывает медиагруппу с проверками"""
    try:
        # Проверяем лимит фотографий
        if len(data.get("photos", [])) >= max_photos:
            bot.send_message(user_id, f"❌ Достигнут максимум {max_photos} фото!")
            return False
        
        # Проверяем дублирование
        photo_id = message.photo[-1].file_unique_id
        existing_ids = {p.get("unique_id") for p in data.get("photos", []) if p.get("unique_id")}
        
        if photo_id in existing_ids:
            bot.reply_to(message, "❌ Это фото уже было добавлено!")
            return False
        
        # Добавляем фото
        data.setdefault("photos", []).append({
            "file_id": message.photo[-1].file_id,
            "unique_id": photo_id,
            "message_id": message.message_id
        })
        
        # Отправляем прогресс
        current = len(data["photos"])
        progress_bar = create_progress_bar(current, max_photos)
        
        sent_msg = bot.reply_to(
            message,
            f"{progress_bar}\n{progress_text}\n✅ Фото добавлено, всего: {current}/{max_photos}"
        )
        
        data["progress_message_id"] = sent_msg.message_id
        return True
        
    except Exception as e:
        logging.error(f"Error processing media group: {e}")
        return False


def cleanup_progress_message(chat_id: int, data: Dict[str, Any]) -> None:
    """Удаляет сообщение с прогрессом"""
    if data.get("progress_message_id"):
        try:
            bot.delete_message(chat_id, data["progress_message_id"])
        except Exception:
            pass
        data.pop("progress_message_id", None)
