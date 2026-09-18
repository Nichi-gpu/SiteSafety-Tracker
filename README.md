# SiteSafety Tracker

A full-stack incident and inspection management system for construction site safety.

## 🚀 Quick Start

1. **Start the Flask Server**:
   ```bash
   python server/app.py
   ```
2. **Open the Application in your browser**:
   - Main Portal: **`http://localhost:8000`** or **`http://localhost:8000/login.html`**
   - Interactive Database Viewer: **`http://localhost:8000/db-viewer`**

---

## 🔑 Default Login Accounts

You can log in using either **Username** or **Email**:

| Role | Username | Email | Password |
|---|---|---|---|
| **Manager** | `manager` | `manager@sitesafety.com` | `password123` |
| **Staff** | `andrei` | `andrei@sitesafety.com` | `password123` |
| **Admin** | `admin` | `admin@sitesafety.com` | `admin123` |

*You can also create any new account on the [Sign Up page](http://localhost:8000/signup.html).*

---

## 🗄️ How to Access and View the Database

Your data is stored in the local SQLite database at:  
`server/sitesafety.db`

### Method 1: Built-in Live Web DB Viewer (Easiest — No Install Needed!)
With the server running, simply navigate to:
👉 **`http://localhost:8000/db-viewer`**

This displays:
- **Users Table**: IDs, usernames, emails, roles, companies, signup timestamps, latest login timestamps, and total login counts.
- **Login Audit Logs**: Complete record of every login, signup, and failed attempt with timestamps, IP addresses, and statuses.
- **Hazards & Inspections**: Real-time safety data.

### Method 2: Inside VS Code (SQLite Viewer Extension)
1. In VS Code, click the **Extensions** icon on the left sidebar (or press `Ctrl + Shift + X`).
2. Search for **"SQLite Viewer"** (by Florian Kohnhäuser).
3. Click **Install**.
4. In your file tree, click on `server/sitesafety.db` — it will open as an interactive table directly inside VS Code!

### Method 3: DB Browser for SQLite (GUI Desktop App)
1. Download the free tool from [sqlitebrowser.org](https://sqlitebrowser.org/).
2. Open DB Browser, click **"Open Database"**, and select `server/sitesafety.db`.
3. Browse, edit, and query any table visually.

### Method 4: Via Terminal (Quick Python One-Liner)
To print all registered users and their login times:
```bash
python -c "import sqlite3; conn = sqlite3.connect('server/sitesafety.db'); conn.row_factory = sqlite3.Row; print([{k: r[k] for k in r.keys() if k != 'password'} for r in conn.execute('SELECT * FROM users').fetchall()])"
```

---

## 📊 Database Schema Summary

### 1. `users` Table
Stores registered accounts with security and timestamp auditing:
- `id`: Unique user ID (Auto-increment)
- `username`: User display/login handle (e.g. `andrei`, `manager`)
- `email`: User email address (Unique)
- `password`: Securely hashed with `bcrypt` (never plain text)
- `role`: `'manager'` or `'staff'`
- `company`: Company or organization name
- `signup_time`: Exact date and time the account was registered
- `last_login_time`: Date and time of the user's most recent login
- `login_count`: Cumulative number of successful logins

### 2. `login_logs` Table
Complete audit trail for security and monitoring:
- `id`: Log entry ID
- `user_id`: Reference to user ID
- `username` & `email`: Identity used in the attempt
- `action`: `LOGIN`, `SIGNUP`, `FAILED_LOGIN`, or `LOGOUT`
- `status`: `SUCCESS` or `FAILED`
- `timestamp`: Date and time of the event
- `ip_address`: Client IP address
- `details`: Descriptive event outcome

### 3. `hazards` Table
Incident and hazard tickets (`ticket`, `location`, `category`, `urgency`, `status`, `cause`, `photo`, `reporter_*`, `resolved_date`).

### 4. `inspections` Table
Safety audits and site walks (`title`, `location`, `inspector`, `date`, `time`, `status`).

---

## 🔌 API Endpoints Reference

- **Auth**:
  - `POST /api/auth/signup` - Register account with username, email, password, role, company
  - `POST /api/auth/login` - Authenticate with email or username + password
  - `POST /api/auth/logout` - End session
  - `GET /api/auth/me` - Fetch authenticated user profile
- **Admin**:
  - `GET /api/admin/users` - Fetch all users and timestamps
  - `GET /api/admin/login-logs` - Fetch login activity audit trail
- **Hazards**:
  - `GET /api/hazards` - List & search hazards (supports filters)
  - `POST /api/hazards` - File new incident report
  - `PATCH /api/hazards/<ticket>/resolve` - Mark hazard as resolved
  - `GET /api/hazards/export/csv` - Download CSV report
- **Inspections & Notifications**:
  - `GET /api/inspections`, `POST /api/inspections`, `DELETE /api/inspections/<id>`
  - `GET /api/notifications`, `POST /api/notifications`, `POST /api/notifications/clear`
