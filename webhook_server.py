import os
import logging
from flask import Flask, request, jsonify
from bot_instance import bot
import handlers.admin
import handlers.user
import handlers.contest_handlers
import handlers.guide_handlers
import handlers.message_handlers
import handlers.news_handlers
import handlers.common_handlers
import handlers.admin_contest_handlers
import handlers.admin_user_handlers
import database.db_classes
from database.db_classes import user_content_storage
from handlers.envParams import admin_ids
from menu.constants import ButtonCallback
from menu.menu import Menu
from services.user_service import UserService

# Настройка логирования
logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)

app = Flask(__name__)

# Получаем URL вебхука из переменных окружения
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram"""
    try:
        # Получаем обновление от Telegram
        update = request.get_json()
        
        # Обрабатываем обновление через бота
        bot.process_new_updates([update])
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервера"""
    return jsonify({'status': 'healthy', 'bot': 'running'})

@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Установка вебхука"""
    try:
        if not WEBHOOK_URL:
            return jsonify({'status': 'error', 'message': 'WEBHOOK_URL not set'}), 400
        
        # Удаляем старый вебхук
        bot.remove_webhook()
        
        # Устанавливаем новый вебхук
        result = bot.set_webhook(url=WEBHOOK_URL)
        
        return jsonify({'status': 'ok', 'result': result})
    
    except Exception as e:
        logging.error(f"Set webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/remove_webhook', methods=['POST'])
def remove_webhook():
    """Удаление вебхука"""
    try:
        result = bot.remove_webhook()
        return jsonify({'status': 'ok', 'result': result})
    
    except Exception as e:
        logging.error(f"Remove webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook_info', methods=['GET'])
def webhook_info():
    """Информация о текущем вебхуке"""
    try:
        info = bot.get_webhook_info()
        return jsonify({'status': 'ok', 'webhook_info': info})
    
    except Exception as e:
        logging.error(f"Get webhook info error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def start_webhook_server():
    """Запуск вебхук сервера"""
    try:
        # Устанавливаем вебхук при запуске
        if WEBHOOK_URL:
            bot.remove_webhook()
            bot.set_webhook(url=WEBHOOK_URL)
            logging.info(f"Webhook set to: {WEBHOOK_URL}")
        
        # Запускаем Flask сервер
        app.run(
            host=WEBHOOK_HOST,
            port=WEBHOOK_PORT,
            debug=False,
            threaded=True
        )
    
    except Exception as e:
        logging.error(f"Failed to start webhook server: {str(e)}")
        raise

if __name__ == "__main__":
    start_webhook_server()
