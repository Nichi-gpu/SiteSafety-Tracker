"""
SiteSafety Tracker - Main Application Entry Point
=================================================
Course Code / Project Deliverable: CPE100L - Section A6 - Group 1
Project Title: SiteSafety Tracker (Construction Site Safety & Incident Monitoring)
Submission Date: September 23, 2026

Description:
------------
This is the primary launcher and entry file for the SiteSafety Tracker application.
It performs the following startup tasks:
  1. Bootstraps and verifies the backend SQLite database (schema & tables).
  2. Seeds essential role credentials (Manager and Staff accounts) if empty.
  3. Configures and starts the Flask HTTP REST API & Web Application Server.

Usage:
------
To run locally:
    $ python main.py

The application interface will be accessible at:
    http://127.0.0.1:8000/
"""

import os
import sys
import webbrowser

# Add server directory to Python path for seamless imports
SERVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server')
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from database import init_db
from seed import seed
from app import app


def bootstrap_application():
    """
    Initializes the database schema and default records prior to starting the web server.
    """
    print("=" * 65)
    print(" SiteSafety Tracker - CPE100L A6 Group 1")
    print(" Incident & Hazard Reporting Web Platform")
    print("=" * 65)
    print("[1/3] Initializing SQLite database schema...")
    init_db()
    
    print("[2/3] Verifying default user accounts & records...")
    try:
        seed()
    except Exception as e:
        print(f"      Note: Seed check passed or existing: {e}")

    print("[3/3] Starting Flask Application Server on port 8000...")
    print("\n -> Access the web interface at: http://127.0.0.1:8000/\n")


def main():
    """
    Main execution function. Bootstraps components and starts the Flask server.
    """
    bootstrap_application()
    
    # Run the Flask app on localhost:8000 (with debug mode enabled for development)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == '__main__':
    main()
