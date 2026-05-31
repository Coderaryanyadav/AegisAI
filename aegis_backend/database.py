import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, TypeDecorator, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from cryptography.fernet import Fernet
import base64

# Base configuration directory in user home to prevent file permission issues
USER_HOME = os.path.expanduser("~")
AEGIS_DIR = os.path.join(USER_HOME, ".aegis_ai")
os.makedirs(AEGIS_DIR, exist_ok=True)
os.makedirs(os.path.join(AEGIS_DIR, "vault"), exist_ok=True)
os.makedirs(os.path.join(AEGIS_DIR, "backups"), exist_ok=True)

DB_PATH = os.path.join(AEGIS_DIR, "aegis_ai.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Cryptographic Master Key derivation (stores salt/key securely in the config folder)
KEY_PATH = os.path.join(AEGIS_DIR, ".master.key")
if not os.path.exists(KEY_PATH):
    # Generate a fresh random key if missing
    new_key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(new_key)
else:
    with open(KEY_PATH, "rb") as f:
        new_key = f.read()

cipher = Fernet(new_key)

class EncryptedText(TypeDecorator):
    """Saves transparently AES-256 encrypted fields in SQLite."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Encrypt plain text value
        encrypted_bytes = cipher.encrypt(value.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Decrypt stored text value
        decrypted_bytes = cipher.decrypt(value.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")

# ================= MODELS =================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="lawyer", nullable=False) # admin, lawyer, auditor
    firm_logo = Column(Text, nullable=True) # base64 logo string
    firm_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    notes = Column(EncryptedText, nullable=True) # Transparently Encrypted Notes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    matters = relationship("Matter", back_populates="client", cascade="all, delete-orphan")

class Matter(Base):
    __tablename__ = "matters"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    case_number = Column(String, unique=True, index=True, nullable=True)
    title = Column(String, nullable=False)
    court = Column(String, nullable=True)
    judge = Column(String, nullable=True)
    opponent_name = Column(String, nullable=True)
    opposing_advocate = Column(String, nullable=True)
    status = Column(String, default="open", nullable=False) # open, pending_hearing, closed, archived
    facts = Column(EncryptedText, nullable=True) # Transparently Encrypted case facts
    cnr_number = Column(String, nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    client = relationship("Client", back_populates="matters")
    schedules = relationship("Schedule", back_populates="matter", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="matter")

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    schedule_type = Column(String, nullable=False) # hearing, deadline, meeting
    target_date = Column(String, nullable=False) # ISO timestamp
    notes = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)

    matter = relationship("Matter", back_populates="schedules")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="SET NULL"), nullable=True)
    original_name = Column(String, nullable=False)
    stored_uuid = Column(String, unique=True, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    status = Column(String, default="uploaded", nullable=False) # uploaded, processing, ocr_needed, processed, failed
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    matter = relationship("Matter", back_populates="documents")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    details = Column(Text, nullable=True)

class BackupHistory(Base):
    __tablename__ = "backup_history"
    id = Column(Integer, primary_key=True, index=True)
    backup_name = Column(String, nullable=False)
    backup_size_bytes = Column(Integer, nullable=False)
    destination_path = Column(String, nullable=False)
    is_manual = Column(Boolean, default=True, nullable=False)
    status = Column(String, nullable=False) # success, failed, verified
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    error_message = Column(Text, nullable=True)

class BareActSection(Base):
    __tablename__ = "bare_act_sections"
    id = Column(Integer, primary_key=True, index=True)
    act = Column(String, index=True, nullable=False) # BNS, BNSS, BSA
    section = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

# ====== BILLING ======
class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    hours = Column(String, nullable=False)       # stored as string decimal
    rate_per_hour = Column(String, nullable=False, default="5000")  # INR
    date = Column(String, nullable=False)        # ISO date string
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    matter_id = Column(Integer, ForeignKey("matters.id", ondelete="CASCADE"), nullable=True)
    invoice_number = Column(String, unique=True, nullable=False)
    total_amount = Column(String, nullable=False)    # INR string
    gst_amount = Column(String, nullable=False)      # 18% GST
    grand_total = Column(String, nullable=False)
    status = Column(String, default="unpaid")        # unpaid, paid, overdue
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ====== ANNOTATIONS ======
class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False)
    selected_text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    color = Column(String, default="yellow")   # yellow, green, red, blue
    page_hint = Column(String, nullable=True)  # rough text position hint
    created_at = Column(DateTime, default=datetime.utcnow)

# ====== 2FA ======
class TwoFactorSecret(Base):
    __tablename__ = "two_factor_secrets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    totp_secret = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=False)
    recovery_codes = Column(Text, nullable=True)  # JSON list of hashed codes
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    
    # Run offline schema alterations for column addition safety
    try:
        with engine.connect() as conn:
            info = conn.execute(text("PRAGMA table_info(matters)")).fetchall()
            existing_cols = [row[1] for row in info]
            if "opponent_name" not in existing_cols:
                conn.execute(text("ALTER TABLE matters ADD COLUMN opponent_name TEXT"))
            if "opposing_advocate" not in existing_cols:
                conn.execute(text("ALTER TABLE matters ADD COLUMN opposing_advocate TEXT"))
            if "cnr_number" not in existing_cols:
                conn.execute(text("ALTER TABLE matters ADD COLUMN cnr_number TEXT"))
            if "is_locked" not in existing_cols:
                conn.execute(text("ALTER TABLE matters ADD COLUMN is_locked INTEGER DEFAULT 0"))
                
            user_info = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            existing_user_cols = [row[1] for row in user_info]
            if "firm_logo" not in existing_user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN firm_logo TEXT"))
            if "firm_name" not in existing_user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN firm_name TEXT"))
                
            conn.commit()
    except Exception as ex:
        print(f"Offline migrations error: {ex}")

    db = SessionLocal()
    try:
        # Seed admin
        admin_exists = db.query(User).filter(User.email == "admin@legalai.local").first()
        if not admin_exists:
            import bcrypt
            hashed = bcrypt.hashpw("adminpassword123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            default_admin = User(
                email="admin@legalai.local",
                hashed_password=hashed,
                role="admin"
            )
            db.add(default_admin)
            db.commit()

        # Seed Bare Acts
        section_count = db.query(BareActSection).count()
        if section_count == 0:
            seed_sections = [
                BareActSection(
                    act="BNS",
                    section="101",
                    title="Punishment for Murder",
                    content="101. (1) Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.\n\n(2) When a group of five or more persons acting in concert commits murder on the ground of race, caste or community, sex, place of birth, language, personal belief or any other ground, each member of such group shall be punished with death or with imprisonment for life or imprisonment for a term which shall not be less than seven years, and shall also be liable to fine."
                ),
                BareActSection(
                    act="BNS",
                    section="109",
                    title="Attempt to Murder",
                    content="109. Whoever does any act with such intention or knowledge, and under such circumstances that, if he by that act caused death, he would be guilty of murder, shall be punished with imprisonment of either description for a term which may extend to ten years, and shall also be liable to fine; and, if hurt is caused to any person by such act, the offender shall be liable to imprisonment for life, or to such punishment as is hereinbefore mentioned."
                ),
                BareActSection(
                    act="BNS",
                    section="63",
                    title="Rape Definition",
                    content="63. A man is said to commit rape who, except in the case hereinafter excepted, has sexual intercourse with a woman under circumstances falling under any of the following seven descriptions:—\nFirstly. — Against her will.\nSecondly. — Without her consent.\nThirdly. — With her consent, when her consent has been obtained by putting her or any person in whom she is interested, in fear of death or of hurt..."
                ),
                BareActSection(
                    act="BNS",
                    section="64",
                    title="Punishment for Rape",
                    content="64. (1) Whoever, except in the cases provided for by sub-section (2), commits rape shall be punished with rigorous imprisonment of either description for a term which shall not be less than ten years, but which may extend to imprisonment for life, and shall also be liable to fine."
                ),
                BareActSection(
                    act="BNS",
                    section="303",
                    title="Theft",
                    content="303. (1) Whoever, intending to take dishonestly any movable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft.\n\n(2) Whoever commits theft shall be punished with imprisonment for a term which may extend to three years, or with fine, or with both, and in the case of a second or subsequent conviction of theft, with rigorous imprisonment for a term which shall not be less than one year, but which may extend to five years, and with fine."
                ),
                BareActSection(
                    act="BNS",
                    section="318",
                    title="Cheating",
                    content="318. (1) Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any property to any person, or to consent that any person shall retain any property... is said to cheat.\n\n(2) Whoever cheats shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both."
                ),
                BareActSection(
                    act="BNS",
                    section="356",
                    title="Defamation",
                    content="356. (1) Whoever, by words either spoken or intended to be read, or by signs or by visible representations, makes or publishes any imputation concerning any person intending to harm... is said to defame that person.\n\n(2) Whoever defames another shall be punished with simple imprisonment for a term which may extend to two years, or with fine, or with both, or with community service."
                ),
                BareActSection(
                    act="BNSS",
                    section="173",
                    title="Information in Cognizable Cases (FIR)",
                    content="173. (1) Every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing by him or under his direction...\n\n(2) Zero FIR: The information may be recorded irrespective of the territory or jurisdiction where the offence was committed, and electronic filing of FIR is formally authorized."
                ),
                BareActSection(
                    act="BNSS",
                    section="180",
                    title="Examination of Witnesses by Police",
                    content="180. (1) Any police officer making an investigation... may examine orally any person supposed to be acquainted with the facts and circumstances of the case.\n\n(2) Statement recording via audio-video electronic means is formally authorized."
                ),
                BareActSection(
                    act="BSA",
                    section="2",
                    title="Interpretation Clause (Document definition)",
                    content="2. (1) In this Adhiniyam, unless the context otherwise requires,—\n'Document' means any matter expressed or described upon any substance by means of letters, figures or marks... and includes electronic or digital records, server logs, local emails, smartphone message transcripts, and device locations."
                ),
                BareActSection(
                    act="BSA",
                    section="63",
                    title="Admissibility of Electronic Records",
                    content="63. Notwithstanding anything contained in this Adhiniyam, any information contained in an electronic record which is printed on paper, stored, recorded or copied in optical or magnetic media produced by a computer... shall be deemed to be also a document... and shall be admissible in any proceedings, without further proof or production of the original."
                )
            ]
            db.bulk_save_objects(seed_sections)
            db.commit()
    except Exception as e:
        print(f"Error seeding default admin account: {e}")
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
