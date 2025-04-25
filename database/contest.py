from datetime import datetime
import json
import sqlite3
import os
from threading import Lock
import time

from menu.constants import UserState

class ContestManager:
    def _init_db():
        """Инициализация БД"""
        if not os.path.exists("database"):
            os.makedirs("database")

        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()

        # Таблица для инфо о конкурсе
        c.execute(
            """CREATE TABLE IF NOT EXISTS contests
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme TEXT NOT NULL,
                    description TEXT NOT NULL,
                    contest_date TEXT NOT NULL,
                    end_date_of_admission TEXT NOT NULL)"""
        )

        # Таблица для работ
        c.execute(
            """CREATE TABLE IF NOT EXISTS submissions
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    photos TEXT NOT NULL,
                    caption TEXT,
                    status TEXT DEFAULT 'pending',
                    reason TEXT,
                    submission_number INTEGER,
                    timestamp DATETIME)"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS approved_submissions (
                user_id INTEGER NOT NULL,
                submission_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, submission_id)
            )"""
        )

        # Таблица для судей
        c.execute(
            """CREATE TABLE IF NOT EXISTS judges
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL)"""
        )

        # Таблица для счетчиков
        c.execute(
            """CREATE TABLE IF NOT EXISTS counters
                    (name TEXT PRIMARY KEY,
                    value INTEGER)"""
        )
        # Инициализация счетчика
        c.execute("INSERT OR IGNORE INTO counters VALUES ('submission', 0)")

        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id)"
        )

        conn.commit()
        conn.close()

    _init_db()

    @staticmethod
    def update_contest(theme, description, contest_date, end_date_of_admission):
        ContestManager._init_db()
        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()

        c.execute("DELETE FROM contests")
        c.execute(
            """INSERT INTO contests 
                    (theme, description, contest_date, end_date_of_admission)
                    VALUES (?, ?, ?, ?)""",
            (theme, description, contest_date, end_date_of_admission),
        )

        conn.commit()
        conn.close()

    @staticmethod
    def get_current_contest():
        ContestManager._init_db()
        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()

        c.execute("SELECT * FROM contests ORDER BY id DESC LIMIT 1")
        contest = c.fetchone()
        conn.close()

        return contest


class SubmissionManager:
    @staticmethod
    def create_submission(user_id, username, full_name, photos, caption):

        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute(
                """INSERT INTO submissions 
                    (user_id, username, full_name, photos, caption, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, username, full_name, json.dumps(photos), caption, datetime.now().isoformat()),
            )
            submission_id = c.lastrowid
            conn.commit()
            return submission_id
        finally:
            conn.close()

    @staticmethod
    def get_pending_submissions():
        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()
        c.execute("SELECT id, user_id FROM submissions WHERE status = 'pending'")
        result = c.fetchall()
        conn.close()
        return result

    @staticmethod
    def update_submission(submission_id, status, reason=None):
        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()
        c.execute(
            """UPDATE submissions 
                    SET status = ?, reason = ?
                    WHERE id = ?""",
            (status, reason, submission_id),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def reset_counter():
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()

            # Обнуляем счетчик
            c.execute("UPDATE counters SET value = 0 WHERE name = 'submission'")

            # Очищаем все заявки
            c.execute("DELETE FROM submissions")

            # Очищаем подтвержденные работы
            c.execute("DELETE FROM approved_submissions")

            # Очищаем список суудей
            c.execute("DELETE FROM judges")

            # Сбрасываем автоинкремент для чистого старта
            c.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('submissions', 'approved_submissions', 'judges')"
            )

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_current_number():
        """Возвращает текущее количество участников"""
        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()
        c.execute("SELECT value FROM counters WHERE name = 'submission'")
        result = c.fetchone()[0]
        conn.close()
        return result

    @staticmethod
    def approve_submission(submission_id):
        conn = sqlite3.connect("database/contests.db")
        try:
            with conn:  # Автоматический commit/rollback
                c = conn.cursor()
                # Получаем и увеличиваем счетчик ТОЛЬКО для подтвержденных работ
                c.execute(
                    "UPDATE counters SET value = value + 1 WHERE name = 'submission'"
                )
                c.execute("SELECT value FROM counters WHERE name = 'submission'")
                number = c.fetchone()[0]

                c.execute(
                    """UPDATE submissions 
                            SET status = 'approved', submission_number = ?
                            WHERE id = ?""",
                    (number, submission_id),
                )

                c.execute(
                    """
                    INSERT INTO approved_submissions (user_id, submission_id) 
                    VALUES ((SELECT user_id FROM submissions WHERE id = ?), ?)
                """,
                    (submission_id, submission_id),
                )
            return number
        finally:
            conn.close()

    @staticmethod
    def rollback_submission(submission_id):
        conn = sqlite3.connect("database/contests.db")
        c = conn.cursor()

        try:
            c.execute(
                """UPDATE submissions 
                        SET status = 'pending', 
                            submission_number = NULL 
                        WHERE id = ?""",
                (submission_id,),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def is_judge(user_id):
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("SELECT 1 FROM judges WHERE user_id = ?", (user_id,))
            return c.fetchone() is not None
        finally:
            conn.close()

    @staticmethod
    def add_judge(user_id, username, full_name):
        if SubmissionManager.is_judge(user_id):
            return False
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute(
                """INSERT INTO judges 
                    (user_id, username, full_name)
                    VALUES (?, ?, ?)""",
                (user_id, username, full_name),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete_judge(user_id):
        if not SubmissionManager.is_judge(user_id):
            return False
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("DELETE FROM judges WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_pending_count():
        """Возвращает количество работ на модерации"""
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'pending'")
            return c.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_approved_count():
        """Возвращает количество одобренных работ"""
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'approved'")
            return c.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_rejected_count():
        """Возвращает количество отвергнутых работ"""
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'rejected'")
            return c.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_judges_count():
        """Возвращает количество подавших заявку на судейство"""
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM judges")
            return c.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_all_submissions_with_info():
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute(
                """SELECT 
                    full_name, 
                    username, 
                    status, 
                    submission_number 
                   FROM submissions"""
            )
            return c.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_all_judges_with_info():
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute(
                """SELECT 
                    full_name, 
                    username 
                   FROM judges"""
            )
            return c.fetchall()
        finally:
            conn.close()


class ContestSubmission:
    def __init__(self):
        self.photos = []  # Список словарей {"file_id": str, "unique_id": str}
        self.caption = ""  # Подпись к работе
        self.media_group_id = None  # ID медиагруппы (для альбомов)
        self.submission_time = time.time()  # Время начала отправки
        self.status = (
            UserState.WAITING_CONTEST_PHOTOS
        )  # collecting_photos → waiting_text → preview
        self.send_by_bot = None  # True/False
        self.last_media_time = time.time()  # Время последнего фото в группе
        self.group_check_timer = None  # Таймер проверки завершения группы
        self.progress_message_id = None  # ID сообщения с прогресс-баром
        self.last_activity = time.time()  # Добавляем недостающий атрибут

    def cancel_timer(self):
        if self.group_check_timer:
            self.group_check_timer.cancel()

    # Добавим метод для обновления времени активности
    def update_activity(self):
        self.last_activity = time.time()
        

class SubmissionStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()
        self.timers = {}
    
    def update_activity(self):
        self.last_activity = time.time()

    def add(self, user_id, submission):
        with self.lock:
            if not hasattr(submission, 'update_activity'):
                raise TypeError("Invalid submission type")
            self.data[user_id] = submission
            # Используем метод обновления активности
            submission.update_activity()
            self.timers[user_id] = submission.last_activity  # Используем last_activity из Submission
    
    # Добавляем новые методы для работы с прогрессом
    def update_progress_message(self, user_id, message_id):
        with self.lock:
            if user_id in self.data:
                self.data[user_id].progress_message_id = message_id

    def update_last_activity(self, user_id):
        with self.lock:
            if user_id in self.data:
                self.data[user_id].last_activity = time.time()
                self.timers[user_id] = self.data[user_id].last_activity

    def get(self, user_id):
        with self.lock:
            return self.data.get(user_id)

    def exists(self, user_id):
        with self.lock:
            return user_id in self.data

    def remove(self, user_id):
        with self.lock:
            if user_id in self.data:
                del self.data[user_id]
                if user_id in self.timers:
                    del self.timers[user_id]

    def get_all_users(self):
        with self.lock:
            return list(self.data.keys())

    def clear(self):
        with self.lock:
            self.data.clear()
            self.timers.clear()


user_submissions = SubmissionStorage()


def get_submission(submission_id):
    """Получение данных о заявке по ID"""
    conn = sqlite3.connect("database/contests.db")
    c = conn.cursor()

    try:
        c.execute(
            """SELECT * FROM submissions 
                   WHERE id = ?""",
            (submission_id,),
        )
        result = c.fetchone()

        if not result:
            raise ValueError(f"Заявка {submission_id} не найдена")

        # Десериализуем JSON-строку в список словарей
        photos = json.loads(result[4]) if result[4] else []

        return {
            "id": result[0],
            "user_id": result[1],
            "username": result[2],
            "full_name": result[3],
            "photos": photos,
            "caption": result[5],
            "status": result[6],
            "reason": result[7],
            "submission_number": result[8],
            "timestamp": result[9],
        }
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        return {"photos": []}  # Возвращаем пустой список при ошибке
    except Exception as e:
        raise e
    finally:
        conn.close()


def is_user_approved(user_id):
    conn = sqlite3.connect("database/contests.db")
    cursor = conn.execute(
        """
        SELECT COUNT(*) FROM approved_submissions WHERE user_id = ?
        """,
        (user_id,),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def is_user_judge(user_id):
    conn = sqlite3.connect("database/contests.db")
    cursor = conn.execute(
        """
        SELECT COUNT(*) FROM judges WHERE user_id = ?
        """,
        (user_id,),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


class UserContentStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()
        self.defaults = {
            "content": {
                "type": "content",
                "photos": [],
                "text": None,
                "counter_msg_id": None,
            },
            "news": {
                "type": "news",
                "photos": [],
                "description": None,
                "speaker": None,
                "island": None,
                "progress_message_id": None,
            },
            "code": {
                "type": "code",
                "code": None,
                "photos": [],
                "speaker": None,
                "island": None,
                "progress_message_id": None,
            },
            "pocket": {"type": "pocket", "photos": [], "media_group_id": None},
            "design": {
                "type": "design",
                "code": None,
                "design_screen": [],
                "game_screens": [],
                "progress_message_id": None,
            },
        }

    def init_content(self, user_id, content_type="content"):
        self.data[user_id] = self.defaults.get(content_type, {}).copy()

    def init_news(self, user_id, content_type="news"):
        self.data[user_id] = self.defaults.get(content_type, {}).copy()

    def init_code(self, user_id, content_type="code"):
        self.data[user_id] = self.defaults.get(content_type, {}).copy()

    def init_pocket(self, user_id, content_type="pocket"):
        self.data[user_id] = self.defaults.get(content_type, {}).copy()

    def init_design(self, user_id, content_type="design"):
        self.data[user_id] = self.defaults.get(content_type, {}).copy()

    def update_counter_message(self, user_id, message_id):
        if user_id in self.data:
            self.data[user_id]["counter_msg_id"] = message_id

    def add_photo(self, user_id, photo_id):
        with self.lock:
            if user_id in self.data:
                self.data[user_id]["photos"].append(photo_id)

    def set_text(self, user_id, text):
        with self.lock:
            if user_id in self.data:
                self.data[user_id]["text"] = text

    def get_data(self, user_id, content_type):
        with self.lock:
            if user_id not in self.data:
                self.init_content(user_id, content_type)
            return self.data[user_id]

    def update_data(self, user_id, new_data):
        with self.lock:
            self.data[user_id]=new_data

    def clear(self, user_id):
        with self.lock:
            if user_id in self.data:
                del self.data[user_id]


user_content_storage = UserContentStorage()