#!/usr/bin/env python3
"""Chat History Manager using a local SQLite database."""

import sqlite3
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: datetime
    message_id: str | None = None


@dataclass
class ChatSession:
    session_id: str
    user_email: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage]
    is_active: bool = True


class ChatHistoryManager:
    """Manages chat history storage using SQLite."""

    def __init__(self, db_path: str = "./chat_history.db") -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_email TEXT,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                is_active INTEGER
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            )"""
        )
        self.conn.commit()

    def create_new_session(self, user_email: str, initial_message: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        title = self._generate_title(initial_message) if initial_message else f"New Chat - {now.strftime('%m/%d %H:%M')}"
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO sessions(session_id, user_email, title, created_at, updated_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            (session_id, user_email, title, now.isoformat(), now.isoformat()),
        )
        if initial_message:
            self.add_message(session_id, "user", initial_message)
        self.conn.commit()
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        now = datetime.utcnow()
        message_id = str(uuid.uuid4())
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO messages(message_id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (message_id, session_id, role, content, now.isoformat()),
        )
        cur.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now.isoformat(), session_id),
        )
        self.conn.commit()
        return True

    def get_user_sessions(self, user_email: str, limit: int = 50) -> List[ChatSession]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM sessions WHERE user_email=? AND is_active=1 ORDER BY updated_at DESC LIMIT ?",
            (user_email, limit),
        )
        rows = cur.fetchall()
        sessions: List[ChatSession] = []
        for row in rows:
            sessions.append(
                ChatSession(
                    session_id=row["session_id"],
                    user_email=row["user_email"],
                    title=row["title"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    messages=self.get_session_messages(row["session_id"]),
                    is_active=row["is_active"] == 1,
                )
            )
        return sessions

    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY timestamp",
            (session_id,),
        )
        rows = cur.fetchall()
        return [
            ChatMessage(
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                message_id=row["message_id"],
            )
            for row in rows
        ]

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        return ChatSession(
            session_id=row["session_id"],
            user_email=row["user_email"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            messages=self.get_session_messages(row["session_id"]),
            is_active=row["is_active"] == 1,
        )

    def delete_session(self, session_id: str, user_email: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE sessions SET is_active=0 WHERE session_id=? AND user_email=?",
            (session_id, user_email),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def update_session_title(self, session_id: str, new_title: str, user_email: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE sessions SET title=?, updated_at=? WHERE session_id=? AND user_email=?",
            (new_title, datetime.utcnow().isoformat(), session_id, user_email),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def get_stats(self, user_email: str) -> Dict[str, Any]:
        sessions = self.get_user_sessions(user_email, limit=1000)
        total_sessions = len(sessions)
        total_messages = sum(len(s.messages) for s in sessions)
        avg_messages = total_messages / total_sessions if total_sessions else 0
        most_recent = sessions[0].updated_at if sessions else None
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": round(avg_messages, 1),
            "most_recent_session": most_recent,
        }

    def _generate_title(self, message: Optional[str], max_length: int = 50) -> str:
        if not message:
            return f"Chat - {datetime.now().strftime('%m/%d %H:%M')}"
        title = (
            message.strip()
            .replace("what is", "")
            .replace("how do", "")
            .replace("can you", "")
            .replace("tell me", "")
            .replace("explain", "")
            .strip()
        )
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        if len(title) > max_length:
            title = title[: max_length - 3] + "..."
        if len(title) < 3:
            title = f"Chat - {datetime.now().strftime('%m/%d %H:%M')}"
        return title
