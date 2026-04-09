import os as _os

MODEM_HOST = "192.168.0.1"
MODEM_USERNAME = "admin"
MODEM_PASSWORD = "your-password-here"  # <-- fill in your modem password

# SQLite database stored next to this config file
DB_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "modem_stats.db")
