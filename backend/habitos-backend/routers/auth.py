"""
routers/auth.py — User registration, login, profile
"""

from fastapi import APIRouter, HTTPException, status, Depends
from database import get_db
from schemas import UserRegister, UserLogin, UserOut, TokenResponse
from auth_utils import hash_password, verify_password, create_token, get_current_user

router = APIRouter()

DEFAULT_TASKS = [
    ("Eat Food",     "🍽️", "meals",   3.0, True,  "high"),
    ("Drink Water",  "💧", "glasses", 8.0, True,  "high"),
    ("Mobile Usage", "📱", "hours",   3.0, False, "medium"),
    ("Played",       "⚽", "hours",   2.0, False, "low"),
    ("Homework",     "📚", "hours",   2.0, True,  "high"),
    ("Sleep",        "😴", "hours",   8.0, True,  "high"),
]

DEFAULT_REMINDERS = [
    ("Drink a glass of water", "💧", "08:00", "0,1,2,3,4,5,6", "water",  "bell"),
    ("Don't skip lunch!",      "🍽️", "12:00", "1,2,3,4,5",     "health", "chime"),
    ("Afternoon water",        "💧", "15:00", "0,1,2,3,4,5,6", "water",  "bell"),
    ("Start homework",         "📚", "17:00", "1,2,3,4,5",     "work",   "ding"),
    ("Screen-off time",        "📵", "21:30", "0,1,2,3,4,5,6", "sleep",  "bell"),
    ("Time to sleep!",         "😴", "22:00", "0,1,2,3,4,5,6", "sleep",  "chime"),
]


def _seed_user_data(conn, user_id: int):
    """Insert default tasks and reminders for a new user."""
    for name, icon, unit, limit, low_warn, priority in DEFAULT_TASKS:
        conn.execute(
            "INSERT INTO tasks(user_id,name,icon,unit,daily_limit,low_warn,priority,is_default) VALUES(?,?,?,?,?,?,?,1)",
            (user_id, name, icon, unit, limit, int(low_warn), priority),
        )
    for label, icon, time_hhmm, days, cat, sound in DEFAULT_REMINDERS:
        conn.execute(
            "INSERT INTO reminders(user_id,label,icon,time_hhmm,repeat_days,category,sound) VALUES(?,?,?,?,?,?,?)",
            (user_id, label, icon, time_hhmm, days, cat, sound),
        )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: UserRegister):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username=?", (body.username,)
        ).fetchone()
        if existing:
            raise HTTPException(400, "Username already taken")

        pw_hash = hash_password(body.password)
        cur = conn.execute(
            "INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
            (body.username, body.email, pw_hash),
        )
        user_id = cur.lastrowid
        _seed_user_data(conn, user_id)
        user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    token = create_token(user_id, body.username)
    return TokenResponse(
        access_token=token,
        user=UserOut(**dict(user_row)),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?", (body.username,)
        ).fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username or password")

    token = create_token(row["id"], row["username"])
    return TokenResponse(
        access_token=token,
        user=UserOut(**dict(row)),
    )


@router.get("/me", response_model=UserOut)
def me(current=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (current["id"],)).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return UserOut(**dict(row))


@router.put("/me/password")
def change_password(body: dict, current=Depends(get_current_user)):
    old_pw = body.get("old_password", "")
    new_pw = body.get("new_password", "")
    if len(new_pw) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    with get_db() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (current["id"],)).fetchone()
        if not row or not verify_password(old_pw, row["password_hash"]):
            raise HTTPException(401, "Old password is incorrect")
        conn.execute(
            "UPDATE users SET password_hash=?, updated_at=datetime('now') WHERE id=?",
            (hash_password(new_pw), current["id"]),
        )
    return {"message": "Password updated successfully"}
