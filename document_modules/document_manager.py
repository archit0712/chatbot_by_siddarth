import os
import uuid
from typing import Dict, List, Any, BinaryIO, Optional
from enum import Enum
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from werkzeug.utils import secure_filename

from core.postgres_auth import UserRole

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    min_access_level = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    uploaded_by = Column(String, nullable=False)
    uploader_email = Column(String, nullable=False)
    tags = Column(String)
    file_path = Column(String, nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)

class DocumentType(str, Enum):
    POLICY = "Policy"
    FINANCIAL = "Financial"
    HR = "HR"
    PROJECT = "Project"
    GENERAL = "General"
    OTHER = "Other"

class DocumentManager:
    """Manage document storage using PostgreSQL and local files."""

    def __init__(self, database_url: str = None, storage_dir: str = "./documents"):
        database_url = database_url or os.getenv("DATABASE_URL", "postgresql://user:password@localhost/chatbot_db")
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)

    def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        title: str,
        description: str,
        min_access_level: UserRole,
        document_type: DocumentType,
        user: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Save document to disk and record metadata in PostgreSQL."""
        session = self.SessionLocal()
        try:
            doc_id = str(uuid.uuid4())
            secure_name = f"{doc_id}_{secure_filename(filename)}"
            file_path = self.storage_dir / secure_name
            with open(file_path, "wb") as f:
                f.write(file.read())

            doc = Document(
                id=doc_id,
                title=title,
                description=description,
                min_access_level=min_access_level.value,
                document_type=document_type.value,
                uploaded_by=user.get("uid", ""),
                uploader_email=user.get("email", ""),
                tags=",".join(tags or []),
                file_path=str(file_path),
            )
            session.add(doc)
            session.commit()
            return {"success": True, "document_id": doc_id}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def _role_access_levels(self, user_role: UserRole) -> List[str]:
        if user_role == UserRole.JUNIOR:
            return [UserRole.JUNIOR.value]
        if user_role == UserRole.SENIOR:
            return [UserRole.JUNIOR.value, UserRole.SENIOR.value]
        if user_role in [UserRole.MANAGER, UserRole.ADMIN]:
            return [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value]
        return []

    def get_accessible_documents(self, user_role: UserRole) -> List[Dict[str, Any]]:
        """Return documents accessible to the given role."""
        session = self.SessionLocal()
        try:
            levels = self._role_access_levels(user_role)
            docs = session.query(Document).filter(Document.min_access_level.in_(levels)).all()
            return [self._doc_to_dict(d) for d in docs]
        except Exception:
            return []
        finally:
            session.close()

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Return all documents for admin view."""
        session = self.SessionLocal()
        try:
            docs = session.query(Document).order_by(Document.upload_timestamp.desc()).all()
            return [self._doc_to_dict(d) for d in docs]
        finally:
            session.close()

    def get_document_content(self, document_id: str, user_role: UserRole) -> Dict[str, Any]:
        """Return document metadata if accessible."""
        session = self.SessionLocal()
        try:
            doc = session.query(Document).filter_by(id=document_id).first()
            if not doc:
                return {"success": False, "error": "Document not found"}
            if doc.min_access_level not in self._role_access_levels(user_role) and user_role != UserRole.ADMIN:
                return {"success": False, "error": "Access denied. Insufficient permissions."}
            return {"success": True, "document": self._doc_to_dict(doc)}
        finally:
            session.close()

    def delete_document(self, document_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a document if user is owner or admin."""
        session = self.SessionLocal()
        logs: List[str] = []
        try:
            doc = session.query(Document).filter_by(id=document_id).first()
            if not doc:
                logs.append(f"Document {document_id} not found")
                return {"success": False, "error": "Document not found", "logs": logs}

            if user.get("uid") != doc.uploaded_by and user.get("role") != UserRole.ADMIN.value:
                logs.append("Permission denied")
                return {"success": False, "error": "Permission denied", "logs": logs}

            from core.database import VectorDatabase
            vector_db = VectorDatabase()
            chunk_count = vector_db.get_document_chunk_count(document_id)
            if chunk_count:
                vector_db.delete_document_chunks(document_id)
                logs.append(f"Deleted {chunk_count} vector chunks")
            file_deleted = False
            try:
                os.remove(doc.file_path)
                file_deleted = True
            except FileNotFoundError:
                logs.append("File not found during deletion")
            session.delete(doc)
            session.commit()
            msg = "Document deleted"
            if not file_deleted:
                msg += " (metadata removed, file missing)"
            logs.append(msg)
            return {"success": True, "message": msg, "logs": logs}
        except Exception as e:
            session.rollback()
            logs.append(str(e))
            return {"success": False, "error": str(e), "logs": logs}
        finally:
            session.close()

    @staticmethod
    def _doc_to_dict(doc: Document) -> Dict[str, Any]:
        return {
            "id": doc.id,
            "title": doc.title,
            "description": doc.description,
            "min_access_level": doc.min_access_level,
            "document_type": doc.document_type,
            "uploaded_by": doc.uploaded_by,
            "uploader_email": doc.uploader_email,
            "tags": (doc.tags.split(",") if doc.tags else []),
            "file_path": doc.file_path,
            "upload_timestamp": doc.upload_timestamp,
        }
