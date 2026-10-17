"""
routers/reminders.py — Reminder CRUD + fire/snooze/dismiss
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, date, timedelta
from database import get_db
from schemas import ReminderCreate, ReminderUpdate, ReminderOut
from auth_utils import get_current_user

router = APIRouter()

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_to_list(csv: str) -> List[int]:
    return [int(d) for d in csv.split(",") if d.strip().isdigit()]

def _days_to_label(days: List[int]) -> str:
    if sorted(days) == [0,1,2,3,4,5,6]:
        return "Every day"
    if sorted(days) == [1,2,3,4,5]:
        return "Weekdays"
    if sorted(days) == [0,6]:
        return "Weekends"
    return ", ".join(DAY_NAMES[d] for d in sorted(days))

def _time_to_12h(t: str) -> str:
    h, m = int(t[:2]), int(t[3:5])
    ampm = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ampm}"

def _next_occurrence(time_hhmm: str, days: List[int]) -> str:
    now = datetime.now()
    today_day = now.weekday()   # Mon=0 … Sun=6  ← Python convention
    # Convert to Sun=0 … Sat=6 convention used in the app
    today_sun0 = (today_day + 1) % 7

    h, m = int(time_hhmm[:2]), int(time_hhmm[3:5])
    rem_minutes = h * 60 + m
    now_minutes = now.hour * 60 + now.minute

    for offset in range(8):
        check_day = (today_sun0 + offset) % 7
        if check_day in days:
            if offset == 0 and rem_minutes > now_minutes:
                return f"Today at {_time_to_12h(time_hhmm)}"
            if offset == 1:
                return f"Tomorrow at {_time_to_12h(time_hhmm)}"
            return f"{DAY_NAMES[check_day]} at {_time_to_12h(time_hhmm)}"
    return "Not scheduled"

def _row_to_out(row) -> dict:
    days = _days_to_list(row["repeat_days"])
    return {
        "id":              row["id"],
        "label":           row["label"],
        "icon":            row["icon"],
        "time_hhmm":       row["time_hhmm"],
        "time_12h":        _time_to_12h(row["time_hhmm"]),
        "repeat_days":     days,
        "days_label":      _days_to_label(days),
        "category":        row["category"],
        "sound":           row["sound"],
        "note":            row["note"],
        "is_enabled":      bool(row["is_enabled"]),
        "next_occurrence": _next_occurrence(row["time_hhmm"], days) if row["is_enabled"] else None,
        "created_at":      row["created_at"],
        "updated_at":      row["updated_at"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[ReminderOut])
def list_reminders(current=Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE user_id=? ORDER BY time_hhmm",
            (current["id"],),
        ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(body: ReminderCreate, current=Depends(get_current_user)):
    days_csv = ",".join(str(d) for d in body.repeat_days)
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO reminders(user_id,label,icon,time_hhmm,repeat_days,category,sound,note,is_enabled)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (current["id"], body.label, body.icon, body.time_hhmm,
             days_csv, body.category, body.sound, body.note, int(body.is_enabled)),
        )
        row = conn.execute("SELECT * FROM reminders WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_to_out(row)


@router.get("/{rem_id}", response_model=ReminderOut)
def get_reminder(rem_id: int, current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?", (rem_id, current["id"])
        ).fetchone()
    if not row:
        raise HTTPException(404, "Reminder not found")
    return _row_to_out(row)


@router.put("/{rem_id}", response_model=ReminderOut)
def update_reminder(rem_id: int, body: ReminderUpdate, current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?", (rem_id, current["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Reminder not found")

        updates = {}
        data = body.model_dump(exclude_none=True)
        if "repeat_days" in data:
            updates["repeat_days"] = ",".join(str(d) for d in sorted(set(data.pop("repeat_days"))))
        if "is_enabled" in data:
            updates["is_enabled"] = int(data.pop("is_enabled"))
        updates.update(data)

        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            conn.execute(
                f"UPDATE reminders SET {set_clause}, updated_at=datetime('now') WHERE id=? AND user_id=?",
                (*updates.values(), rem_id, current["id"]),
            )
        row = conn.execute("SELECT * FROM reminders WHERE id=?", (rem_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{rem_id}", status_code=204)
def delete_reminder(rem_id: int, current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM reminders WHERE id=? AND user_id=?", (rem_id, current["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Reminder not found")
        conn.execute("DELETE FROM reminders WHERE id=?", (rem_id,))


@router.patch("/{rem_id}/toggle", response_model=ReminderOut)
def toggle_reminder(rem_id: int, current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?", (rem_id, current["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Reminder not found")
        new_val = 1 - row["is_enabled"]
        conn.execute(
            "UPDATE reminders SET is_enabled=?, updated_at=datetime('now') WHERE id=?",
            (new_val, rem_id),
        )
        row = conn.execute("SELECT * FROM reminders WHERE id=?", (rem_id,)).fetchone()
    return _row_to_out(row)


# ══════════════════════════════════════════════════════════════════════════════
#  FIRE / SNOOZE / DISMISS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{rem_id}/fire")
def fire_reminder(rem_id: int, current=Depends(get_current_user)):
    """Called when the frontend detects a reminder should fire (or for testing)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?", (rem_id, current["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Reminder not found")
        conn.execute(
            "INSERT INTO reminder_logs(reminder_id) VALUES(?)", (rem_id,)
        )
        log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"log_id": log_id, "message": f"Reminder '{row['label']}' logged as fired"}


@router.post("/logs/{log_id}/snooze")
def snooze_log(log_id: int, minutes: int = 5, current=Depends(get_current_user)):
    with get_db() as conn:
        log = conn.execute("SELECT * FROM reminder_logs WHERE id=?", (log_id,)).fetchone()
        if not log:
            raise HTTPException(404, "Log entry not found")
        rem = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?",
            (log["reminder_id"], current["id"]),
        ).fetchone()
        if not rem:
            raise HTTPException(403, "Not your reminder")
        conn.execute("UPDATE reminder_logs SET snoozed=1 WHERE id=?", (log_id,))
    snooze_until = (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")
    return {"message": f"Snoozed until {snooze_until}"}


@router.post("/logs/{log_id}/dismiss")
def dismiss_log(log_id: int, current=Depends(get_current_user)):
    with get_db() as conn:
        log = conn.execute("SELECT * FROM reminder_logs WHERE id=?", (log_id,)).fetchone()
        if not log:
            raise HTTPException(404, "Log entry not found")
        rem = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?",
            (log["reminder_id"], current["id"]),
        ).fetchone()
        if not rem:
            raise HTTPException(403, "Not your reminder")
        conn.execute("UPDATE reminder_logs SET dismissed=1 WHERE id=?", (log_id,))
    return {"message": "Reminder dismissed"}


@router.get("/logs/today")
def todays_reminder_log(current=Depends(get_current_user)):
    """Which reminders have fired today?"""
    today = date.today().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT rl.*, r.label, r.icon, r.time_hhmm
               FROM reminder_logs rl
               JOIN reminders r ON rl.reminder_id = r.id
               WHERE r.user_id=? AND date(rl.fired_at)=?
               ORDER BY rl.fired_at DESC""",
            (current["id"], today),
        ).fetchall()
    return [dict(r) for r in rows]
