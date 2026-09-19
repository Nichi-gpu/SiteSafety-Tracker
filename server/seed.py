import sqlite3
import bcrypt
from database import get_db, init_db

def seed():
    print('[*] Seeding SiteSafety database...')
    init_db()
    conn = get_db()
    
    # ── 1. Default Users ────────────────────────────────────
    users = [
        ('manager', 'manager@sitesafety.com', bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), 'manager', 'SiteSafety Corp'),
        ('andrei', 'andrei@sitesafety.com', bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), 'staff', 'SiteSafety Corp'),
        ('admin', 'admin@sitesafety.com', bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), 'manager', 'SiteSafety Global')
    ]
    with conn:
        for u in users:
            existing = conn.execute('SELECT id FROM users WHERE email = ?', (u[1],)).fetchone()
            if existing:
                conn.execute('''
                    UPDATE users SET username = ?, role = ?, company = ? WHERE email = ?
                ''', (u[0], u[3], u[4], u[1]))
            else:
                conn.execute('''
                    INSERT INTO users (username, email, password, role, company, signup_time)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ''', (u[0], u[1], u[2], u[3], u[4]))
    print('  [OK] Users seeded with usernames & timestamps')

    # Seed initial audit log entry
    with conn:
        conn.execute('''
            INSERT INTO login_logs (username, email, role, action, status, timestamp, details)
            VALUES ('system', 'system@sitesafety.com', 'manager', 'SYSTEM_INIT', 'SUCCESS', datetime('now', 'localtime'), 'Database initialized & seeded')
        ''')

    # ── 2. Hazards (Only user-created reports) ─────────────────────
    # Mock hazards removed as requested. Only real reports are stored.

    # ── 3. Inspections ──────────────────────────────────────
    # Existing inspection schedule maintained

    # ── 4. Notifications ────────────────────────────────────
    # Mock notifications removed. Only real system notifications appear.

    # ── 5. Contacts ─────────────────────────────────────────
    # Mock contacts removed. User adds their own contacts.

    conn.close()
    print('[OK] Database successfully initialized with users and clean records!')

if __name__ == '__main__':
    seed()
