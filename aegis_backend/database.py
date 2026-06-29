import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Date, Numeric, ForeignKey, TypeDecorator, event
from sqlalchemy.pool import StaticPool, NullPool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from cryptography.fernet import Fernet
import base64

# Base configuration directory in user home to prevent file permission issues
USER_HOME = os.path.expanduser("~")
AEGIS_DIR = os.path.join(USER_HOME, ".aegis_ai")
os.makedirs(AEGIS_DIR, exist_ok=True)
os.makedirs(os.path.join(AEGIS_DIR, "vault"), exist_ok=True)
os.makedirs(os.path.join(AEGIS_DIR, "backups"), exist_ok=True)

DB_PATH = os.path.join(AEGIS_DIR, "aegis_ai.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args = {
        "connect_args": {"check_same_thread": False},
        "poolclass": NullPool if ("test" in DATABASE_URL or ":memory:" in DATABASE_URL) else None
    }
else:
    sync_db_url = DATABASE_URL
    if sync_db_url.startswith("postgresql://") and not sync_db_url.startswith("postgresql+"):
        sync_db_url = sync_db_url.replace("postgresql://", "postgresql+pg8000://")
    engine = create_engine(
        sync_db_url,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600
    )

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

USE_POSTGRES = os.environ.get("USE_POSTGRES", "false").lower() == "true"

if DATABASE_URL.startswith("sqlite") and not USE_POSTGRES:
    async_db_url = DATABASE_URL
    if async_db_url.startswith("sqlite://") and not async_db_url.startswith("sqlite+aiosqlite://"):
        async_db_url = async_db_url.replace("sqlite://", "sqlite+aiosqlite://")
    async_engine = create_async_engine(
        async_db_url,
        connect_args={"check_same_thread": False}
    )
else:
    async_db_url = os.environ.get("POSTGRES_URL", DATABASE_URL)
    if async_db_url.startswith("postgresql://") and not async_db_url.startswith("postgresql+"):
        async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        async_db_url,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600
    )

AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=async_engine, class_=AsyncSession)

DATABASE_URL_RO = os.environ.get("DATABASE_URL_RO", DATABASE_URL)
if DATABASE_URL_RO.startswith("sqlite"):
    async_db_url_ro = DATABASE_URL_RO
    if async_db_url_ro.startswith("sqlite://") and not async_db_url_ro.startswith("sqlite+aiosqlite://"):
        async_db_url_ro = async_db_url_ro.replace("sqlite://", "sqlite+aiosqlite://")
    async_engine_ro = create_async_engine(
        async_db_url_ro,
        connect_args={"check_same_thread": False}
    )
else:
    async_db_url_ro = DATABASE_URL_RO
    if async_db_url_ro.startswith("postgresql://") and not async_db_url_ro.startswith("postgresql+"):
        async_db_url_ro = async_db_url_ro.replace("postgresql://", "postgresql+asyncpg://")
    async_engine_ro = create_async_engine(
        async_db_url_ro,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600
    )

from sqlalchemy import event

@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if os.environ.get("AEGIS_TEST_MODE") == "true":
        return
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
    except Exception:
        pass

@event.listens_for(async_engine_ro.sync_engine, "connect")
def set_sqlite_pragma_ro(dbapi_connection, connection_record):
    if os.environ.get("AEGIS_TEST_MODE") == "true":
        return
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
    except Exception:
        pass

AsyncSessionLocalRO = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=async_engine_ro, class_=AsyncSession)



# Machine-bound key encryption helpers to protect local key files at rest
def get_machine_key() -> bytes:
    import uuid
    import platform
    import hashlib
    import base64
    # Combine stable hardware address, node name, and OS platform
    node_str = f"{uuid.getnode()}-{platform.node()}-{platform.system()}"
    key_hash = hashlib.sha256(node_str.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)

def encrypt_key_file(data: str | bytes) -> bytes:
    raw_bytes = data if isinstance(data, bytes) else data.encode("utf-8")
    return Fernet(get_machine_key()).encrypt(raw_bytes)

def decrypt_key_file(encrypted_data: bytes) -> bytes:
    return Fernet(get_machine_key()).decrypt(encrypted_data)

# Cryptographic Master Key derivation (stores salt/key securely in OS keyring or fallback local file)
KEY_PATH = os.path.join(AEGIS_DIR, ".master.key")

def get_secure_key(key_name: str, fallback_path: str, is_hex: bool = False):
    # 1. Check environment variable override
    env_var = f"AEGIS_{key_name.upper()}_KEY"
    env_val = os.environ.get(env_var)
    if env_val:
        return env_val.strip()
        
    # 2. Try OS Keyring (cross-platform secure storage)
    try:
        import keyring
        stored = keyring.get_password("AegisAI", key_name)
        if stored:
            if not is_hex:
                return stored.encode("utf-8")
            return stored
    except Exception:
        pass
        
    # 3. Fallback to local files (with machine-bound encryption)
    if os.path.exists(fallback_path):
        try:
            with open(fallback_path, "rb") as f:
                encrypted_val = f.read()
            try:
                decrypted_val = decrypt_key_file(encrypted_val)
                if is_hex:
                    return decrypted_val.decode("utf-8").strip()
                return decrypted_val
            except Exception:
                # Fallback: if it was saved unencrypted, return raw value
                if is_hex:
                    return encrypted_val.decode("utf-8").strip()
                return encrypted_val
        except Exception:
            pass
            
    # 4. Generate new key if not found anywhere
    if is_hex:
        import secrets
        new_key = secrets.token_hex(32)
    else:
        new_key = Fernet.generate_key()
        
    # Store to OS Keyring
    try:
        import keyring
        keyring.set_password("AegisAI", key_name, new_key if is_hex else new_key.decode("utf-8"))
    except Exception:
        pass
        
    # Store to local file as backup fallback
    try:
        encrypted_val = encrypt_key_file(new_key)
        with open(fallback_path, "wb") as f:
            f.write(encrypted_val)
        try:
            os.chmod(fallback_path, 0o600)
        except Exception:
            pass
    except Exception:
        pass
        
    return new_key

master_key = get_secure_key("master", KEY_PATH, is_hex=False)
cipher = Fernet(master_key)

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
    notes = Column(EncryptedText, nullable=True) # Transparently Encrypted Notes
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
    status = Column(String, default="open", nullable=False) # open, pending_hearing, closed, archived
    facts = Column(EncryptedText, nullable=True) # Transparently Encrypted case facts
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
    schedule_type = Column(String, nullable=False) # hearing, deadline, meeting
    target_date = Column(DateTime, nullable=False) # DateTime column
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
    status = Column(String, default="uploaded", nullable=False) # uploaded, processing, ocr_needed, processed, failed
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
    status = Column(String, nullable=False) # success, failed, verified
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    error_message = Column(Text, nullable=True)

class BareActSection(Base):
    __tablename__ = "bare_act_sections"
    id = Column(Integer, primary_key=True, index=True)
    act = Column(String, index=True, nullable=False) # BNS, BNSS, BSA
    section = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

# ====== BILLING ======
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
    status = Column(String, default="unpaid") # unpaid, paid, overdue
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

# ====== ANNOTATIONS ======
class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    user_email = Column(String, nullable=False)
    selected_text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    color = Column(String, default="yellow")   # yellow, green, red, blue
    page_hint = Column(String, nullable=True)  # rough text position hint
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

# ====== 2FA ======
class TwoFactorSecret(Base):
    __tablename__ = "two_factor_secrets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    totp_secret = Column(EncryptedText, nullable=False)
    is_enabled = Column(Boolean, default=False)
    recovery_codes = Column(Text, nullable=True)  # JSON list of hashed codes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class StatutoryMapping(Base):
    __tablename__ = "statutory_mappings"
    id = Column(Integer, primary_key=True, index=True)
    old_act = Column(String, index=True, nullable=False)  # IPC, CrPC, IEA
    old_section = Column(String, index=True, nullable=False)
    new_act = Column(String, index=True, nullable=False)  # BNS, BNSS, BSA
    new_section = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=True)
    change_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)

# ====== Token Revocation ======
class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

def run_migrations():
    import alembic.config
    import alembic.command
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(base_dir, "alembic.ini")
    if os.path.exists(ini_path):
        cfg = alembic.config.Config(ini_path)
        cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        alembic.command.upgrade(cfg, "head")
    else:
        Base.metadata.create_all(bind=engine)

def init_db():
    try:
        run_migrations()
    except Exception as e:
        print(f"Programmatic migrations failed: {e}. Falling back to create_all.")
        Base.metadata.create_all(bind=engine)

    # Ensure a partial unique index on case_number that only applies to non-null values
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import text
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_matters_case_number_notnull ON matters(case_number) WHERE case_number IS NOT NULL"))
        except Exception as ex:
            print(f"Could not create partial unique index for case_number: {ex}")

    db = SessionLocal()
    try:
        # Seed statutory conversion mappings from IndianLegalHelper static dictionaries if empty
        if db.query(StatutoryMapping).count() == 0:
            from aegis_backend.indian_legal_helper import IndianLegalHelper
            
            # Seed IPC mappings
            for old_sec, detail in IndianLegalHelper.IPC_TO_BNS_MAP.items():
                db.add(StatutoryMapping(
                    old_act="IPC",
                    old_section=old_sec,
                    new_act=detail["act"],
                    new_section=detail["new_section"],
                    subject=detail["subject"],
                    change_type=detail["change_type"],
                    description=detail["description"]
                ))
            # Seed CrPC mappings
            for old_sec, detail in IndianLegalHelper.CRPC_TO_BNSS_MAP.items():
                db.add(StatutoryMapping(
                    old_act="CrPC",
                    old_section=old_sec,
                    new_act=detail["act"],
                    new_section=detail["new_section"],
                    subject=detail["subject"],
                    change_type=detail["change_type"],
                    description=detail["description"]
                ))
            # Seed IEA mappings
            for old_sec, detail in IndianLegalHelper.IEA_TO_BSA_MAP.items():
                db.add(StatutoryMapping(
                    old_act="IEA",
                    old_section=old_sec,
                    new_act=detail["act"],
                    new_section=detail["new_section"],
                    subject=detail["subject"],
                    change_type=detail["change_type"],
                    description=detail["description"]
                ))
            db.commit()

        # Seed admin
        admin_exists = db.query(User).filter(User.role == "admin").first()
        admin_pw = os.environ.get("AEGIS_ADMIN_PASSWORD")
        test_mode = os.environ.get("AEGIS_TEST_MODE") == "true"
        
        if not admin_exists:
            import bcrypt
            import logging
            import secrets
            
            logger = logging.getLogger("aegis_ai.backend")
            
            if admin_pw:
                actual_pw = admin_pw
                logger.info("Seeding admin account using password from AEGIS_ADMIN_PASSWORD environment variable.")
            elif test_mode:
                actual_pw = "adminpassword123"
                logger.warning("AEGIS_TEST_MODE is enabled. Seeding admin account with default password 'adminpassword123'.")
            else:
                actual_pw = secrets.token_urlsafe(16)
                pw_file_path = os.path.join(AEGIS_DIR, ".admin.initial.pw")
                try:
                    with open(pw_file_path, "w") as f:
                        f.write(actual_pw)
                    try:
                        os.chmod(pw_file_path, 0o600)
                    except Exception:
                        pass
                    logger.warning(
                        "\n" + "="*80 + "\n"
                        "SECURITY WARNING: Seeding default admin account (admin@legalai.local) with a programmatically generated password.\n"
                        f"The password has been securely written to: {pw_file_path}\n"
                        "Please retrieve it, log in, and delete that file.\n"
                        "To set a custom admin password directly, configure 'AEGIS_ADMIN_PASSWORD' in your environment.\n" +
                        "="*80 + "\n"
                    )
                except Exception as file_ex:
                    logger.error(f"Failed to write admin password to secure file: {file_ex}")
                    logger.warning(f"TEMPORARY PASSWORD (File write failed): {actual_pw}")
                
            hashed = bcrypt.hashpw(actual_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            default_admin = User(
                email="admin@legalai.local",
                hashed_password=hashed,
                role="admin",
                must_change_password=True
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
            db.add_all(seed_sections)
            db.commit()
    except Exception as e:
        print(f"Error seeding default admin account: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()

async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise

async def get_db_ro():
    async with AsyncSessionLocalRO() as db_ro:
        try:
            yield db_ro
        except Exception:
            await db_ro.rollback()
            raise

