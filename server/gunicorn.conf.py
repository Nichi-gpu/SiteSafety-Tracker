import os

# Render and other cloud platforms provide the port via the PORT environment variable.
# Default to port 8000 for local execution.
port = os.environ.get("PORT", "8000")
bind = f"0.0.0.0:{port}"

# Recommended configuration for single-container Flask + SQLite:
# 1 worker with 4 threads ensures thread concurrency while avoiding SQLite multi-process locking.
workers = 1
threads = 4
timeout = 120
