import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ChatHistoryService:
    def __init__(self, db_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = db_path or os.path.join(base_dir, "data", "chat_history.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    suggestions_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at)"
            )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row_to_session(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "subject": row["subject"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_message(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "sources": json.loads(row["sources_json"] or "[]"),
            "suggested_questions": json.loads(row["suggestions_json"] or "[]"),
            "created_at": row["created_at"],
        }

    def create_session(self, user_id: str, subject: str, title: str = None) -> Dict[str, Any]:
        now = self._now()
        session_id = str(uuid.uuid4())
        clean_title = (title or "New chat").strip()[:80] or "New chat"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, user_id, title, subject, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, clean_title, subject, now, now),
            )
        return self.get_session(session_id, user_id)

    def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def get_or_create_session(
        self,
        user_id: str,
        subject: str,
        session_id: str = None,
        title_seed: str = None,
    ) -> Dict[str, Any]:
        if session_id:
            existing = self.get_session(session_id, user_id)
            if existing:
                if existing["subject"] != subject:
                    self.update_session(session_id, user_id, subject=subject)
                    existing = self.get_session(session_id, user_id)
                return existing
        return self.create_session(user_id, subject, title=title_seed)

    def list_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        user_id: str,
        title: str = None,
        subject: str = None,
    ) -> Optional[Dict[str, Any]]:
        existing = self.get_session(session_id, user_id)
        if not existing:
            return None

        next_title = (title.strip()[:80] if title else existing["title"]) or existing["title"]
        next_subject = subject or existing["subject"]
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE chat_sessions
                SET title = ?, subject = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (next_title, next_subject, now, session_id, user_id),
            )
        return self.get_session(session_id, user_id)

    def delete_session(self, session_id: str, user_id: str) -> bool:
        if not self.get_session(session_id, user_id):
            return False
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
        return True

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: List[Dict[str, Any]] = None,
        suggested_questions: List[str] = None,
    ) -> Dict[str, Any]:
        now = self._now()
        message_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages
                    (id, session_id, role, content, sources_json, suggestions_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    content,
                    json.dumps(sources or [], ensure_ascii=False),
                    json.dumps(suggested_questions or [], ensure_ascii=False),
                    now,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        return self.get_message(message_id)

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_messages WHERE id = ?",
                (message_id,),
            ).fetchone()
        return self._row_to_message(row) if row else None

    def list_messages(self, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        if not self.get_session(session_id, user_id):
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]
