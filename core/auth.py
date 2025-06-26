"""Simple authentication manager backed by SQLite."""

import sqlite3
import hashlib
import uuid
from enum import Enum
from typing import Dict, Optional, Any
import streamlit as st


class UserRole(str, Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    MANAGER = "Manager"
    ADMIN = "Admin"


class AuthenticationManager:
    """Handle user registration and login using a local SQLite database."""

    def __init__(self, db_path: str = "./auth.db") -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT
            )"""
        )
        self.conn.commit()

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, email: str, password: str, role: UserRole = UserRole.JUNIOR) -> Dict[str, Any]:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users(id, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), email, self._hash_password(password), role.value),
            )
            self.conn.commit()
            return {"success": True, "message": "User registered"}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Email already registered"}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        if not row or row["password_hash"] != self._hash_password(password):
            return {"success": False, "error": "Invalid credentials"}
        st.session_state.user_info = {
            "uid": row["id"],
            "email": row["email"],
            "role": row["role"],
            "authenticated": True,
        }
        return {"success": True, "user": st.session_state.user_info}

    def logout(self) -> None:
        st.session_state.user_info = {"authenticated": False}

    def is_authenticated(self) -> bool:
        return st.session_state.get("user_info", {}).get("authenticated", False)

    def get_user_role(self) -> Optional[str]:
        if not self.is_authenticated():
            return None
        return st.session_state.user_info.get("role")
