# HabitOS — Python Backend

A **FastAPI + SQLite** backend for the HabitOS habit tracker.  
No external database needed — everything is stored in `habitos.db`.

---

## 📁 Project Structure

```
habitos-backend/
├── main.py           ← FastAPI app entry point
├── database.py       ← SQLite setup & connection helper
├── schemas.py        ← Pydantic request/response models
├── auth_utils.py     ← Password hashing + JWT tokens
├── scheduler.py      ← Background reminder checker thread
├── requirements.txt  ← Python dependencies
├── habitos.db        ← Auto-created SQLite database
├── routers/
│   ├── auth.py       ← /api/auth  (register, login, me)
│   ├── habits.py     ← /api/habits (tasks + daily logs)
│   ├── reminders.py  ← /api/reminders (CRUD + fire/snooze)
│   └── stats.py      ← /api/stats (weekly, streaks, AI suggestions)
└── frontend/
    └── index.html    ← Drop your HabitOS-Final.html here
```

---

## 🚀 Quick Start

### 1. Install Python 3.11+

Download from https://python.org

### 2. Create a virtual environment

```bash
cd habitos-backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

The server starts at **http://localhost:8000**

### 5. View interactive API docs

Open **http://localhost:8000/docs** in your browser — you'll see every endpoint
with a "Try it out" button powered by Swagger UI.

---

## 🌐 Serve the Frontend

Copy your `HabitOS-Final.html` into a `frontend/` folder and rename it `index.html`:

```
habitos-backend/
└── frontend/
    └── index.html    ← HabitOS-Final.html renamed
```

Then open **http://localhost:8000** — the backend serves the HTML automatically.

---

## 🔑 Authentication Flow

All protected endpoints require a **Bearer token** in the `Authorization` header.

### Register a new user
```
POST /api/auth/register
{
  "username": "john",
  "email": "john@example.com",
  "password": "mypassword"
}
```

### Login
```
POST /api/auth/login
{
  "username": "john",
  "password": "mypassword"
}
```

Both return:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "john", ... }
}
```

Use the token in all subsequent requests:
```
Authorization: Bearer eyJ...
```

---

## 📡 API Reference

### Auth
| Method | Endpoint              | Description            |
|--------|-----------------------|------------------------|
| POST   | /api/auth/register    | Create account         |
| POST   | /api/auth/login       | Login & get token      |
| GET    | /api/auth/me          | Get current user       |
| PUT    | /api/auth/me/password | Change password        |

### Habits — Tasks
| Method | Endpoint                    | Description              |
|--------|-----------------------------|--------------------------|
| GET    | /api/habits/tasks           | List all tasks           |
| POST   | /api/habits/tasks           | Create custom task       |
| PUT    | /api/habits/tasks/{id}      | Update task              |
| DELETE | /api/habits/tasks/{id}      | Delete task              |

### Habits — Daily Logs
| Method | Endpoint                    | Description                          |
|--------|-----------------------------|--------------------------------------|
| GET    | /api/habits/logs/{date}     | Get all logs for a date (YYYY-MM-DD) |
| POST   | /api/habits/logs            | Create/update a single log entry     |
| POST   | /api/habits/logs/bulk       | Save entire day at once              |
| PUT    | /api/habits/logs/{id}       | Update a log entry                   |
| DELETE | /api/habits/logs/{id}       | Delete a log entry                   |
| GET    | /api/habits/logs            | List logs (with date range filter)   |

### Reminders
| Method | Endpoint                         | Description              |
|--------|----------------------------------|--------------------------|
| GET    | /api/reminders                   | List all reminders       |
| POST   | /api/reminders                   | Create reminder          |
| GET    | /api/reminders/{id}              | Get single reminder      |
| PUT    | /api/reminders/{id}              | Update reminder          |
| DELETE | /api/reminders/{id}              | Delete reminder          |
| PATCH  | /api/reminders/{id}/toggle       | Enable/disable           |
| POST   | /api/reminders/{id}/fire         | Record a reminder firing |
| POST   | /api/reminders/logs/{id}/snooze  | Snooze (default 5 min)   |
| POST   | /api/reminders/logs/{id}/dismiss | Dismiss a fired reminder |
| GET    | /api/reminders/logs/today        | See today's fired reminders |

### Stats
| Method | Endpoint                  | Description                              |
|--------|---------------------------|------------------------------------------|
| GET    | /api/stats/today          | Today's summary (score, streak, etc.)   |
| GET    | /api/stats/streak         | Current streak                           |
| GET    | /api/stats/weekly         | 7-day report with daily scores           |
| GET    | /api/stats/tasks          | Per-task analytics                       |
| GET    | /api/stats/suggestions    | AI-generated habit suggestions           |

---

## 📝 Example: Save Today's Data (Bulk)

```bash
curl -X POST http://localhost:8000/api/habits/logs/bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "log_date": "2025-02-21",
    "entries": [
      {"task_id": 1, "value": 3},
      {"task_id": 2, "value": 7},
      {"task_id": 5, "value": 2}
    ]
  }'
```

---

## 🔧 Configuration

Set these environment variables to customise behaviour:

| Variable          | Default                              | Description              |
|-------------------|--------------------------------------|--------------------------|
| HABITOS_SECRET    | habitos-super-secret-...             | JWT signing secret       |

Change the secret in production:
```bash
# Windows
set HABITOS_SECRET=my-very-secret-key-change-this

# Mac/Linux
export HABITOS_SECRET=my-very-secret-key-change-this
```

---

## ⏰ Reminder Scheduler

The background thread (`scheduler.py`) checks every minute and logs when a
reminder fires. To send **real notifications**, edit `_on_reminder_fire()` in
`scheduler.py`:

```python
def _on_reminder_fire(rem):
    # Example: send email
    send_email(user_email, subject=rem['label'], body=f"Reminder at {rem['time_hhmm']}")

    # Example: send browser push notification via web-push library
    webpush(subscription_info, data=rem['label'])
```

---

## 🛠️ VS Code Setup

1. Open the `habitos-backend/` folder in VS Code
2. Install the **Python** extension
3. Select the `venv` interpreter (`Ctrl+Shift+P` → "Python: Select Interpreter")
4. Open the terminal and run: `uvicorn main:app --reload`
5. Visit `http://localhost:8000/docs`
