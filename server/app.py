from flask import Flask, request, jsonify, session, send_from_directory, Response, render_template_string, redirect
from functools import wraps
from flask_cors import CORS
import bcrypt
import os
import sys
import io
import csv
from datetime import datetime, timedelta
import random
import secrets
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

app = Flask(__name__, static_folder=WORKSPACE_ROOT, static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
CORS(app, supports_credentials=True)

# ── Auth Guards ──────────────────────────────────────────
def login_required(f):
    """Decorator: rejects requests if user is not authenticated via session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'userId' not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated

def manager_required(f):
    """Decorator: rejects requests if user is not an authenticated manager."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'userId' not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        if session.get('role') != 'manager':
            return jsonify({"error": "Access denied. Manager privileges required."}), 403
        return f(*args, **kwargs)
    return decorated

def esc(val):
    """Escape user-supplied values for safe HTML rendering (XSS protection)."""
    if val is None:
        return ''
    from markupsafe import escape as _escape
    return str(_escape(str(val)))

def safe_int(val, default=1, min_val=1, max_val=1000):
    """Safely parse integer query parameters with bounds checking to prevent 500 crashes."""
    try:
        n = int(val)
        return max(min_val, min(n, max_val))
    except (ValueError, TypeError):
        return default

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
    return send_from_directory(WORKSPACE_ROOT, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    root_path = os.path.join(WORKSPACE_ROOT, path)
    if os.path.exists(root_path) and os.path.isfile(root_path):
        return send_from_directory(WORKSPACE_ROOT, path)
        
    # If looking for an HTML page without extension
    if '.' not in path:
        html_root = os.path.join(WORKSPACE_ROOT, f"{path}.html")
        if os.path.exists(html_root):
            return send_from_directory(WORKSPACE_ROOT, f"{path}.html")

    return "File not found", 404

# ── Health ───────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

def log_activity(action, status='SUCCESS', details='', user_id=None, username=None, email=None, role=None):
    """
    Strictly record all user and manager activities into the login_logs audit table.
    """
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip = request.remote_addr or ''
        ua = request.headers.get('User-Agent', '')
        if not username and 'userId' in session:
            user_id = session.get('userId')
            username = session.get('username')
            email = session.get('email')
            role = session.get('role')
        conn = get_db()
        with conn:
            conn.execute(
                '''INSERT INTO login_logs (user_id, username, email, role, action, status, timestamp, ip_address, user_agent, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, username or 'System', email or '', role or '', action, status, now_str, ip, ua, details)
            )
    except Exception as e:
        print(f"[*] Activity log error: {e}")

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

    session.permanent = True
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

@app.route('/api/auth/profile', methods=['PUT', 'POST'])
@login_required
def update_profile():
    user_id = session.get('userId')
    data = request.json or {}
    new_username = data.get('username', '').strip()
    new_email = data.get('email', '').strip().lower()
    new_company = data.get('company', '').strip()

    if not new_email:
        return jsonify({"error": "Email is required."}), 400

    conn = get_db()
    with conn:
        existing = conn.execute('SELECT id FROM users WHERE LOWER(email) = ? AND id != ?', (new_email, user_id)).fetchone()
        if existing:
            return jsonify({"error": "This email address is already in use by another account."}), 409

        if new_username:
            existing_u = conn.execute('SELECT id FROM users WHERE LOWER(username) = ? AND id != ?', (new_username.lower(), user_id)).fetchone()
            if existing_u:
                return jsonify({"error": "This username is already taken."}), 409

        conn.execute(
            '''UPDATE users
               SET username = COALESCE(NULLIF(?, ''), username),
                   email = ?,
                   company = ?
               WHERE id = ?''',
            (new_username, new_email, new_company, user_id)
        )

        user = conn.execute(
            'SELECT id, username, email, role, company, signup_time, last_login_time, login_count FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        session['username'] = user['username']
        session['email'] = user['email']

        log_activity('UPDATE_PROFILE', 'SUCCESS', f"User updated profile: {user['username']} ({user['email']})")

    return jsonify({
        "message": "Profile updated successfully.",
        "user": dict(user)
    })

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

    # Generate 6-digit verification code using cryptographically secure secrets module
    code = f"{secrets.randbelow(900000) + 100000}"
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
@manager_required
def list_users():
    conn = get_db()
    rows = conn.execute(
        '''SELECT id, username, email, role, company, signup_time, last_login_time, login_count, created_at 
           FROM users ORDER BY id ASC'''
    ).fetchall()
    return jsonify({"users": [dict(r) for r in rows]})
@app.route('/api/admin/login-logs')
@manager_required
def list_login_logs():
    limit = safe_int(request.args.get('limit'), default=100, min_val=1, max_val=500)
    conn = get_db()
    rows = conn.execute(
        '''SELECT id, user_id, username, email, role, action, status, timestamp, ip_address, details 
           FROM login_logs ORDER BY id DESC LIMIT ?''', 
        (limit,)
    ).fetchall()
    return jsonify({"logs": [dict(r) for r in rows]})

# ── Interactive Database Viewer (Web UI - Dark Theme) ─────
@app.route('/db-viewer')
def db_viewer():
    # Require manager-level authentication to access DB viewer
    if 'userId' not in session:
        return redirect('/login.html')
    if session.get('role') != 'manager':
        return redirect('/home.html')
    conn = get_db()
    users = conn.execute("SELECT id, username, email, role, company, signup_time, last_login_time, login_count FROM users ORDER BY id ASC").fetchall()
    logs = conn.execute("SELECT id, user_id, username, email, role, action, status, timestamp, ip_address, details FROM login_logs ORDER BY id DESC LIMIT 150").fetchall()
    hazards = conn.execute("SELECT ticket, location, category, urgency, status, reporter_name, date, time, cause FROM hazards ORDER BY id DESC").fetchall()
    inspections = conn.execute("SELECT id, title, location, inspector, date, time, status FROM inspections ORDER BY id DESC").fetchall()
    contacts = conn.execute("SELECT id, name, position, phone, email, department, status FROM contacts ORDER BY id DESC").fetchall()
    
    total_users = len(users)
    manager_count = sum(1 for u in users if u['role'] == 'manager')
    staff_count = sum(1 for u in users if u['role'] == 'staff')
    pending_hazards = sum(1 for h in hazards if h['status'] == 'Pending')
    resolved_hazards = sum(1 for h in hazards if h['status'] == 'Resolved')
    total_inspections = len(inspections)
    total_logs = conn.execute("SELECT COUNT(*) as c FROM login_logs").fetchone()['c']
    total_contacts = len(contacts)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SiteSafety Tracker — Central Database Hub</title>
    <link rel="icon" href="logo.png" type="image/png">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-deep: #081733;
            --bg-card: #0c2045;
            --bg-card-alt: #0a1b38;
            --bg-navbar: #0b459b;
            --primary-blue: #0b459b;
            --primary-hover: #0d54bc;
            --border-color: rgba(163, 199, 247, 0.22);
            --border-focus: #a3c7f7;
            --border-light: #bdd6f5;
            --text-main: #ffffff;
            --text-body: #e2e8f0;
            --text-muted: #8cbdf6;
            --text-dim: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-deep);
            color: var(--text-body);
            min-height: 100vh;
            padding: 24px 20px 60px;
            line-height: 1.5;
            background-image: radial-gradient(circle at 15% 15%, rgba(12, 32, 69, 0.8) 0%, transparent 60%),
                              radial-gradient(circle at 85% 85%, rgba(11, 69, 155, 0.25) 0%, transparent 60%);
        }}
        .container {{ max-width: 1320px; margin: 0 auto; }}

        /* Top Bar matching home page header */
        header.db-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            padding: 16px 24px;
            background: var(--bg-navbar);
            border: 1px solid var(--border-focus);
            border-radius: 12px;
            box-shadow: 0 8px 24px -4px rgba(8, 23, 51, 0.5);
            margin-bottom: 24px;
        }}
        .header-brand {{ display: flex; flex-direction: column; }}
        .header-title-main {{ font-size: 17px; font-weight: 700; letter-spacing: 0.5px; color: #ffffff; text-transform: uppercase; }}
        .header-title-sub {{ font-size: 12px; font-weight: 600; color: #bdd6f5; letter-spacing: 0.8px; text-transform: uppercase; margin-top: 1px; }}
        .header-title-desc {{ font-size: 11px; font-weight: 500; color: #e2e8f0; margin-top: 2px; }}

        .header-actions {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
        .db-status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 7px 14px;
            background: rgba(8, 23, 51, 0.45);
            border: 1px solid rgba(163, 199, 247, 0.35);
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: #ffffff;
        }}
        .pulse-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #34d399;
            box-shadow: 0 0 6px #34d399;
            animation: pulseAnim 2s infinite ease-in-out;
        }}
        @keyframes pulseAnim {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.25); opacity: 0.6; }}
        }}
        .btn-top {{
            display: inline-flex;
            align-items: center;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s ease;
            cursor: pointer;
            border: 1px solid rgba(163, 199, 247, 0.35);
            background: rgba(8, 23, 51, 0.45);
            color: #ffffff;
        }}
        .btn-top:hover {{ background: rgba(8, 23, 51, 0.75); border-color: #ffffff; transform: translateY(-1px); }}
        .btn-action-primary {{ background: #0c2045; border-color: #bdd6f5; }}
        .btn-action-primary:hover {{ background: #081733; }}

        /* Metric Cards Row */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px 20px;
            position: relative;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
            border-top: 3px solid var(--border-focus);
            transition: transform 0.2s, border-color 0.2s;
        }}
        .kpi-card:hover {{ transform: translateY(-2px); border-color: var(--border-focus); }}
        .kpi-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            font-family: 'JetBrains Mono', monospace;
        }}
        .kpi-sub {{
            font-size: 11px;
            color: var(--text-dim);
            margin-top: 4px;
        }}

        /* Live Table Search Filter */
        .search-container {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 18px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
        }}
        .search-input {{
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #ffffff;
            font-size: 13px;
            font-family: inherit;
        }}
        .search-input::placeholder {{ color: var(--text-dim); }}
        .search-badge {{
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: var(--text-muted);
            background: rgba(8, 23, 51, 0.5);
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }}

        /* Tab Navigation */
        .tabs-nav {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .tab-btn {{
            background: var(--bg-card);
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            padding: 9px 18px;
            border-radius: 8px;
            font-family: inherit;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        .tab-btn:hover {{ background: #0f2752; color: #ffffff; border-color: var(--border-focus); }}
        .tab-btn.active {{
            background: var(--bg-navbar);
            color: #ffffff;
            border-color: var(--border-focus);
            box-shadow: 0 4px 12px rgba(11, 69, 155, 0.4);
        }}
        .tab-count {{
            background: rgba(8, 23, 51, 0.5);
            font-size: 11px;
            padding: 2px 7px;
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            color: #ffffff;
        }}

        /* Table Card Container */
        .card-table {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.35);
            margin-bottom: 30px;
        }}
        .card-table-header {{
            padding: 14px 20px;
            background: #081733;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .table-title {{ font-size: 14px; font-weight: 600; color: #ffffff; letter-spacing: 0.3px; }}
        .table-wrap {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
        th {{
            background: var(--bg-navbar);
            padding: 12px 16px;
            color: #ffffff;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.6px;
            border-bottom: 1px solid var(--border-focus);
            white-space: nowrap;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(163, 199, 247, 0.1);
            color: var(--text-body);
        }}
        tr:nth-child(even) td {{ background: rgba(8, 23, 51, 0.4); }}
        tr:hover td {{ background: rgba(11, 69, 155, 0.2); }}

        /* Badges & Tags */
        .mono {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; }}
        .badge {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            white-space: nowrap;
        }}
        .badge-manager {{ background: rgba(245, 216, 53, 0.15); color: #fde047; border: 1px solid rgba(245, 216, 53, 0.35); }}
        .badge-staff {{ background: rgba(140, 189, 246, 0.15); color: #8cbdf6; border: 1px solid rgba(140, 189, 246, 0.35); }}
        .badge-pending {{ background: rgba(245, 216, 53, 0.15); color: #fde047; border: 1px solid rgba(245, 216, 53, 0.35); }}
        .badge-resolved {{ background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.35); }}
        .badge-scheduled {{ background: rgba(140, 189, 246, 0.15); color: #8cbdf6; border: 1px solid rgba(140, 189, 246, 0.35); }}

        .urgency-high {{ color: #f87171; font-weight: 600; }}
        .urgency-medium {{ color: #fde047; font-weight: 600; }}
        .urgency-low {{ color: #34d399; font-weight: 600; }}

        /* Action Badges */
        .action-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 0.3px;
        }}
        .action-report {{ background: rgba(245, 216, 53, 0.15); color: #fde047; border: 1px solid rgba(245, 216, 53, 0.3); }}
        .action-resolve {{ background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }}
        .action-inspection {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        .action-cancel {{ background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }}
        .action-contact {{ background: rgba(20, 184, 166, 0.15); color: #2dd4bf; border: 1px solid rgba(20, 184, 166, 0.3); }}
        .action-login {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .action-logout {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}
        .action-signup {{ background: rgba(129, 140, 248, 0.15); color: #a5b4fc; border: 1px solid rgba(129, 140, 248, 0.3); }}
        .action-default {{ background: rgba(148, 163, 184, 0.12); color: #cbd5e1; }}

        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        .empty-cell {{ color: var(--text-dim); font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Bar matching website header -->
        <header class="db-header">
            <div class="header-brand">
                <div class="header-title-main">SiteSafety Tracker</div>
                <div class="header-title-sub">Database Hub</div>
                <div class="header-title-desc">Central SQLite System Records</div>
            </div>
            <div class="header-actions">
                <div class="db-status-pill">
                    <span class="pulse-dot"></span>
                    <span>Database: sitesafety.db</span>
                </div>
                <a href="/manager-home.html" class="btn-top">Manager Portal</a>
                <a href="/home.html" class="btn-top">Staff Portal</a>
                <button type="button" onclick="location.reload()" class="btn-top btn-action-primary">Refresh</button>
                <a href="/api/hazards/export/csv" class="btn-top btn-action-primary">Export CSV</a>
            </div>
        </header>

        <!-- Metric Cards Row (Clean, words only) -->
        <section class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Users</div>
                <div class="kpi-value">{total_users}</div>
                <div class="kpi-sub">{manager_count} Managers • {staff_count} Staff</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Pending Hazards</div>
                <div class="kpi-value">{pending_hazards}</div>
                <div class="kpi-sub">Active open reports</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Resolved Hazards</div>
                <div class="kpi-value">{resolved_hazards}</div>
                <div class="kpi-sub">Archived resolutions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Scheduled Inspections</div>
                <div class="kpi-value">{total_inspections}</div>
                <div class="kpi-sub">Timetable checks</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Audit Records</div>
                <div class="kpi-value">{total_logs}</div>
                <div class="kpi-sub">Logged activities</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Directory Contacts</div>
                <div class="kpi-value">{total_contacts}</div>
                <div class="kpi-sub">Personnel listed</div>
            </div>
        </section>

        <!-- Live Instant Search Bar -->
        <div class="search-container">
            <input type="text" id="db-search-input" class="search-input" placeholder="Search records across active table (e.g. ticket, username, location, action)...">
            <span class="search-badge">Instant Filter</span>
        </div>

        <!-- Tab Navigation Bar -->
        <nav class="tabs-nav">
            <button class="tab-btn active" onclick="switchTab('tab-users', this)">
                Users <span class="tab-count">{total_users}</span>
            </button>
            <button class="tab-btn" onclick="switchTab('tab-logs', this)">
                Audit Trail <span class="tab-count">{total_logs}</span>
            </button>
            <button class="tab-btn" onclick="switchTab('tab-hazards', this)">
                Hazard Reports <span class="tab-count">{len(hazards)}</span>
            </button>
            <button class="tab-btn" onclick="switchTab('tab-inspections', this)">
                Inspections <span class="tab-count">{total_inspections}</span>
            </button>
            <button class="tab-btn" onclick="switchTab('tab-contacts', this)">
                Contacts <span class="tab-count">{total_contacts}</span>
            </button>
        </nav>

        <!-- TAB 1: USERS -->
        <div id="tab-users" class="tab-panel active">
            <div class="card-table">
                <div class="card-table-header">
                    <div class="table-title">User Accounts ({total_users})</div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>User ID</th>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Company</th>
                                <th>Sign Up Time</th>
                                <th>Last Login</th>
                                <th>Logins</th>
                            </tr>
                        </thead>
                        <tbody>'''
    
    for u in users:
        role_badge = 'badge-manager' if u['role'] == 'manager' else 'badge-staff'
        last_log = esc(u['last_login_time']) or '<span class="empty-cell">Never</span>'
        html += f'''
                            <tr>
                                <td class="mono">#{u['id']}</td>
                                <td><strong>{esc(u['username'])}</strong></td>
                                <td class="mono">{esc(u['email'])}</td>
                                <td><span class="badge {role_badge}">{esc(u['role'])}</span></td>
                                <td>{esc(u['company']) or '<span class="empty-cell">N/A</span>'}</td>
                                <td class="mono">{esc(u['signup_time'])}</td>
                                <td class="mono">{last_log}</td>
                                <td class="mono"><strong>{u['login_count']}</strong></td>
                            </tr>'''
    
    html += f'''
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 2: AUDIT TRAIL -->
        <div id="tab-logs" class="tab-panel">
            <div class="card-table">
                <div class="card-table-header">
                    <div class="table-title">Activity and Audit Trail (Showing {len(logs)} of {total_logs} records)</div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Log ID</th>
                                <th>Action</th>
                                <th>Status</th>
                                <th>Account</th>
                                <th>Role</th>
                                <th>Timestamp</th>
                                <th>IP Address</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>'''
    
    for l in logs:
        action = l['action']
        if 'REPORT' in action or 'HAZARD' in action and 'RESOLVE' not in action:
            act_cls = 'action-report'
        elif 'RESOLVE' in action:
            act_cls = 'action-resolve'
        elif 'INSPECTION' in action and 'CANCEL' not in action:
            act_cls = 'action-inspection'
        elif 'CANCEL' in action or 'DELETE' in action:
            act_cls = 'action-cancel'
        elif 'CONTACT' in action:
            act_cls = 'action-contact'
        elif 'LOGIN' in action:
            act_cls = 'action-login'
        elif 'LOGOUT' in action:
            act_cls = 'action-logout'
        elif 'SIGNUP' in action:
            act_cls = 'action-signup'
        else:
            act_cls = 'action-default'
            
        status_color = '#34d399' if l['status'] == 'SUCCESS' else '#f87171'
        role_label = l['role'] or 'system'
        
        html += f'''
                            <tr>
                                <td class="mono">#{l['id']}</td>
                                <td><span class="action-tag {act_cls}">{esc(l['action'])}</span></td>
                                <td style="color:{status_color}; font-weight:600; font-size:11px;">{esc(l['status'])}</td>
                                <td><strong>{esc(l['username'] or l['email'] or 'System')}</strong></td>
                                <td><span class="badge {'badge-manager' if role_label=='manager' else 'badge-staff'}">{esc(role_label)}</span></td>
                                <td class="mono">{esc(l['timestamp'])}</td>
                                <td class="mono">{esc(l['ip_address']) or '<span class="empty-cell">local</span>'}</td>
                                <td>{esc(l['details'])}</td>
                            </tr>'''

    html += f'''
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 3: HAZARDS (PENDING & RESOLVED) -->
        <div id="tab-hazards" class="tab-panel">
            <div class="card-table">
                <div class="card-table-header">
                    <div class="table-title">Hazard Reports ({len(hazards)})</div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Ticket</th>
                                <th>Location</th>
                                <th>Category</th>
                                <th>Urgency</th>
                                <th>Status</th>
                                <th>Reporter</th>
                                <th>Date &amp; Time</th>
                                <th>Cause / Description</th>
                            </tr>
                        </thead>
                        <tbody>'''
    
    for h in hazards:
        status_cls = 'badge-resolved' if h['status'] == 'Resolved' else 'badge-pending'
        urg = (h['urgency'] or 'Medium').lower()
        urg_cls = f'urgency-{urg}' if urg in ['high', 'medium', 'low'] else 'urgency-medium'
        html += f'''
                            <tr>
                                <td class="mono"><strong>{esc(h['ticket'])}</strong></td>
                                <td>{esc(h['location'])}</td>
                                <td>{esc(h['category'])}</td>
                                <td><span class="{urg_cls}">{esc(h['urgency'])}</span></td>
                                <td><span class="badge {status_cls}">{esc(h['status'])}</span></td>
                                <td>{esc(h['reporter_name']) or '<span class="empty-cell">N/A</span>'}</td>
                                <td class="mono">{esc(h['date'])} {esc(h['time'])}</td>
                                <td>{esc(h['cause']) or '<span class="empty-cell">No details provided</span>'}</td>
                            </tr>'''

    html += f'''
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 4: INSPECTIONS -->
        <div id="tab-inspections" class="tab-panel">
            <div class="card-table">
                <div class="card-table-header">
                    <div class="table-title">Scheduled Inspections ({total_inspections})</div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Inspection ID</th>
                                <th>Inspection Name</th>
                                <th>Location</th>
                                <th>Inspector</th>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>'''
    
    for i in inspections:
        html += f'''
                            <tr>
                                <td class="mono">#{i['id']}</td>
                                <td><strong>{esc(i['title'])}</strong></td>
                                <td>{esc(i['location'])}</td>
                                <td>{esc(i['inspector'])}</td>
                                <td class="mono">{esc(i['date'])}</td>
                                <td class="mono">{esc(i['time'])}</td>
                                <td><span class="badge badge-scheduled">{esc(i['status'])}</span></td>
                            </tr>'''

    html += f'''
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 5: CONTACTS -->
        <div id="tab-contacts" class="tab-panel">
            <div class="card-table">
                <div class="card-table-header">
                    <div class="table-title">Contact Directory ({total_contacts})</div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Contact ID</th>
                                <th>Name</th>
                                <th>Position</th>
                                <th>Department</th>
                                <th>Phone</th>
                                <th>Email</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>'''
    
    for c in contacts:
        html += f'''
                            <tr>
                                <td class="mono">#{c['id']}</td>
                                <td><strong>{esc(c['name'])}</strong></td>
                                <td>{esc(c['position'])}</td>
                                <td><span class="badge badge-staff">{esc(c['department'])}</span></td>
                                <td class="mono">{esc(c['phone'])}</td>
                                <td class="mono">{esc(c['email']) or '<span class="empty-cell">N/A</span>'}</td>
                                <td><span class="badge badge-resolved">{esc(c['status'])}</span></td>
                            </tr>'''

    html += '''
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId, el) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
            
            if (el) el.classList.add('active');
            const target = document.getElementById(tabId);
            if (target) target.classList.add('active');
            
            filterActiveTable();
        }

        const searchInput = document.getElementById('db-search-input');
        function filterActiveTable() {
            if (!searchInput) return;
            const q = searchInput.value.toLowerCase().trim();
            const activePanel = document.querySelector('.tab-panel.active');
            if (!activePanel) return;

            const rows = activePanel.querySelectorAll('tbody tr');
            rows.forEach(row => {
                if (!q) {
                    row.style.display = '';
                    return;
                }
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(q) ? '' : 'none';
            });
        }

        if (searchInput) {
            searchInput.addEventListener('input', filterActiveTable);
        }
    </script>
</body>
</html>'''
    return render_template_string(html)

# ── Hazard Routes ────────────────────────────────────────
@app.route('/api/hazards')
@login_required
def list_hazards():
    status = request.args.get('status')
    urgency = request.args.get('urgency')
    search = request.args.get('search')
    page = safe_int(request.args.get('page'), default=1, min_val=1, max_val=10000)
    limit = safe_int(request.args.get('limit'), default=50, min_val=1, max_val=200)

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
@login_required
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
@login_required
def create_hazard():
    data = request.json or {}
    now = datetime.now()
    mm = f"{now.month:02d}"
    dd = f"{now.day:02d}"
    yy = str(now.year)
    
    conn = get_db()
    with conn:
        ticket = (data.get('ticket') or '').strip()
        if not ticket:
            count = conn.execute('SELECT COUNT(*) as c FROM hazards').fetchone()['c'] + 1
            ticket = f"ABC-{yy}-{mm}{dd}-{count:02d}"
            
        date_str = data.get('date') or f"{mm}-{dd}-{yy[-2:]}"
        time_str = data.get('time') or now.strftime("%I:%M %p")
        status = data.get('status') or 'Pending'
        category = data.get('category') or 'General Hazard'
        location = data.get('location') or 'Unknown Location'
        urgency = data.get('urgency') or 'Medium'
        cause = data.get('cause') or ''
        photo = data.get('photo') or ''
        
        personnel = data.get('personnel') or {}
        rep_name = personnel.get('name') or ''
        rep_pos = personnel.get('position') or ''
        rep_phone = personnel.get('phone') or ''
        rep_dept = personnel.get('dept') or ''
        
        existing = conn.execute('SELECT id FROM hazards WHERE ticket = ?', (ticket,)).fetchone()
        if existing:
            conn.execute('''
                UPDATE hazards SET location=?, category=?, date=?, time=?, urgency=?, status=?, cause=?, photo=?,
                reporter_name=?, reporter_position=?, reporter_phone=?, reporter_dept=?
                WHERE ticket = ?
            ''', (location, category, date_str, time_str, urgency, status, cause, photo,
                  rep_name, rep_pos, rep_phone, rep_dept, ticket))
        else:
            conn.execute('''
                INSERT INTO hazards (ticket, location, category, date, time, urgency, status, cause, photo,
                reporter_name, reporter_position, reporter_phone, reporter_dept)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticket, location, category, date_str, time_str, urgency, status, cause, photo,
                rep_name, rep_pos, rep_phone, rep_dept
            ))
        
        conn.execute('INSERT INTO notifications (title, time_label, unread) VALUES (?, ?, 1)', 
                     (f"New Hazard Report: {ticket} - {category}", "Just now"))

    log_activity('REPORT_HAZARD', 'SUCCESS', f"Hazard ticket {ticket} ({category}) filed at {location}")
    return jsonify({"message": "Hazard report created.", "ticket": ticket}), 201

@app.route('/api/hazards/<ticket>/resolve', methods=['PATCH'])
@manager_required
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

    log_activity('RESOLVE_HAZARD', 'SUCCESS', f"Hazard ticket {ticket} marked as RESOLVED")
    return jsonify({"message": "Hazard marked as resolved.", "ticket": ticket})

@app.route('/api/hazards/export/csv')
@manager_required
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
@login_required
def list_inspections():
    page = safe_int(request.args.get('page'), default=1, min_val=1, max_val=10000)
    limit = safe_int(request.args.get('limit'), default=50, min_val=1, max_val=200)
    
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) as c FROM inspections').fetchone()['c']
    offset = (page - 1) * limit
    
    rows = conn.execute('SELECT * FROM inspections ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    inspections = [dict(row) for row in rows]
    
    return jsonify({"inspections": inspections, "total": total, "page": page, "limit": limit})

@app.route('/api/inspections', methods=['POST'])
@manager_required
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

    log_activity('SCHEDULE_INSPECTION', 'SUCCESS', f"Inspection scheduled: {data.get('title')} at {data.get('location')} by {data.get('inspector')}")
    return jsonify({"message": "Inspection scheduled successfully.", "id": cursor.lastrowid}), 201

@app.route('/api/inspections/<int:id>', methods=['DELETE'])
@manager_required
def delete_inspection(id):
    conn = get_db()
    with conn:
        cursor = conn.execute('DELETE FROM inspections WHERE id = ?', (id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Inspection not found."}), 404

    log_activity('CANCEL_INSPECTION', 'SUCCESS', f"Inspection #{id} cancelled")
    return jsonify({"message": "Inspection cancelled."})

# ── Contact Directory Routes ─────────────────────────────
@app.route('/api/contacts', methods=['GET'])
@login_required
def list_contacts():
    conn = get_db()
    rows = conn.execute('SELECT * FROM contacts ORDER BY id DESC').fetchall()
    return jsonify({"contacts": [dict(row) for row in rows]})

@app.route('/api/contacts', methods=['POST'])
@login_required
def create_contact():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    position = (data.get('position') or '').strip()
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    dept = (data.get('dept') or data.get('department') or 'Security').strip()
    
    if not name or not phone:
        return jsonify({"error": "Contact name and phone number are required."}), 400
        
    conn = get_db()
    with conn:
        cursor = conn.execute(
            'INSERT INTO contacts (name, position, phone, email, department, status) VALUES (?, ?, ?, ?, ?, ?)',
            (name, position or 'Team Member', phone, email, dept, 'Active')
        )
        new_id = cursor.lastrowid
        
    log_activity('ADD_CONTACT', 'SUCCESS', f"Contact '{name}' ({dept}) added to directory")
    return jsonify({"message": "Contact added successfully.", "id": new_id}), 201

@app.route('/api/contacts/<id>', methods=['DELETE'])
@login_required
def delete_contact(id):
    clean_id = str(id).replace('contact-', '')
    conn = get_db()
    with conn:
        if clean_id.isdigit():
            cursor = conn.execute('DELETE FROM contacts WHERE id = ?', (int(clean_id),))
        else:
            cursor = conn.execute('DELETE FROM contacts WHERE name = ?', (id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Contact not found."}), 404

    log_activity('DELETE_CONTACT', 'SUCCESS', f"Contact #{id} deleted from directory")
    return jsonify({"message": "Contact deleted successfully."})

# ── Notification Routes ──────────────────────────────────
@app.route('/api/notifications')
@login_required
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
@login_required
def create_notification():
    title = (request.json or {}).get('title')
    if not title:
        return jsonify({"error": "Notification title is required."}), 400
        
    conn = get_db()
    with conn:
        cursor = conn.execute('INSERT INTO notifications (title, time_label, unread) VALUES (?, ?, 1)', (title, 'Just now'))
        
    return jsonify({"message": "Notification created.", "id": cursor.lastrowid}), 201

@app.route('/api/notifications/clear', methods=['POST'])
@login_required
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
