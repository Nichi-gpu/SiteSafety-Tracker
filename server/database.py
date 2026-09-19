import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'sitesafety.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT    NOT NULL DEFAULT '',
            email           TEXT    NOT NULL UNIQUE,
            password        TEXT    NOT NULL,
            role            TEXT    NOT NULL DEFAULT 'staff' CHECK(role IN ('staff','manager')),
            company         TEXT    NOT NULL DEFAULT '',
            signup_time     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            last_login_time TEXT    DEFAULT NULL,
            login_count     INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS login_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            username        TEXT    DEFAULT '',
            email           TEXT    DEFAULT '',
            role            TEXT    DEFAULT '',
            action          TEXT    NOT NULL, -- 'LOGIN', 'SIGNUP', 'FAILED_LOGIN', 'LOGOUT'
            status          TEXT    NOT NULL DEFAULT 'SUCCESS', -- 'SUCCESS' or 'FAILED'
            timestamp       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            ip_address      TEXT    DEFAULT '',
            user_agent      TEXT    DEFAULT '',
            details         TEXT    DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS hazards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket      TEXT    NOT NULL UNIQUE,
            location    TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            time        TEXT    NOT NULL,
            urgency     TEXT    NOT NULL DEFAULT 'Medium',
            status      TEXT    NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Resolved')),
            cause       TEXT    DEFAULT '',
            photo       TEXT    DEFAULT '',
            reporter_name     TEXT DEFAULT '',
            reporter_position TEXT DEFAULT '',
            reporter_phone    TEXT DEFAULT '',
            reporter_dept     TEXT DEFAULT '',
            resolved_date     TEXT DEFAULT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS inspections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            location    TEXT    NOT NULL,
            inspector   TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            time        TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'Scheduled',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            time_label  TEXT    NOT NULL DEFAULT 'Just now',
            unread      INTEGER NOT NULL DEFAULT 1,
            user_id     INTEGER DEFAULT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            position    TEXT    NOT NULL,
            phone       TEXT    NOT NULL,
            email       TEXT    DEFAULT '',
            department  TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'Active',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS password_resets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    NOT NULL,
            code        TEXT    NOT NULL,
            expires_at  TEXT    NOT NULL,
            used        INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        ''')

        # Auto-migrate any existing users table columns if missing
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'username' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT NOT NULL DEFAULT ''")
        if 'signup_time' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN signup_time TEXT NOT NULL DEFAULT ''")
        if 'last_login_time' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN last_login_time TEXT DEFAULT NULL")
        if 'login_count' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0")

        # Auto-migrate contacts table if missing email or created_at
        contact_cols = [r['name'] for r in conn.execute("PRAGMA table_info(contacts)").fetchall()]
        if 'email' not in contact_cols:
            conn.execute("ALTER TABLE contacts ADD COLUMN email TEXT DEFAULT ''")
        if 'created_at' not in contact_cols:
            conn.execute("ALTER TABLE contacts ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))")

    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database schema initialized with users, login_logs, hazards, inspections, notifications, contacts.")
