"""
routers/habits.py — Task management + daily habit logging
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from database import get_db
from schemas import (
    TaskCreate, TaskUpdate, TaskOut,
    HabitLogCreate, HabitLogUpdate, HabitLogOut,
    BulkLogCreate, DayLogOut,
)
from auth_utils import get_current_user

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calc_status(value: float, limit: float, low_warn: bool) -> str:
    if value > limit:
        return "over"
    if low_warn and value < limit:
        return "under"
    return "ok"

def _calc_score(logs: list, tasks: list) -> int:
    """0–100 productivity score from a day's logs."""
    if not logs:
        return 0
    task_map = {t["id"]: t for t in tasks}
    total, earned = 0, 0
    for log in logs:
        t = task_map.get(log["task_id"])
        if not t:
            continue
        total += 100
        v, limit, low = log["value"], t["daily_limit"], bool(t["low_warn"])
        if low:
            earned += min(100, (v / limit) * 100)
        else:
            earned += 100 if v <= limit else max(0, 100 - ((v - limit) / limit) * 100)
    return round(earned / total * 100) if total else 0

def _row_to_log_out(row, task) -> dict:
    return {
        "id":         row["id"],
        "task_id":    row["task_id"],
        "task_name":  task["name"],
        "task_icon":  task["icon"],
        "task_unit":  task["unit"],
        "task_limit": task["daily_limit"],
        "log_date":   row["log_date"],
        "value":      row["value"],
        "note":       row["note"],
        "status":     _calc_status(row["value"], task["daily_limit"], bool(task["low_warn"])),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/tasks", response_model=List[TaskOut])
def list_tasks(current=Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1 ORDER BY is_default DESC, id",
            (current["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate, current=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO tasks(user_id,name,icon,unit,daily_limit,low_warn,priority,is_default)
               VALUES(?,?,?,?,?,?,?,0)""",
            (current["id"], body.name, body.icon, body.unit,
             body.daily_limit, int(body.low_warn), body.priority),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, current["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")

        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if "low_warn" in updates:
            updates["low_warn"] = int(updates["low_warn"])
        if "is_active" in updates:
            updates["is_active"] = int(updates["is_active"])

        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id=? AND user_id=?",
                (*updates.values(), task_id, current["id"]),
            )
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, current["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")
        if row["is_default"]:
            # Soft-delete defaults; hard-delete custom tasks
            conn.execute("UPDATE tasks SET is_active=0 WHERE id=?", (task_id,))
        else:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


# ══════════════════════════════════════════════════════════════════════════════
#  DAILY LOGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/logs/{log_date}", response_model=DayLogOut)
def get_day_logs(log_date: str, current=Depends(get_current_user)):
    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
        ).fetchall()
        task_map = {t["id"]: t for t in tasks}

        logs = conn.execute(
            "SELECT * FROM habit_logs WHERE user_id=? AND log_date=?",
            (current["id"], log_date),
        ).fetchall()

    log_outs = [_row_to_log_out(l, task_map[l["task_id"]]) for l in logs if l["task_id"] in task_map]
    score = _calc_score(logs, list(task_map.values()))

    return {
        "log_date":          log_date,
        "logs":              log_outs,
        "productivity_score": score,
        "total_tasks":        len(tasks),
        "completed_tasks":    len(logs),
    }


@router.post("/logs", response_model=HabitLogOut, status_code=201)
def create_log(body: HabitLogCreate, current=Depends(get_current_user)):
    with get_db() as conn:
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND user_id=?", (body.task_id, current["id"])
        ).fetchone()
        if not task:
            raise HTTPException(404, "Task not found")

        # Upsert: update if log already exists for this date
        existing = conn.execute(
            "SELECT id FROM habit_logs WHERE user_id=? AND task_id=? AND log_date=?",
            (current["id"], body.task_id, body.log_date),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE habit_logs SET value=?,note=?,updated_at=datetime('now') WHERE id=?",
                (body.value, body.note, existing["id"]),
            )
            log_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO habit_logs(user_id,task_id,log_date,value,note) VALUES(?,?,?,?,?)",
                (current["id"], body.task_id, body.log_date, body.value, body.note),
            )
            log_id = cur.lastrowid

        log = conn.execute("SELECT * FROM habit_logs WHERE id=?", (log_id,)).fetchone()
    return _row_to_log_out(log, task)


@router.post("/logs/bulk", status_code=201)
def bulk_log(body: BulkLogCreate, current=Depends(get_current_user)):
    """Save an entire day's data at once (like the frontend 'Save Today' button)."""
    results = []
    with get_db() as conn:
        tasks = {
            t["id"]: t for t in conn.execute(
                "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
            ).fetchall()
        }
        for entry in body.entries:
            if entry.task_id not in tasks:
                continue
            existing = conn.execute(
                "SELECT id FROM habit_logs WHERE user_id=? AND task_id=? AND log_date=?",
                (current["id"], entry.task_id, body.log_date),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE habit_logs SET value=?,note=?,updated_at=datetime('now') WHERE id=?",
                    (entry.value, entry.note, existing["id"]),
                )
                log_id = existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO habit_logs(user_id,task_id,log_date,value,note) VALUES(?,?,?,?,?)",
                    (current["id"], entry.task_id, body.log_date, entry.value, entry.note),
                )
                log_id = cur.lastrowid
            log = conn.execute("SELECT * FROM habit_logs WHERE id=?", (log_id,)).fetchone()
            results.append(_row_to_log_out(log, tasks[entry.task_id]))

    return {"log_date": body.log_date, "saved": len(results), "logs": results}


@router.put("/logs/{log_id}", response_model=HabitLogOut)
def update_log(log_id: int, body: HabitLogUpdate, current=Depends(get_current_user)):
    with get_db() as conn:
        log = conn.execute(
            "SELECT * FROM habit_logs WHERE id=? AND user_id=?", (log_id, current["id"])
        ).fetchone()
        if not log:
            raise HTTPException(404, "Log not found")
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (log["task_id"],)).fetchone()

        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            conn.execute(
                f"UPDATE habit_logs SET {set_clause}, updated_at=datetime('now') WHERE id=?",
                (*updates.values(), log_id),
            )
        log = conn.execute("SELECT * FROM habit_logs WHERE id=?", (log_id,)).fetchone()
    return _row_to_log_out(log, task)


@router.delete("/logs/{log_id}", status_code=204)
def delete_log(log_id: int, current=Depends(get_current_user)):
    with get_db() as conn:
        log = conn.execute(
            "SELECT id FROM habit_logs WHERE id=? AND user_id=?", (log_id, current["id"])
        ).fetchone()
        if not log:
            raise HTTPException(404, "Log not found")
        conn.execute("DELETE FROM habit_logs WHERE id=?", (log_id,))


@router.get("/logs", response_model=List[DayLogOut])
def list_logs(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    current=Depends(get_current_user),
):
    """Return logs grouped by day for a date range."""
    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
        ).fetchall()
        task_map = {t["id"]: t for t in tasks}

        query = "SELECT * FROM habit_logs WHERE user_id=?"
        params: list = [current["id"]]
        if from_date:
            query += " AND log_date>=?"; params.append(from_date)
        if to_date:
            query += " AND log_date<=?"; params.append(to_date)
        query += " ORDER BY log_date DESC"

        all_logs = conn.execute(query, params).fetchall()

    # Group by date
    day_map: dict = {}
    for log in all_logs:
        d = log["log_date"]
        day_map.setdefault(d, []).append(log)

    result = []
    for d, logs in day_map.items():
        log_outs = [_row_to_log_out(l, task_map[l["task_id"]]) for l in logs if l["task_id"] in task_map]
        score = _calc_score(logs, list(task_map.values()))
        result.append({
            "log_date": d,
            "logs": log_outs,
            "productivity_score": score,
            "total_tasks": len(tasks),
            "completed_tasks": len(logs),
        })
    return result
