import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

# Setup a local SQLite DB to represent "AlloyDB"
DB_PATH = os.path.join(os.path.dirname(__file__), "real_alloy_db.sqlite")


@contextmanager
def get_connection():
    """Context manager for safe database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_db():
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                start_time TEXT NOT NULL,
                end_time TEXT,
                location TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                result_json TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_tokens (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                name TEXT DEFAULT '',
                token_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


# --------------- Memory Operations ---------------

def save_to_memory(user_id: str, content: str, category: str = "general") -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory_context (user_id, content, category) VALUES (?, ?, ?)",
            (user_id, content, category),
        )
        return {"id": cursor.lastrowid, "content": content, "category": category}


def get_memory(user_id: str, category: str = None) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT id, content, category, timestamp FROM memory_context WHERE user_id = ? AND category = ? ORDER BY timestamp DESC",
                (user_id, category),
            )
        else:
            cursor.execute(
                "SELECT id, content, category, timestamp FROM memory_context WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,),
            )
        return [dict(row) for row in cursor.fetchall()]


def delete_memory(memory_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_context WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0


# --------------- Task Operations ---------------

def create_task(user_id: str, title: str, description: str = "", priority: str = "medium", due_date: str = None) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (user_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, description, priority, due_date),
        )
        return {"id": cursor.lastrowid, "title": title, "status": "open", "priority": priority}


def get_tasks(user_id: str, status: str = None) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                (user_id, status),
            )
        else:
            cursor.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
        return [dict(row) for row in cursor.fetchall()]


def update_task(task_id: int, **kwargs) -> dict:
    allowed = {"title", "description", "status", "priority", "due_date"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return {"error": "No valid fields to update"}
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        if cursor.rowcount == 0:
            return {"error": "Task not found"}
        return {"id": task_id, **updates}


def delete_task(task_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0


# --------------- Event Operations ---------------

def create_event(user_id: str, title: str, start_time: str, end_time: str = None, description: str = "", location: str = "") -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (user_id, title, description, start_time, end_time, location) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, description, start_time, end_time, location),
        )
        return {"id": cursor.lastrowid, "title": title, "start_time": start_time, "end_time": end_time}


def get_events(user_id: str) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE user_id = ? ORDER BY start_time ASC",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_event(event_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return cursor.rowcount > 0


# --------------- Notes Operations ---------------

def create_note(user_id: str, title: str, content: str = "", tags: str = "") -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (user_id, title, content, tags) VALUES (?, ?, ?, ?)",
            (user_id, title, content, tags),
        )
        return {"id": cursor.lastrowid, "title": title}


def get_notes(user_id: str, tag: str = None) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        if tag:
            cursor.execute(
                "SELECT * FROM notes WHERE user_id = ? AND tags LIKE ? ORDER BY updated_at DESC",
                (user_id, f"%{tag}%"),
            )
        else:
            cursor.execute(
                "SELECT * FROM notes WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            )
        return [dict(row) for row in cursor.fetchall()]


def update_note(note_id: int, **kwargs) -> dict:
    allowed = {"title", "content", "tags"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return {"error": "No valid fields to update"}
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [note_id]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE notes SET {set_clause} WHERE id = ?", values)
        if cursor.rowcount == 0:
            return {"error": "Note not found"}
        return {"id": note_id, **updates}


def delete_note(note_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cursor.rowcount > 0


# --------------- Workflow Log Operations ---------------

def create_workflow_log(user_id: str, workflow_name: str, steps_json: str) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workflow_logs (user_id, workflow_name, steps_json) VALUES (?, ?, ?)",
            (user_id, workflow_name, steps_json),
        )
        return {"id": cursor.lastrowid, "workflow_name": workflow_name, "status": "running"}


def complete_workflow_log(workflow_id: int, status: str, result_json: str) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE workflow_logs SET status = ?, result_json = ?, completed_at = ? WHERE id = ?",
            (status, result_json, datetime.now().isoformat(), workflow_id),
        )
        return {"id": workflow_id, "status": status}


# --------------- Health Check ---------------

def check_db_health() -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception:
        return False


# --------------- Google Token Operations ---------------

def save_google_token(user_id: str, email: str, name: str, token_json: str) -> dict:
    """Upsert a user's Google OAuth token into the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO google_tokens (user_id, email, name, token_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email=excluded.email,
                name=excluded.name,
                token_json=excluded.token_json,
                updated_at=excluded.updated_at
        """, (user_id, email, name, token_json, datetime.now().isoformat()))
        return {"user_id": user_id, "email": email, "name": name}


def get_google_token(user_id: str) -> dict | None:
    """Retrieve a user's stored Google OAuth token."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM google_tokens WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_google_token(user_id: str) -> bool:
    """Remove a user's Google token (sign out)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM google_tokens WHERE user_id = ?", (user_id,))
        return cursor.rowcount > 0


# Initialize on import
initialize_db()
