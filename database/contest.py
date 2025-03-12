import sqlite3
import os

class ContestManager:
    @staticmethod
    def _init_db():
        """Инициализация БД"""
        if not os.path.exists('database'):
            os.makedirs('database')
            
        conn = sqlite3.connect('database/contests.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS contests
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      theme TEXT NOT NULL,
                      description TEXT NOT NULL,
                      contest_date TEXT NOT NULL,
                      end_date_of_admission TEXT NOT NULL)''')
        conn.commit()
        conn.close()

    @staticmethod
    def update_contest(theme, description, contest_date, end_date_of_admission):
        ContestManager._init_db()
        conn = sqlite3.connect('database/contests.db')
        c = conn.cursor()
        
        c.execute("DELETE FROM contests")
        c.execute('''INSERT INTO contests 
                    (theme, description, contest_date, end_date_of_admission)
                    VALUES (?, ?, ?, ?)''',
                (theme, description, contest_date, end_date_of_admission))
        
        conn.commit()
        conn.close()

    @staticmethod
    def get_current_contest():
        ContestManager._init_db()
        conn = sqlite3.connect('database/contests.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM contests ORDER BY id DESC LIMIT 1")
        contest = c.fetchone()
        conn.close()
        
        return contest