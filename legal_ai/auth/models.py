import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from legal_ai.database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="lawyer", nullable=False)  # admin, lawyer, auditor
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True, nullable=False)  # Safe generated filename (e.g. UUID)
    original_name = Column(String, nullable=False)                     # Original filename uploaded
    file_path = Column(String, nullable=False)                         # Absolute path on local filesystem
    file_hash = Column(String, index=True, nullable=True)             # SHA256 checksum to prevent duplicate processing
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String, default="pending", nullable=False)         # pending, processing, processed, failed

    # Relationships
    owner = relationship("User", back_populates="documents")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)    # Null if system or pre-login action
    user_email = Column(String, nullable=True)                          # Cached email for record retention
    action = Column(String, nullable=False)                             # USER_LOGIN, DOCUMENT_UPLOAD, RAG_QUERY, etc.
    target_type = Column(String, nullable=True)                         # USER, DOCUMENT, SYSTEM
    target_id = Column(String, nullable=True)                           # ID of the target resource
    details = Column(String, nullable=True)                             # JSON string or text details of action
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
