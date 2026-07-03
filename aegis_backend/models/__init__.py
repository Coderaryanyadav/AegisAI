# SQLAlchemy Models package initialization
from .base import Base, EncryptedText
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="lawyer", nullable=False)
    firm_logo = Column(Text, nullable=True)
    firm_name = Column(String, nullable=True)
    gst_rate = Column(Numeric(5, 2), default=18.0, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    is_disabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    notes = Column(EncryptedText, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    
    matters = relationship("Matter", back_populates="client", cascade="all, delete-orphan")

class Matter(Base):
    __tablename__ = "matters"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    case_number = Column(String, index=True, nullable=True)
    title = Column(String, nullable=False)
    court = Column(String, nullable=True)
    judge = Column(String, nullable=True)
    opponent_name = Column(String, nullable=True)
    opposing_advocate = Column(String, nullable=True)
    status = Column(String, default="open", nullable=False)
    facts = Column(EncryptedText, nullable=True)
    cnr_number = Column(String, nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    hmac_signature = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    client = relationship("Client", back_populates="matters")
    schedules = relationship("Schedule", back_populates="matter", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="matter")

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=False)
    schedule_type = Column(String, nullable=False)
    target_date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    matter = relationship("Matter", back_populates="schedules")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="SET NULL"), index=True, nullable=True)
    original_name = Column(String, nullable=False)
    stored_uuid = Column(String, unique=True, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    status = Column(String, default="uploaded", nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    matter = relationship("Matter", back_populates="documents")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    details = Column(Text, nullable=True)
    entry_hash = Column(String, nullable=True)

class BackupHistory(Base):
    __tablename__ = "backup_history"
    id = Column(Integer, primary_key=True, index=True)
    backup_name = Column(String, nullable=False)
    backup_size_bytes = Column(Integer, nullable=False)
    destination_path = Column(String, nullable=False)
    is_manual = Column(Boolean, default=True, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    error_message = Column(Text, nullable=True)

class BareActSection(Base):
    __tablename__ = "bare_act_sections"
    id = Column(Integer, primary_key=True, index=True)
    act = Column(String, index=True, nullable=False)
    section = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="CASCADE"), index=True, nullable=False)
    user_email = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    hours = Column(Numeric(10, 2), nullable=False)
    rate_per_hour = Column(Numeric(10, 2), nullable=False, default=5000.0)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="CASCADE"), index=True, nullable=True)
    invoice_number = Column(String, unique=True, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    gst_amount = Column(Numeric(10, 2), nullable=False)
    grand_total = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="unpaid")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    user_email = Column(String, nullable=False)
    selected_text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    color = Column(String, default="yellow")
    page_hint = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class TwoFactorSecret(Base):
    __tablename__ = "two_factor_secrets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    totp_secret = Column(EncryptedText, nullable=False)
    is_enabled = Column(Boolean, default=False)
    recovery_codes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class StatutoryMapping(Base):
    __tablename__ = "statutory_mappings"
    id = Column(Integer, primary_key=True, index=True)
    old_act = Column(String, index=True, nullable=False)
    old_section = Column(String, index=True, nullable=False)
    new_act = Column(String, index=True, nullable=False)
    new_section = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=True)
    change_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
