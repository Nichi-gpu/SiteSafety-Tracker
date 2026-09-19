from flask import Flask, request, jsonify, session, send_from_directory, Response, render_template_string
from flask_cors import CORS
import bcrypt
import os
import sys
import io
import csv
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import get_db, init_db

# Ensure UTF-8 output in Windows PowerShell/cmd
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Auto-load server/.env or .env file if present
for env_path in [os.path.join(os.path.dirname(__file__), '.env'), os.path.join(os.path.dirname(__file__), '..', '.env')]:
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PUBLIC_DIR = os.path.join(WORKSPACE_ROOT, 'public')

app = Flask(__name__, static_folder=WORKSPACE_ROOT, static_url_path='')
app.secret_key = 'sitesafety-tracker-secret-key-2026'
CORS(app, supports_credentials=True)

# Ensure DB initialized & seeded
init_db()
try:
    _conn = get_db()
    _user_count = _conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    _conn.close()
    if _user_count == 0:
        print('[*] Users table empty. Initializing and seeding default data...')
        import seed
        seed.seed()
except Exception as _e:
    print(f'[*] DB seed check: {_e}')

# ── Static Files & Fallback ──────────────────────────────
@app.route('/')
def index():
    if os.path.exists(os.path.join(WORKSPACE_ROOT, 'index.html')):
        return send_from_directory(WORKSPACE_ROOT, 'index.html')
    return send_from_directory(PUBLIC_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Check project root first (where active development happens)
    root_path = os.path.join(WORKSPACE_ROOT, path)
    if os.path.exists(root_path) and os.path.isfile(root_path):
        return send_from_directory(WORKSPACE_ROOT, path)
    
    # Check public folder second
    public_path = os.path.join(PUBLIC_DIR, path)
    if os.path.exists(public_path) and os.path.isfile(public_path):
        return send_from_directory(PUBLIC_DIR, path)
        
    # If looking for an HTML page without extension
    if '.' not in path:
        html_root = os.path.join(WORKSPACE_ROOT, f"{path}.html")
        if os.path.exists(html_root):
            return send_from_directory(WORKSPACE_ROOT, f"{path}.html")
        html_pub = os.path.join(PUBLIC_DIR, f"{path}.html")
        if os.path.exists(html_pub):
            return send_from_directory(PUBLIC_DIR, f"{path}.html")

    return "File not found", 404

# ── Health ───────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

# ── Auth Routes ──────────────────────────────────────────
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json or {}
    company = data.get('company', '').strip()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = 'manager' if data.get('role') == 'manager' else 'staff'
    ip = request.remote_addr or ''
    ua = request.headers.get('User-Agent', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400
    if not username:
        # Fallback: create username from email prefix if not provided
        username = email.split('@')[0]
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    import re
    if not re.search(r'\d', password):
        return jsonify({"error": "Password must include at least one number (0-9)."}), 400
    if not re.search(r'[^a-zA-Z0-9]', password):
        return jsonify({"error": "Password must include at least one special character (e.g. !@#$%^&*)."}), 400

    conn = get_db()
    with conn:
        # Check email uniqueness
        existing_email = conn.execute('SELECT id FROM users WHERE LOWER(email) = ?', (email,)).fetchone()
        if existing_email:
            return jsonify({"error": "An account with this email already exists."}), 409

        # Check username uniqueness
        existing_user = conn.execute('SELECT id FROM users WHERE LOWER(username) = ?', (username.lower(),)).fetchone()
        if existing_user:
            return jsonify({"error": "This username is already taken. Please choose another."}), 409

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor = conn.execute(
            '''INSERT INTO users (username, email, password, role, company, signup_time, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (username, email, hashed, role, company, now_str, now_str)
        )
        user_id = cursor.lastrowid

        # Record signup audit log
        conn.execute(
            '''INSERT INTO login_logs (user_id, username, email, role, action, status, timestamp, ip_address, user_agent, details)
               VALUES (?, ?, ?, ?, 'SIGNUP', 'SUCCESS', ?, ?, ?, 'New account created')''',
            (user_id, username, email, role, now_str, ip, ua)
        )

        return jsonify({
            "message": "Account created successfully.",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "company": company,
                "signup_time": now_str
            }
        }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    identifier = (data.get('email') or data.get('username') or data.get('login') or '').strip().lower()
    password = data.get('password', '')
    ip = request.remote_addr or ''
    ua = request.headers.get('User-Agent', '')

    if not identifier or not password:
        return jsonify({"error": "Email/Username and password are required."}), 400

    conn = get_db()
    user = conn.execute(
        'SELECT * FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?', 
        (identifier, identifier)
    ).fetchone()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check user and password hash
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        # Log failed login attempt
        with conn:
            conn.execute(
                '''INSERT INTO login_logs (username, email, role, action, status, timestamp, ip_address, user_agent, details)
                   VALUES (?, ?, '', 'FAILED_LOGIN', 'FAILED', ?, ?, ?, 'Invalid credentials')''',
                (identifier, identifier if '@' in identifier else '', now_str, ip, ua)
            )
        return jsonify({"error": "Invalid email/username or password."}), 401

    # Successful login: update last_login_time and login_count
    new_count = (user['login_count'] or 0) + 1
    with conn:
        conn.execute(
            '''UPDATE users 
               SET last_login_time = ?, login_count = ? 
               WHERE id = ?''',
            (now_str, new_count, user['id'])
        )
        conn.execute(
            '''INSERT INTO login_logs (user_id, username, email, role, action, status, timestamp, ip_address, user_agent, details)
               VALUES (?, ?, ?, ?, 'LOGIN', 'SUCCESS', ?, ?, ?, 'User logged in successfully')''',
            (user['id'], user['username'], user['email'], user['role'], now_str, ip, ua)
        )

    session['userId'] = user['id']
    session['username'] = user['username']
    session['email'] = user['email']
    session['role'] = user['role']

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "role": user['role'],
            "company": user['company'],
            "signup_time": user['signup_time'] or user['created_at'],
            "last_login_time": now_str,
            "login_count": new_count
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    user_id = session.get('userId')
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if user_id:
        conn = get_db()
        with conn:
            conn.execute(
                '''INSERT INTO login_logs (user_id, username, email, role, action, status, timestamp, details)
                   VALUES (?, ?, ?, ?, 'LOGOUT', 'SUCCESS', ?, 'User logged out')''',
                (user_id, session.get('username', ''), session.get('email', ''), session.get('role', ''), now_str)
            )
    session.clear()
    return jsonify({"message": "Logged out successfully."})

@app.route('/api/auth/me')
def me():
    if 'userId' not in session:
        return jsonify({"error": "Not authenticated."}), 401
    
    conn = get_db()
    user = conn.execute(
        'SELECT id, username, email, role, company, signup_time, last_login_time, login_count, created_at FROM users WHERE id = ?', 
        (session['userId'],)
    ).fetchone()
    if not user:
        return jsonify({"error": "User not found."}), 401
        
    return jsonify({"user": dict(user)})

# ── Password Reset & Email Verification ───────────────────
def send_verification_email(to_email, code):
    """
    Sends a 6-digit verification code to the user's email.
    If SMTP credentials are configured (e.g. Gmail App Password), delivers real email.
    Otherwise, logs prominently to server console for testing/development.
    """
    # Dynamically re-read server/.env so credential updates take effect immediately
    for env_path in [os.path.join(os.path.dirname(__file__), '.env'), os.path.join(os.path.dirname(__file__), '..', '.env')]:
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass

    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_EMAIL', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Poppins', Arial, sans-serif; background: #0c2045; color: #1e293b; padding: 25px; margin: 0; }}
            .card {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }}
            .header {{ background: #0b459b; padding: 28px 20px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }}
            .header p {{ margin: 6px 0 0 0; font-size: 12px; color: #a3c7f7; letter-spacing: 1px; text-transform: uppercase; }}
            .body {{ padding: 32px 28px; text-align: center; }}
            .body h2 {{ font-size: 18px; color: #0c2448; margin-top: 0; margin-bottom: 12px; }}
            .body p {{ font-size: 14px; color: #475569; line-height: 1.6; margin: 8px 0; }}
            .code-box {{ display: inline-block; background: #edf2f9; border: 2px dashed #0b459b; border-radius: 10px; padding: 14px 28px; font-size: 34px; font-weight: 700; letter-spacing: 8px; color: #0b459b; margin: 22px 0; font-family: monospace; }}
            .notice {{ font-size: 12px; color: #94a3b8; margin-top: 14px; }}
            .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>SiteSafety Tracker</h1>
                <p>Security & Access Control</p>
            </div>
            <div class="body">
                <h2>Password Reset Request</h2>
                <p>We received a request to reset your password for your SiteSafety Tracker account.</p>
                <p>Use the 6-digit verification code below to complete your reset:</p>
                <div class="code-box">{code}</div>
                <p class="notice">⚠️ This verification code is valid for <strong>15 minutes</strong>.<br>If you did not request a password reset, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                &copy; 2026 SiteSafety Tracker — Incident and Inspection Management System
            </div>
        </div>
    </body>
    </html>
    """

    print(f"\n=======================================================")
    print(f" [EMAIL VERIFICATION CODE] For: {to_email}")
    print(f" CODE: {code} (Expires in 15 minutes)")
    print(f"=======================================================\n")

    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{code} is your SiteSafety Tracker verification code"
            msg['From'] = f"SiteSafety Tracker <{smtp_user}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))

            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
            server.quit()
            print(f"[✓] Real email delivered to {to_email} via SMTP.")
            return True, "Email sent successfully via SMTP."
        except Exception as e:
            print(f"[!] SMTP failed: {e}. (Code printed in terminal above).")
            return False, str(e)
    else:
        print("[i] SMTP credentials not configured. Code logged in terminal for instant testing.")
        return True, "Code logged to server terminal (dev mode)."

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    identifier = data.get('email', '').strip().lower()

    if not identifier:
        return jsonify({"error": "Email address or username is required."}), 400

    conn = get_db()
    user = conn.execute(
        'SELECT id, username, email FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?', 
        (identifier, identifier)
    ).fetchone()
    if not user:
        return jsonify({"error": "No registered account found with that email or username. Please check your spelling or sign up first."}), 404

    target_email = user['email'].lower()

    # Generate 6-digit verification code
    code = f"{random.randint(100000, 999999)}"
    expires_at = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conn:
        conn.execute(
            'INSERT INTO password_resets (email, code, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)',
            (target_email, code, expires_at, now_str)
        )

    sent, info = send_verification_email(target_email, code)

    # In dev mode (when SMTP is not configured), provide code in response for frictionless testing
    is_dev = not bool(os.environ.get('SMTP_EMAIL'))
    
    # Mask email for privacy display
    parts = target_email.split('@')
    masked = f"{parts[0][:2]}***@{parts[1]}" if len(parts[0]) > 2 else f"*@{parts[1]}"

    resp = {
        "message": f"Verification code sent to {masked}. Please check your Inbox and Spam/Junk folder.",
        "email": target_email,
        "masked_email": masked
    }
    if is_dev:
        resp["dev_code"] = code
        resp["dev_note"] = "SMTP not yet set: code displayed for quick development testing."

    return jsonify(resp), 200

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')
    ip = request.remote_addr or ''
    ua = request.headers.get('User-Agent', '')

    if not email or not code or not new_password:
        return jsonify({"error": "Email, verification code, and new password are required."}), 400

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long."}), 400
    import re
    if not re.search(r'\d', new_password):
        return jsonify({"error": "New password must include at least one number (0-9)."}), 400
    if not re.search(r'[^a-zA-Z0-9]', new_password):
        return jsonify({"error": "New password must include at least one special character (e.g. !@#$%^&*)."}), 400

    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    reset_record = conn.execute(
        '''SELECT id FROM password_resets 
           WHERE LOWER(email) = ? AND code = ? AND used = 0 AND expires_at > ?
           ORDER BY id DESC LIMIT 1''',
        (email, code, now_str)
    ).fetchone()

    if not reset_record:
        return jsonify({"error": "Invalid or expired verification code. Please request a new code."}), 400

    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    with conn:
        conn.execute('UPDATE users SET password = ? WHERE LOWER(email) = ?', (hashed, email))
        conn.execute('UPDATE password_resets SET used = 1 WHERE id = ?', (reset_record['id'],))
        conn.execute(
            '''INSERT INTO login_logs (username, email, role, action, status, timestamp, ip_address, user_agent, details)
               VALUES (?, ?, '', 'PASSWORD_RESET', 'SUCCESS', ?, ?, ?, 'Password reset via email verification code')''',
            (email, email, now_str, ip, ua)
        )

    return jsonify({"message": "Password successfully updated! You can now log in with your new password."}), 200


@app.route('/api/admin/users')
def list_users():
    conn = get_db()
    rows = conn.execute(
        '''SELECT id, username, email, role, company, signup_time, last_login_time, login_count, created_at 
           FROM users ORDER BY id ASC'''
    ).fetchall()
    return jsonify({"users": [dict(r) for r in rows]})

@app.route('/api/admin/login-logs')
def list_login_logs():
    limit = int(request.args.get('limit', 100))
    conn = get_db()
    rows = conn.execute(
        '''SELECT id, user_id, username, email, role, action, status, timestamp, ip_address, details 
           FROM login_logs ORDER BY id DESC LIMIT ?''', 
        (limit,)
    ).fetchall()
    return jsonify({"logs": [dict(r) for r in rows]})

# ── Interactive Database Viewer (Web UI) ─────────────────
@app.route('/db-viewer')
def db_viewer():
    conn = get_db()
    users = conn.execute("SELECT id, username, email, role, company, signup_time, last_login_time, login_count FROM users ORDER BY id ASC").fetchall()
    logs = conn.execute("SELECT id, username, email, role, action, status, timestamp, ip_address, details FROM login_logs ORDER BY id DESC LIMIT 50").fetchall()
    hazards = conn.execute("SELECT ticket, location, category, urgency, status, reporter_name, date FROM hazards ORDER BY id DESC LIMIT 20").fetchall()
    inspections = conn.execute("SELECT id, title, location, inspector, date, time, status FROM inspections ORDER BY id DESC LIMIT 20").fetchall()
    
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SiteSafety Tracker — SQLite Database Viewer</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #0f172a;
                --surface: #1e293b;
                --surface-card: #182234;
                --border: #334155;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --primary: #38bdf8;
                --accent: #f59e0b;
                --success: #10b981;
                --danger: #ef4444;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Poppins', sans-serif;
                background: var(--bg);
                color: var(--text);
                padding: 30px 20px;
                min-height: 100vh;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 15px;
                margin-bottom: 25px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--border);
            }
            h1 { font-size: 24px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
            .badge { background: #0284c7; color: #fff; font-size: 11px; padding: 3px 8px; border-radius: 999px; text-transform: uppercase; font-weight: 600; }
            .meta-text { color: var(--text-muted); font-size: 13px; font-family: 'JetBrains Mono', monospace; }
            
            .nav-tabs {
                display: flex;
                gap: 8px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .tab-btn {
                background: var(--surface);
                color: var(--text-muted);
                border: 1px solid var(--border);
                padding: 8px 18px;
                border-radius: 8px;
                font-family: inherit;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            .tab-btn:hover { background: #283548; color: #fff; }
            .tab-btn.active {
                background: var(--primary);
                color: #0f172a;
                font-weight: 600;
                border-color: var(--primary);
            }

            .card {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
                margin-bottom: 30px;
            }
            .card-header {
                padding: 16px 20px;
                background: var(--surface-card);
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .card-title { font-size: 16px; font-weight: 600; }
            .count-pill { background: rgba(56,189,248,0.15); color: var(--primary); font-size: 12px; padding: 2px 10px; border-radius: 999px; font-weight: 600; }
            
            .table-wrap { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
            th {
                background: #151f30;
                padding: 12px 16px;
                color: var(--text-muted);
                font-weight: 600;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.5px;
                border-bottom: 1px solid var(--border);
            }
            td {
                padding: 12px 16px;
                border-bottom: 1px solid #243144;
                color: #e2e8f0;
            }
            tr:hover td { background: rgba(255,255,255,0.02); }
            
            .role-pill {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .role-manager { background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); }
            .role-staff { background: rgba(56,189,248,0.2); color: #38bdf8; border: 1px solid rgba(56,189,248,0.4); }
            
            .status-tag {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            .status-success { background: rgba(16,185,129,0.2); color: #10b981; }
            .status-failed { background: rgba(239,68,68,0.2); color: #ef4444; }
            
            .mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
            .action-links { display: flex; gap: 10px; }
            .btn-action {
                text-decoration: none;
                background: var(--surface);
                color: var(--text);
                border: 1px solid var(--border);
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                display: inline-flex;
                align-items: center;
                gap: 5px;
                transition: 0.2s;
            }
            .btn-action:hover { background: #334155; color: #fff; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1>SiteSafety Tracker <span class="badge">SQLite Database</span></h1>
                    <p class="meta-text" style="margin-top: 5px;">File: server/sitesafety.db • Port 8000 Active</p>
                </div>
                <div class="action-links">
                    <a href="/login.html" class="btn-action">← Go to Login Page</a>
                    <a href="/index.html" class="btn-action">🏠 Home</a>
                    <button onclick="location.reload()" class="btn-action">🔄 Refresh Data</button>
                </div>
            </header>

            <div class="nav-tabs">
                <button class="tab-btn active" onclick="switchTab('tab-users')">👥 Users & Logins (''' + str(len(users)) + ''')</button>
                <button class="tab-btn" onclick="switchTab('tab-logs')">📜 Login Audit Logs (''' + str(len(logs)) + ''')</button>
                <button class="tab-btn" onclick="switchTab('tab-hazards')">⚠️ Hazards (''' + str(len(hazards)) + ''')</button>
                <button class="tab-btn" onclick="switchTab('tab-inspections')">📋 Inspections (''' + str(len(inspections)) + ''')</button>
            </div>

            <!-- TAB 1: USERS -->
            <div id="tab-users" class="tab-content active">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Registered Users</span>
                        <span class="count-pill">''' + str(len(users)) + ''' Users</span>
                    </div>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Company</th>
                                    <th>Time of Sign Up</th>
                                    <th>Time of Last Login</th>
                                    <th>Login Count</th>
                                </tr>
                            </thead>
                            <tbody>
    '''
    for u in users:
        role_cls = 'role-manager' if u['role'] == 'manager' else 'role-staff'
        last_log = u['last_login_time'] or '<span style="color:#64748b;">Never</span>'
        html += f'''
                                <tr>
                                    <td class="mono">{u['id']}</td>
                                    <td><strong>{u['username']}</strong></td>
                                    <td class="mono">{u['email']}</td>
                                    <td><span class="role-pill {role_cls}">{u['role']}</span></td>
                                    <td>{u['company']}</td>
                                    <td class="mono">{u['signup_time']}</td>
                                    <td class="mono">{last_log}</td>
                                    <td><strong>{u['login_count']}</strong></td>
                                </tr>
        '''
    html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 2: AUDIT LOGS -->
            <div id="tab-logs" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Login & Activity Audit Trail</span>
                        <span class="count-pill">Last 50 Logs</span>
                    </div>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Log ID</th>
                                    <th>Action</th>
                                    <th>Status</th>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Timestamp</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody>
    '''
    for log in logs:
        st_cls = 'status-success' if log['status'] == 'SUCCESS' else 'status-failed'
        html += f'''
                                <tr>
                                    <td class="mono">{log['id']}</td>
                                    <td><strong>{log['action']}</strong></td>
                                    <td><span class="status-tag {st_cls}">{log['status']}</span></td>
                                    <td>{log['username']}</td>
                                    <td class="mono">{log['email']}</td>
                                    <td>{log['role']}</td>
                                    <td class="mono">{log['timestamp']}</td>
                                    <td style="color:#cbd5e1;">{log['details']}</td>
                                </tr>
        '''
    html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 3: HAZARDS -->
            <div id="tab-hazards" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Recent Hazards</span>
                        <span class="count-pill">''' + str(len(hazards)) + ''' Records</span>
                    </div>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Ticket #</th>
                                    <th>Category</th>
                                    <th>Location</th>
                                    <th>Urgency</th>
                                    <th>Status</th>
                                    <th>Reporter</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
    '''
    for h in hazards:
        html += f'''
                                <tr>
                                    <td class="mono"><strong>{h['ticket']}</strong></td>
                                    <td>{h['category']}</td>
                                    <td>{h['location']}</td>
                                    <td>{h['urgency']}</td>
                                    <td>{h['status']}</td>
                                    <td>{h['reporter_name']}</td>
                                    <td class="mono">{h['date']}</td>
                                </tr>
        '''
    html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 4: INSPECTIONS -->
            <div id="tab-inspections" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Scheduled Inspections</span>
                        <span class="count-pill">''' + str(len(inspections)) + ''' Records</span>
                    </div>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Title</th>
                                    <th>Location</th>
                                    <th>Inspector</th>
                                    <th>Date</th>
                                    <th>Time</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
    '''
    for i in inspections:
        html += f'''
                                <tr>
                                    <td class="mono">{i['id']}</td>
                                    <td><strong>{i['title']}</strong></td>
                                    <td>{i['location']}</td>
                                    <td>{i['inspector']}</td>
                                    <td class="mono">{i['date']}</td>
                                    <td class="mono">{i['time']}</td>
                                    <td>{i['status']}</td>
                                </tr>
        '''
    html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function switchTab(tabId) {
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                
                event.currentTarget.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

# ── Hazard Routes ────────────────────────────────────────
@app.route('/api/hazards')
def list_hazards():
    status = request.args.get('status')
    urgency = request.args.get('urgency')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))

    sql = 'SELECT * FROM hazards WHERE 1=1'
    params = []

    if status:
        sql += ' AND status = ?'
        params.append(status)
    if urgency and urgency != 'all':
        sql += ' AND LOWER(urgency) = LOWER(?)'
        params.append(urgency)
    if search:
        sql += ' AND (LOWER(ticket) LIKE ? OR LOWER(location) LIKE ? OR LOWER(category) LIKE ?)'
        q = f"%{search.lower()}%"
        params.extend([q, q, q])

    sql += ' ORDER BY id DESC'
    
    conn = get_db()
    count_sql = sql.replace('SELECT *', 'SELECT COUNT(*) as total')
    total = conn.execute(count_sql, params).fetchone()['total']

    offset = (page - 1) * limit
    sql += ' LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    
    hazards = []
    for row in rows:
        hazards.append({
            "ticket": row['ticket'],
            "location": row['location'],
            "category": row['category'],
            "date": row['date'],
            "time": row['time'],
            "urgency": row['urgency'],
            "status": row['status'],
            "cause": row['cause'],
            "photo": row['photo'],
            "resolvedDate": row['resolved_date'],
            "personnel": {
                "name": row['reporter_name'],
                "position": row['reporter_position'],
                "phone": row['reporter_phone'],
                "dept": row['reporter_dept']
            }
        })

    return jsonify({"hazards": hazards, "total": total, "page": page, "limit": limit})

@app.route('/api/hazards/<ticket>')
def get_hazard(ticket):
    conn = get_db()
    row = conn.execute('SELECT * FROM hazards WHERE ticket = ?', (ticket,)).fetchone()
    if not row:
        return jsonify({"error": "Hazard not found."}), 404
        
    return jsonify({
        "ticket": row['ticket'],
        "location": row['location'],
        "category": row['category'],
        "date": row['date'],
        "time": row['time'],
        "urgency": row['urgency'],
        "status": row['status'],
        "cause": row['cause'],
        "photo": row['photo'],
        "resolvedDate": row['resolved_date'],
        "personnel": {
            "name": row['reporter_name'],
            "position": row['reporter_position'],
            "phone": row['reporter_phone'],
            "dept": row['reporter_dept']
        }
    })

@app.route('/api/hazards', methods=['POST'])
def create_hazard():
    data = request.json or {}
    now = datetime.now()
    mm = f"{now.month:02d}"
    dd = f"{now.day:02d}"
    yy = str(now.year)
    
    conn = get_db()
    with conn:
        count = conn.execute('SELECT COUNT(*) as c FROM hazards').fetchone()['c'] + 1
        ticket = f"ABC-{yy}-{mm}{dd}-{count:02d}"
        date_str = f"{mm}-{dd}-{yy[-2:]}"
        time_str = now.strftime("%I:%M %p")
        
        personnel = data.get('personnel', {})
        
        conn.execute('''
            INSERT INTO hazards (ticket, location, category, date, time, urgency, status, cause, photo,
            reporter_name, reporter_position, reporter_phone, reporter_dept)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?)
        ''', (
            ticket, data.get('location', 'Unknown Location'), data.get('category', 'General Hazard'),
            date_str, time_str, data.get('urgency', 'Medium'), data.get('cause', ''), data.get('photo', ''),
            personnel.get('name', ''), personnel.get('position', ''), personnel.get('phone', ''), personnel.get('dept', '')
        ))
        
        conn.execute('INSERT INTO notifications (title, time_label, unread) VALUES (?, ?, 1)', 
                     (f"New Hazard Report: {ticket} - {data.get('category', '')}", "Just now"))
                     
    return jsonify({"message": "Hazard report created.", "ticket": ticket}), 201

@app.route('/api/hazards/<ticket>/resolve', methods=['PATCH'])
def resolve_hazard(ticket):
    resolved_date = datetime.now().strftime("%m-%d-%y")
    
    conn = get_db()
    with conn:
        cursor = conn.execute("UPDATE hazards SET status = 'Resolved', resolved_date = ? WHERE ticket = ? AND status = 'Pending'", 
                              (resolved_date, ticket))
        if cursor.rowcount == 0:
            return jsonify({"error": "Hazard not found or already resolved."}), 404
            
        conn.execute('INSERT INTO notifications (title, time_label, unread) VALUES (?, ?, 1)', 
                     (f"Hazard Ticket {ticket} Marked as Resolved", "Just now"))
                     
    return jsonify({"message": "Hazard marked as resolved.", "ticket": ticket})

@app.route('/api/hazards/export/csv')
def export_hazards():
    conn = get_db()
    rows = conn.execute("SELECT * FROM hazards WHERE status = 'Resolved' ORDER BY id DESC").fetchall()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Ticket Number','Location','Category','Incident Date','Incident Time','Status','Incident Cause','Reporter'])
    
    for r in rows:
        cw.writerow([
            r['ticket'], r['location'], r['category'], r['date'], r['time'], r['status'], 
            r['cause'], r['reporter_name']
        ])
        
    return Response(si.getvalue(), mimetype='text/csv', 
                    headers={"Content-Disposition": "attachment; filename=SiteSafety_Resolved_Hazards.csv"})

# ── Inspection Routes ────────────────────────────────────
@app.route('/api/inspections')
def list_inspections():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) as c FROM inspections').fetchone()['c']
    offset = (page - 1) * limit
    
    rows = conn.execute('SELECT * FROM inspections ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    inspections = [dict(row) for row in rows]
    
    return jsonify({"inspections": inspections, "total": total, "page": page, "limit": limit})

@app.route('/api/inspections', methods=['POST'])
def create_inspection():
    data = request.json or {}
    if not data.get('title') or not data.get('location') or not data.get('inspector'):
        return jsonify({"error": "Title, location, and inspector are required."}), 400
        
    conn = get_db()
    with conn:
        cursor = conn.execute(
            'INSERT INTO inspections (title, location, inspector, date, time, status) VALUES (?, ?, ?, ?, ?, ?)',
            (data.get('title'), data.get('location'), data.get('inspector'), 
             data.get('date', 'TBD'), data.get('time', 'TBD'), data.get('status', 'Scheduled'))
        )
        conn.execute('INSERT INTO notifications (title, time_label, unread) VALUES (?, ?, 1)', 
                     (f"New Inspection Scheduled: {data.get('title')}", "Just now"))
                     
    return jsonify({"message": "Inspection scheduled successfully.", "id": cursor.lastrowid}), 201

@app.route('/api/inspections/<int:id>', methods=['DELETE'])
def delete_inspection(id):
    conn = get_db()
    with conn:
        cursor = conn.execute('DELETE FROM inspections WHERE id = ?', (id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Inspection not found."}), 404
            
    return jsonify({"message": "Inspection cancelled."})

# ── Notification Routes ──────────────────────────────────
@app.route('/api/notifications')
def list_notifications():
    conn = get_db()
    rows = conn.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 20').fetchall()
    
    notifications = []
    for row in rows:
        notifications.append({
            "id": str(row['id']),
            "title": row['title'],
            "time": row['time_label'],
            "unread": bool(row['unread'])
        })
        
    return jsonify({"notifications": notifications})

@app.route('/api/notifications', methods=['POST'])
def create_notification():
    title = (request.json or {}).get('title')
    if not title:
        return jsonify({"error": "Notification title is required."}), 400
        
    conn = get_db()
    with conn:
        cursor = conn.execute('INSERT INTO notifications (title, time_label, unread) VALUES (?, ?, 1)', (title, 'Just now'))
        
    return jsonify({"message": "Notification created.", "id": cursor.lastrowid}), 201

@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    conn = get_db()
    with conn:
        conn.execute('DELETE FROM notifications')
    return jsonify({"message": "All notifications cleared."})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print('')
    print('  +------------------------------------------------+')
    print('  |     SiteSafety Tracker Server Online           |')
    print(f'  |     Main Site:  http://localhost:{port}           |')
    print(f'  |     DB Viewer:  http://localhost:{port}/db-viewer |')
    print('  +------------------------------------------------+')
    print('')
    app.run(host='0.0.0.0', port=port, debug=False)
