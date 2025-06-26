import os
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime

import streamlit as st
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import bcrypt

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    uid = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='Junior')
    created_at = Column(DateTime, default=datetime.utcnow)

class UserRole(str, Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    MANAGER = "Manager"
    ADMIN = "Admin"

class PostgresAuthManager:
    """Authentication manager backed by PostgreSQL."""
    def __init__(self, database_url: str = None):
        database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/chatbot')
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def register_user(self, email: str, password: str, role: UserRole = UserRole.JUNIOR) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            if session.query(User).filter_by(email=email).first():
                return {"success": False, "error": "User already exists"}
            uid = str(uuid.uuid4())
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            user = User(uid=uid, email=email, password_hash=password_hash, role=role.value)
            session.add(user)
            session.commit()
            return {"success": True, "user_id": uid, "message": "User registered successfully"}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def login(self, email: str, password: str) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter_by(email=email).first()
            if not user:
                return {"success": False, "error": "Email not found"}
            if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                return {"success": False, "error": "Incorrect password"}
            st.session_state.user_info = {
                'uid': user.uid,
                'email': user.email,
                'role': user.role,
                'authenticated': True
            }
            return {'success': True, 'message': f'Logged in as {email}', 'user': st.session_state.user_info}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def logout(self) -> None:
        if 'user_info' in st.session_state:
            st.session_state.user_info = {'authenticated': False}

    def is_authenticated(self) -> bool:
        return st.session_state.get('user_info', {}).get('authenticated', False)

    def get_user_role(self) -> Optional[str]:
        if not self.is_authenticated():
            return None
        return st.session_state.user_info.get('role')

    def update_user_role(self, uid: str, new_role: UserRole) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter_by(uid=uid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            user.role = new_role.value
            session.commit()
            return {"success": True, "message": f"User role updated to {new_role.value}"}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def get_all_users(self) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            users = session.query(User).all()
            users_list = [{'uid': u.uid, 'email': u.email, 'role': u.role} for u in users]
            return {"success": True, "users": users_list}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def delete_user(self, uid: str) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter_by(uid=uid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            session.delete(user)
            session.commit()
            return {"success": True, "message": f"User with ID {uid} deleted"}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def has_access_to_level(self, access_level: str) -> bool:
        user_role = self.get_user_role()
        if not user_role:
            return False
        role_hierarchy = {
            UserRole.JUNIOR.value: [UserRole.JUNIOR.value],
            UserRole.SENIOR.value: [UserRole.JUNIOR.value, UserRole.SENIOR.value],
            UserRole.MANAGER.value: [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value],
            UserRole.ADMIN.value: [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value, UserRole.ADMIN.value],
        }
        return access_level in role_hierarchy.get(user_role, [])
