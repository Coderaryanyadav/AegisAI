import os
import time
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from aegis_backend.database import get_db, User, AEGIS_DIR

# Generate or retrieve unique secure cryptographically random key if not configured in environment
SEC_KEY_PATH = os.path.join(AEGIS_DIR, ".jwt.key")
if not os.path.exists(SEC_KEY_PATH):
    import secrets
    generated_key = secrets.token_hex(32)
    with open(SEC_KEY_PATH, "w") as f:
        f.write(generated_key)
    try:
        os.chmod(SEC_KEY_PATH, 0o600)
    except Exception:
        pass
else:
    with open(SEC_KEY_PATH, "r") as f:
        generated_key = f.read()

SECRET_KEY = os.environ.get("AEGIS_SECRET_KEY", generated_key)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AEGIS_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 1 day session for local client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
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

auth_attempts = defaultdict(list)

def rate_limit_auth(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    attempts = [t for t in auth_attempts[ip] if now - t < 60]
    auth_attempts[ip] = attempts
    if len(attempts) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please try again later."
        )
    auth_attempts[ip].append(now)

# Online/Offline Mode State (shared state)
SYSTEM_ONLINE_MODE = False

def verify_offline_mode():
    if SYSTEM_ONLINE_MODE:
        raise HTTPException(
            status_code=423,
            detail="System is currently in Online Sync Mode. Modifications are locked. Please toggle back to Offline Mode to enable edits."
        )
    return True

def log_audit_trail(db: Session, email: str, action: str, target_type: str, target_id: Optional[str] = None, details: Optional[str] = None):
    from aegis_backend.database import AuditLog
    log = AuditLog(
        user_email=email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    db.add(log)
    try:
        db.commit()
    except Exception:
        db.rollback()

def read_decrypted_document_text(txt_path: str) -> str:
    from aegis_backend.database import cipher
    with open(txt_path, "rb") as f:
        encrypted_data = f.read()
    try:
        return cipher.decrypt(encrypted_data).decode('utf-8')
    except Exception:
        # Fallback for plain text
        return encrypted_data.decode('utf-8', errors='ignore')
