"""
database.py
-----------
Handles all SQLite database setup and low-level connection logic for the
Community Skill Exchange Platform (SkillSwap).

College requirement demonstrated: SQLite persistence (no hardcoded data).
All application data (users, offers, requests, exchanges, ratings,
notifications) lives in skill_exchange.db and is created automatically
the first time the app runs.
"""

import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill_exchange.db")


def get_connection():
    """Return a new SQLite connection with rows accessible as dictionaries."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    # Enforce foreign keys (off by default in SQLite)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create all required tables if they do not already exist.
    Safe to call every time the application starts.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT,
            points REAL DEFAULT 0,
            rating REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS SKILL_OFFERS (
            offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            category TEXT,
            difficulty TEXT NOT NULL,       -- Basic / Intermediate / Advanced
            duration REAL NOT NULL,         -- hours
            mode TEXT NOT NULL,             -- Online / Offline / Both
            available_days TEXT,
            available_time TEXT,
            points REAL NOT NULL,           -- auto-calculated via SymPy
            approval_status TEXT DEFAULT 'pending',  -- pending / approved / rejected
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS SKILL_REQUESTS (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            category TEXT,
            duration REAL NOT NULL,
            mode TEXT NOT NULL,
            location TEXT,
            available_days TEXT,
            available_time TEXT,
            status TEXT DEFAULT 'open',     -- open / matched / closed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS EXCHANGES (
            exchange_id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            offer_id INTEGER,
            skill TEXT NOT NULL,
            duration REAL NOT NULL,
            points REAL NOT NULL,
            status TEXT DEFAULT 'Pending',  -- Pending / Accepted / Rejected / Completed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            FOREIGN KEY (requester_id) REFERENCES USERS(user_id),
            FOREIGN KEY (provider_id) REFERENCES USERS(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS RATINGS (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            reviewed_user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            feedback TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exchange_id) REFERENCES EXCHANGES(exchange_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS NOTIFICATIONS (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'unread',   -- unread / read
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        )
    """)

    # Small extra table so the moderator "Reports" tab has something real
    # to query (kept intentionally simple for the 50% prototype).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS REPORTS (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reported_user_id INTEGER NOT NULL,
            reporter_id INTEGER,
            reason TEXT,
            status TEXT DEFAULT 'open',     -- open / resolved
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Allows: python database.py  -> just creates the .db file and tables
    init_db()
    print(f"Database initialized at {DB_NAME}")
