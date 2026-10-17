"""
database.py — SQLite setup using built-in sqlite3
Tables: users, tasks, habit_logs, reminders, reminder_logs
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "habitos.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager — auto-commits or rolls back."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables on first run."""
    with get_db() as conn:
        conn.executescript("""
        -- ── Users ────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            email       TEXT    UNIQUE,
            password_hash TEXT  NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        );

        -- ── Tasks (habit definitions) ─────────────────────────────
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name        TEXT    NOT NULL,
            icon        TEXT    NOT NULL DEFAULT '⭐',
            unit        TEXT    NOT NULL DEFAULT 'units',
            daily_limit REAL    NOT NULL DEFAULT 1.0,
            low_warn    INTEGER NOT NULL DEFAULT 1,   -- 1=warn if below, 0=warn if above
            priority    TEXT    NOT NULL DEFAULT 'medium',
            is_default  INTEGER NOT NULL DEFAULT 0,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        -- ── Daily habit logs ──────────────────────────────────────
        CREATE TABLE IF NOT EXISTS habit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            log_date    TEXT    NOT NULL,   -- YYYY-MM-DD
            value       REAL    NOT NULL,
            note        TEXT,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now')),
            UNIQUE(user_id, task_id, log_date)
        );

        -- ── Reminders ────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label       TEXT    NOT NULL,
            icon        TEXT    NOT NULL DEFAULT '🔔',
            time_hhmm   TEXT    NOT NULL,          -- HH:MM (24h)
            repeat_days TEXT    NOT NULL DEFAULT '0,1,2,3,4,5,6',  -- CSV of day numbers
            category    TEXT    NOT NULL DEFAULT 'custom',
            sound       TEXT    NOT NULL DEFAULT 'bell',
            note        TEXT,
            is_enabled  INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        );

        -- ── Reminder fire log (tracks what has already fired today) ─
        CREATE TABLE IF NOT EXISTS reminder_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder_id  INTEGER NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
            fired_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            snoozed      INTEGER NOT NULL DEFAULT 0,
            dismissed    INTEGER NOT NULL DEFAULT 0
        );

        -- ── Indexes ───────────────────────────────────────────────
        CREATE INDEX IF NOT EXISTS idx_habit_logs_user_date   ON habit_logs(user_id, log_date);
        CREATE INDEX IF NOT EXISTS idx_habit_logs_task        ON habit_logs(task_id);
        CREATE INDEX IF NOT EXISTS idx_reminders_user_enabled ON reminders(user_id, is_enabled);
        CREATE INDEX IF NOT EXISTS idx_reminder_logs_date     ON reminder_logs(reminder_id, fired_at);
        """)

    print("✅ Database initialised →", DB_PATH)
