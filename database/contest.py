from datetime import datetime
import json
import sqlite3
import os
from threading import Lock
import time


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
    def create_submission(user_id, photos, caption):

        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute(
                """INSERT INTO submissions 
                        (user_id, photos, caption, status, timestamp)
                        VALUES (?, ?, ?, 'pending', ?)""",
                (user_id, json.dumps(photos), caption, datetime.now()),
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

            # Сбрасываем автоинкремент для чистого старта
            c.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('submissions', 'approved_submissions')"
            )

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_current_number():
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
        conn = sqlite3.connect("database/contests.db")
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'rejected'")
            return c.fetchone()[0]
        finally:
            conn.close()


class SubmissionStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()
        self.timers = {}

    def add(self, user_id, submission):
        with self.lock:
            self.data[user_id] = submission
            self.timers[user_id] = time.time()

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

        return {
            "id": result[0],
            "user_id": result[1],
            "photos": json.loads(result[2]),
            "caption": result[3],
            "status": result[4],
            "reason": result[5],
            "submission_number": result[6],
            "timestamp": result[7],
        }

    except Exception as e:
        raise e
    finally:
        conn.close()


def is_user_approved(user_id):  # Убрать self
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


class UserContentStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()

    def init_content(self, user_id, target_chat):
        with self.lock:
            self.data[user_id] = {
                "target_chat": target_chat,
                "photos": [],
                "text": None,
            }

    def add_photo(self, user_id, photo_id):
        with self.lock:
            if user_id in self.data:
                self.data[user_id]["photos"].append(photo_id)

    def set_text(self, user_id, text):
        with self.lock:
            if user_id in self.data:
                self.data[user_id]["text"] = text

    def get_data(self, user_id):
        with self.lock:
            return self.data.get(user_id)

    def init_news(self, user_id):
        self.data[user_id] = {
            "type": "news",
            "photos": [],
            "processed": False,
            "description": None,
            "speaker": None,
            "island": None,
            "description_requested": False,
            "unique_ids": set(),
        }

    def init_code(self, user_id):
        self.data[user_id] = {
            "type": "code",
            "code": None,
            "photos": [],
            "speaker": None,
            "island": None,
        }

    def init_pocket(self, user_id):
        self.data[user_id] = {"type": "pocket", "photos": []}

    def init_design(self, user_id):
        self.data[user_id] = {
            "type": "design",
            "code": None,
            "design_screen": None,
            "game_screens": [],
        }

    def clear(self, user_id):
        with self.lock:
            if user_id in self.data:
                del self.data[user_id]


user_content_storage = UserContentStorage()
