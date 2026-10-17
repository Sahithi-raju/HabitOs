"""
routers/stats.py — Streak, weekly report, productivity, AI suggestions
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import date, timedelta
from database import get_db
from schemas import WeeklyStatOut, TaskStatOut, AISuggestionOut
from auth_utils import get_current_user

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_day(logs, tasks) -> int:
    task_map = {t["id"]: t for t in tasks}
    total = earned = 0
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

def _get_streak(conn, user_id: int) -> int:
    streak = 0
    check = date.today()
    while True:
        has = conn.execute(
            "SELECT 1 FROM habit_logs WHERE user_id=? AND log_date=? LIMIT 1",
            (user_id, check.isoformat()),
        ).fetchone()
        if has:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


# ══════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/streak")
def get_streak(current=Depends(get_current_user)):
    with get_db() as conn:
        streak = _get_streak(conn, current["id"])
    return {"streak": streak, "message": f"🔥 {streak}-day streak!" if streak > 0 else "No streak yet."}


@router.get("/weekly", response_model=WeeklyStatOut)
def weekly_report(
    week_offset: int = Query(0, description="0=this week, 1=last week, etc."),
    current=Depends(get_current_user),
):
    """Return stats for a 7-day window."""
    today = date.today()
    end   = today - timedelta(days=week_offset * 7)
    start = end - timedelta(days=6)

    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
        ).fetchall()
        logs  = conn.execute(
            "SELECT * FROM habit_logs WHERE user_id=? AND log_date BETWEEN ? AND ?",
            (current["id"], start.isoformat(), end.isoformat()),
        ).fetchall()
        streak = _get_streak(conn, current["id"])

    # Group logs by date
    day_logs: dict = {}
    for log in logs:
        day_logs.setdefault(log["log_date"], []).append(log)

    daily_scores = []
    for offset in range(7):
        d = (start + timedelta(days=offset)).isoformat()
        dl = day_logs.get(d, [])
        score = _score_day(dl, tasks)
        daily_scores.append({"date": d, "score": score, "logged": len(dl)})

    scored = [(ds["date"], ds["score"]) for ds in daily_scores if ds["logged"] > 0]
    avg = round(sum(s for _, s in scored) / len(scored)) if scored else 0
    best  = max(scored, key=lambda x: x[1])[0] if scored else None
    worst = min(scored, key=lambda x: x[1])[0] if scored else None

    return {
        "week_start":         start.isoformat(),
        "week_end":           end.isoformat(),
        "days_logged":        len(scored),
        "avg_productivity":   avg,
        "streak":             streak,
        "best_day":           best,
        "worst_day":          worst,
        "daily_scores":       daily_scores,
    }


@router.get("/tasks", response_model=List[TaskStatOut])
def task_stats(
    days: int = Query(7, ge=1, le=90),
    current=Depends(get_current_user),
):
    """Per-task analytics over the last N days."""
    end   = date.today()
    start = end - timedelta(days=days - 1)

    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
        ).fetchall()
        logs  = conn.execute(
            """SELECT task_id, value, log_date
               FROM habit_logs
               WHERE user_id=? AND log_date BETWEEN ? AND ?
               ORDER BY log_date""",
            (current["id"], start.isoformat(), end.isoformat()),
        ).fetchall()

    log_by_task: dict = {}
    for log in logs:
        log_by_task.setdefault(log["task_id"], []).append(log)

    result = []
    for task in tasks:
        tl = log_by_task.get(task["id"], [])
        if not tl:
            continue
        values = [l["value"] for l in tl]
        avg    = round(sum(values) / len(values), 2)
        limit  = task["daily_limit"]
        low    = bool(task["low_warn"])
        on_target = sum(
            1 for v in values
            if (low and v >= limit) or (not low and v <= limit)
        )

        # Simple trend: compare first half vs second half
        half = len(values) // 2
        if half > 0:
            first_avg  = sum(values[:half]) / half
            second_avg = sum(values[half:]) / max(len(values[half:]), 1)
            diff = second_avg - first_avg
            trend = "improving" if (low and diff > 0.1) or (not low and diff < -0.1) \
                    else "declining" if (low and diff < -0.1) or (not low and diff > 0.1) \
                    else "stable"
        else:
            trend = "stable"

        result.append({
            "task_id":        task["id"],
            "task_name":      task["name"],
            "task_icon":      task["icon"],
            "avg_value":      avg,
            "days_logged":    len(tl),
            "days_on_target": on_target,
            "compliance_pct": round(on_target / len(tl) * 100),
            "trend":          trend,
        })

    return result


@router.get("/suggestions", response_model=List[AISuggestionOut])
def ai_suggestions(
    days: int = Query(3, ge=2, le=14),
    current=Depends(get_current_user),
):
    """AI-style habit suggestions based on recent logs."""
    end   = date.today() - timedelta(days=1)   # yesterday backwards
    start = end - timedelta(days=days - 1)

    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
        ).fetchall()
        logs  = conn.execute(
            """SELECT task_id, value
               FROM habit_logs
               WHERE user_id=? AND log_date BETWEEN ? AND ?""",
            (current["id"], start.isoformat(), end.isoformat()),
        ).fetchall()

    log_by_task: dict = {}
    for log in logs:
        log_by_task.setdefault(log["task_id"], []).append(log["value"])

    suggestions = []
    for task in tasks:
        tl = log_by_task.get(task["id"], [])
        if len(tl) < 2:
            continue
        avg   = sum(tl) / len(tl)
        limit = task["daily_limit"]
        low   = bool(task["low_warn"])
        n     = len(tl)

        if not low and avg > limit:
            suggestions.append({
                "type":            "warning",
                "icon":            task["icon"],
                "title":           f"Reduce {task['name']}",
                "message":         f"Your avg {task['name'].lower()} is {avg:.1f} {task['unit']} over {n} days (limit: {limit}). Try to cut back.",
                "tomorrow_target": f"Reduce to {limit} {task['unit']}",
                "task_id":         task["id"],
            })
        elif low and avg < limit:
            suggestions.append({
                "type":            "warning",
                "icon":            task["icon"],
                "title":           f"Increase {task['name']}",
                "message":         f"Avg is only {avg:.1f} {task['unit']} over {n} days. Aim for {limit}.",
                "tomorrow_target": f"Target {limit} {task['unit']}",
                "task_id":         task["id"],
            })
        elif low and all(v >= limit for v in tl):
            suggestions.append({
                "type":            "success",
                "icon":            task["icon"],
                "title":           f"Great {task['name']} Habit!",
                "message":         f"You've hit your {task['name'].lower()} goal every day for {n} days. Keep it up!",
                "tomorrow_target": f"Maintain {limit}+ {task['unit']}",
                "task_id":         task["id"],
            })

    return suggestions


@router.get("/today")
def today_summary(current=Depends(get_current_user)):
    """Quick dashboard summary for today."""
    today = date.today().isoformat()
    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND is_active=1", (current["id"],)
        ).fetchall()
        logs  = conn.execute(
            "SELECT * FROM habit_logs WHERE user_id=? AND log_date=?",
            (current["id"], today),
        ).fetchall()
        reminders_today = conn.execute(
            """SELECT COUNT(*) AS cnt FROM reminders
               WHERE user_id=? AND is_enabled=1""",
            (current["id"],),
        ).fetchone()["cnt"]
        streak = _get_streak(conn, current["id"])

    score = _score_day(logs, tasks)
    return {
        "date":              today,
        "productivity_score": score,
        "streak":            streak,
        "tasks_total":       len(tasks),
        "tasks_logged":      len(logs),
        "reminders_active":  reminders_today,
        "completion_pct":    round(len(logs) / len(tasks) * 100) if tasks else 0,
    }
