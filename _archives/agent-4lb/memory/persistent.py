"""
💾 Mémoire Persistante SQLite pour Agent 4LB
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import json

class PersistentMemory:
    def __init__(self, db_path: str = None):
        from core.config import MEMORY_DB_PATH
        self.db_path = db_path or str(MEMORY_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,
                    content TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY, task TEXT, result TEXT, status TEXT,
                    iterations INTEGER, started_at TEXT, completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY, category TEXT, key TEXT UNIQUE,
                    value TEXT, confidence REAL, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY, action TEXT, error_message TEXT,
                    context TEXT, resolution TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_category ON knowledge(category);
            """)
    
    def save_message(self, session_id: str, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                        (session_id, role, content))
    
    def get_conversation(self, session_id: str, limit: int = 50) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)).fetchall()
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]
    
    def save_task(self, task: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (task, status, started_at) VALUES (?, 'running', ?)",
                (task, datetime.now().isoformat()))
            return cursor.lastrowid
    
    def complete_task(self, task_id: int, result: str, iterations: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET result = ?, status = 'completed', iterations = ?, completed_at = ? WHERE id = ?",
                (result, iterations, datetime.now().isoformat(), task_id))
    
    def fail_task(self, task_id: int, error: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET result = ?, status = 'failed', completed_at = ? WHERE id = ?",
                (error, datetime.now().isoformat(), task_id))
    
    def get_task_history(self, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT task, result, status, iterations, started_at, completed_at FROM tasks ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [{"task": r[0], "result": r[1], "status": r[2], "iterations": r[3],
                "started_at": r[4], "completed_at": r[5]} for r in rows]
    
    def save_knowledge(self, category: str, key: str, value: str, confidence: float = 1.0):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT INTO knowledge (category, key, value, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET
                value = excluded.value, confidence = excluded.confidence, updated_at = excluded.updated_at""",
                (category, key, value, confidence, now, now))
    
    def get_knowledge(self, key: str = None, category: str = None) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            if key:
                rows = conn.execute("SELECT category, key, value, confidence FROM knowledge WHERE key = ?", (key,)).fetchall()
            elif category:
                rows = conn.execute("SELECT category, key, value, confidence FROM knowledge WHERE category = ?", (category,)).fetchall()
            else:
                rows = conn.execute("SELECT category, key, value, confidence FROM knowledge ORDER BY updated_at DESC LIMIT 100").fetchall()
        return [{"category": r[0], "key": r[1], "value": r[2], "confidence": r[3]} for r in rows]
    
    def log_error(self, action: str, error_message: str, context: str = None, resolution: str = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO errors (action, error_message, context, resolution) VALUES (?, ?, ?, ?)",
                        (action, error_message, context, resolution))
    
    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            msgs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'").fetchone()[0]
            knowledge = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        return {"messages": msgs, "tasks": tasks, "completed": completed, "knowledge": knowledge}

memory = PersistentMemory()
