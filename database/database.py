import sqlite3


def init_db():
    conn = sqlite3.connect('database/contests.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS contests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  theme TEXT NOT NULL,
                  description TEXT NOT NULL,
                  start_date TEXT NOT NULL,
                  end_date TEXT NOT NULL)''')
    conn.commit()
    conn.close()


init_db()
