import os
import time
import bcrypt
import jwt
import re
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from aegis_backend.database import get_db, User, AEGIS_DIR, get_secure_key

# Generate or retrieve unique secure cryptographically random key if not configured in environment
SEC_KEY_PATH = os.path.join(AEGIS_DIR, ".jwt.key")
SECRET_KEY = get_secure_key("jwt", SEC_KEY_PATH, is_hex=True)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AEGIS_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))  # 30 minutes sliding session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("AEGIS_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    # Check token revocation
    is_revoked = False
    try:
        redis_client = await get_redis()
        if await redis_client.get(f"revoked_token:{token}"):
            is_revoked = True
    except Exception:
        from aegis_backend.database import RevokedToken
        from sqlalchemy import select
        rev_stmt = select(RevokedToken).filter(RevokedToken.token == token)
        rev_res = await db.execute(rev_stmt)
        if rev_res.scalars().first():
            is_revoked = True

    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked/logged out."
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    from sqlalchemy import select
    stmt = select(User).filter(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled")

    if user.must_change_password:
        path = request.url.path
        if not (path.endswith("/auth/change-default-password") or path.endswith("/auth/me")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before accessing this resource."
            )
            
    return user

def verify_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted. Administrator privileges required."
        )
    return current_user

def verify_lawyer_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "lawyer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted. Lawyer or Administrator privileges required."
        )
    return current_user

import redis.asyncio as aioredis
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

async def get_redis():
    return await aioredis.from_url(REDIS_URL, decode_responses=True)

async def rate_limit_auth(request: Request, db: AsyncSession = Depends(get_db)):
    if os.environ.get("AEGIS_TEST_MODE") == "true":
        return
    ip = request.client.host if request.client else "127.0.0.1"
    
    try:
        redis_client = await get_redis()
        key = f"rate_limit:auth:{ip}"
        
        current = await redis_client.get(key)
        if current and int(current) >= 5:
            raise HTTPException(
                status_code=429,
                detail="Too many authentication attempts. Please try again later."
            )
        
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60, nx=True)
        await pipe.execute()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        # Fallback to DB rate limiting
        from aegis_backend.database import AuthRateLimit
        from sqlalchemy import select, func
        import datetime
        
        # Check attempts in last 60 seconds
        one_minute_ago = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(seconds=60)
        stmt = select(func.count(AuthRateLimit.id)).filter(
            AuthRateLimit.ip_address == ip,
            AuthRateLimit.timestamp >= one_minute_ago
        )
        res = await db.execute(stmt)
        attempts = res.scalar() or 0
        if attempts >= 5:
            raise HTTPException(
                status_code=429,
                detail="Too many authentication attempts. Please try again later."
            )
        
        # Record attempt
        db.add(AuthRateLimit(ip_address=ip))
        try:
            await db.commit()
        except Exception:
            await db.rollback()

# Online/Offline Mode State (shared state)
SYSTEM_ONLINE_MODE = False

def verify_offline_mode():
    if SYSTEM_ONLINE_MODE:
        raise HTTPException(
            status_code=423,
            detail="System is currently in Online Sync Mode. Modifications are locked. Please toggle back to Offline Mode to enable edits."
        )
    return True

PROMPT_INJECTION_PATTERNS = [
    r"\bignore\b.*\bprevious\b",
    r"\bignore\b.*\binstruction\b",
    r"\bignore\b.*\bsystem\b",
    r"\boverride\b.*\binstruction\b",
    r"\boverride\b.*\bsystem\b",
    r"\bbypass\b.*\bguideline\b",
    r"\bforget\b.*\binstruction\b",
    r"\bforget\b.*\bwhat\s+i\s+said\b",
    r"\byou\s+are\s+now\b",
    r"\bact\s+as\s+a\b",
    r"\bnew\s+role\b",
    r"\boutput\b.*\bclient\s+notes\b"
]

def check_prompt_injection(text: str) -> bool:
    """Checks if a given user input text contains typical prompt injection or system override instructions."""
    if not text:
        return False
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

import asyncio

audit_lock = asyncio.Lock()

async def log_audit_trail(db: AsyncSession, email: str, action: str, target_type: str, target_id: Optional[str] = None, details: Optional[str] = None):
    from aegis_backend.database import AuditLog
    from sqlalchemy import select
    
    async with audit_lock:
        # Cryptographic Hash Chaining to prevent local database tampering
        try:
            stmt = select(AuditLog).order_by(AuditLog.id.desc())
            res = await db.execute(stmt)
            last_log = res.scalars().first()
            prev_hash = last_log.entry_hash if (last_log and last_log.entry_hash) else "GENESIS"
        except Exception:
            prev_hash = "GENESIS"
            
        hash_input = f"{email}|{action}|{target_type}|{target_id or ''}|{details or ''}|{prev_hash}"
        import hmac
        entry_hash = hmac.new(SECRET_KEY.encode(), hash_input.encode('utf-8'), hashlib.sha256).hexdigest()

        log = AuditLog(
            user_email=email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            entry_hash=entry_hash
        )
        db.add(log)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

async def verify_audit_trail_integrity(db: AsyncSession) -> bool:
    """Validates the blockchain-style SHA-256 hash chaining of all audit logs."""
    from aegis_backend.database import AuditLog
    from sqlalchemy import select
    try:
        stmt = select(AuditLog).order_by(AuditLog.id.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        prev_hash = "GENESIS"
        chain_started = False
        for log in logs:
            if not log.entry_hash:
                if chain_started:
                    # A log after the chain started is missing a hash! Tampering detected.
                    return False
                continue
            chain_started = True
            hash_input = f"{log.user_email}|{log.action}|{log.target_type}|{log.target_id or ''}|{log.details or ''}|{prev_hash}"
            import hmac
            computed = hmac.new(SECRET_KEY.encode(), hash_input.encode('utf-8'), hashlib.sha256).hexdigest()
            if log.entry_hash != computed:
                return False
            prev_hash = log.entry_hash
        return True
    except Exception:
        return False

def read_decrypted_document_text(txt_path: str) -> str:
    from aegis_backend.database import cipher
    with open(txt_path, "rb") as f:
        encrypted_data = f.read()
    try:
        return cipher.decrypt(encrypted_data).decode('utf-8')
    except Exception:
        # Fallback for plain text
        return encrypted_data.decode('utf-8', errors='ignore')

async def check_matter_access(db: AsyncSession, user: User, matter_id: int):
    """Checks if a user is authorized to access a given matter (IDOR protection)."""
    from aegis_backend.database import Matter, Client
    from sqlalchemy import select

    stmt = select(Matter).filter(Matter.id == matter_id)
    res = await db.execute(stmt)
    matter = res.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    if user.role == "client":
        stmt_client = select(Client).filter(Client.email == user.email)
        res_client = await db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client or matter.client_id != client.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return matter

async def check_document_access(db: AsyncSession, user: User, document_id: int):
    """Checks if a user is authorized to access a given document (IDOR protection)."""
    from aegis_backend.database import Document, Matter, Client
    from sqlalchemy import select

    stmt = select(Document).filter(Document.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if user.role == "client":
        if not doc.matter_id:
            raise HTTPException(status_code=403, detail="Access denied")
        stmt_client = select(Client).filter(Client.email == user.email)
        res_client = await db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            raise HTTPException(status_code=403, detail="Access denied")
        stmt_matter = select(Matter).filter(Matter.id == doc.matter_id)
        res_matter = await db.execute(stmt_matter)
        matter = res_matter.scalars().first()
        if not matter or matter.client_id != client.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return doc

async def safe_db_rollback(db):
    try:
        if db is not None and hasattr(db, "rollback"):
            await db.rollback()
    except Exception:
        pass
