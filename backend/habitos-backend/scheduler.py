"""
scheduler.py — Background thread that checks reminders every 60 seconds
and prints/logs whecd backendn one fires. In production, connect this to push
notifications, email, or WebSocket.
"""

import threading
import time
import logging
from datetime import datetime, date
from database import get_db

logger = logging.getLogger("habitos.scheduler")
logger.setLevel(logging.INFO)

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _check_and_fire():
    """Check all enabled reminders; fire any that match current HH:MM."""
    now    = datetime.now()
    h, m   = now.hour, now.minute
    today  = now.weekday()           # Mon=0 … Sun=6
    sun0   = (today + 1) % 7         # Convert to Sun=0 … Sat=6
    today_date = date.today().isoformat()
    current_hhmm = f"{h:02d}:{m:02d}"

    try:
        with get_db() as conn:
            reminders = conn.execute(
                "SELECT * FROM reminders WHERE is_enabled=1"
            ).fetchall()

            for rem in reminders:
                if rem["time_hhmm"] != current_hhmm:
                    continue
                days = [int(d) for d in rem["repeat_days"].split(",") if d.strip()]
                if sun0 not in days:
                    continue

                # Check if already fired in the last 2 minutes (avoid double-fire)
                already = conn.execute(
                    """SELECT 1 FROM reminder_logs
                       WHERE reminder_id=?
                         AND fired_at >= datetime('now', '-2 minutes')
                       LIMIT 1""",
                    (rem["id"],),
                ).fetchone()
                if already:
                    continue

                # Fire!
                conn.execute(
                    "INSERT INTO reminder_logs(reminder_id) VALUES(?)", (rem["id"],)
                )
                logger.info(
                    "🔔 FIRED reminder #%s '%s' for user_id=%s at %s",
                    rem["id"], rem["label"], rem["user_id"], current_hhmm,
                )
                # ── Hook point: send push notification / email / WebSocket here ──
                _on_reminder_fire(rem)

    except Exception as exc:
        logger.error("Scheduler error: %s", exc)


def _on_reminder_fire(rem):
    """
    Called when a reminder fires.
    Extend this to send:
      - Email via smtplib / sendgrid
      - Push via web-push
      - WebSocket message to connected frontend
    """
    print(f"\n⏰ REMINDER FIRED → [{rem['icon']}] {rem['label']} | User #{rem['user_id']}\n")


def _scheduler_loop():
    logger.info("⏰ Reminder scheduler started")
    while not _stop_event.is_set():
        _check_and_fire()
        # Sleep until the next full minute
        sleep_secs = 60 - datetime.now().second
        _stop_event.wait(timeout=sleep_secs)
    logger.info("⏰ Reminder scheduler stopped")


def start_scheduler():
    global _scheduler_thread
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="HabitOSScheduler")
    _scheduler_thread.start()


def stop_scheduler():
    _stop_event.set()
    if _scheduler_thread:
        _scheduler_thread.join(timeout=5)
