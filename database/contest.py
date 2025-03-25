from datetime import datetime
import json
import sqlite3
import os


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
        c = conn.cursor()
        c.execute("UPDATE counters SET value = 0 WHERE name = 'submission'")
        conn.commit()
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
