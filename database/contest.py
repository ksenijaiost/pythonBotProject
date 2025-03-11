import sqlite3


class ContestManager:
    @staticmethod
    def update_contest(theme, description, start_date, end_date):
        conn = sqlite3.connect('contests.db')
        c = conn.cursor()

        # Очищаем старые данные (если нужно хранить историю - замените на INSERT)
        c.execute("DELETE FROM contests")

        c.execute("INSERT INTO contests (theme, description, start_date, end_date) VALUES (?, ?, ?, ?)",
                  (theme, description, start_date, end_date))
        conn.commit()
        conn.close()

    @staticmethod
    def get_current_contest():
        conn = sqlite3.connect('contests.db')
        c = conn.cursor()

        c.execute("SELECT * FROM contests ORDER BY id DESC LIMIT 1")
        contest = c.fetchone()
        conn.close()

        return contest  # (id, theme, description, start_date, end_date)
