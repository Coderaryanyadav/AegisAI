import os
import datetime
from pathlib import Path
import jwt
from cryptography.fernet import Fernet
from legal_ai.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ENCRYPTION_KEY

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# JWT token utility
def create_access_token(data: dict, expires_delta: datetime.timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# File encryption management
# Ensure we have a persistent Fernet key.
def resolve_encryption_key() -> bytes:
    # First priority: config value
    if ENCRYPTION_KEY:
        return ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY

    # Second priority: Read directly from .env file to avoid config caching issues
    base_dir = Path(__file__).resolve().parent.parent.parent
    env_file = base_dir / ".env"
    
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("ENCRYPTION_KEY="):
                    key_val = line.strip().split("=", 1)[1]
                    if key_val:
                        return key_val.encode()

    # Generate a new key if not found
    new_key = Fernet.generate_key()
    
    # Write it to .env so it persists
    with open(env_file, "a") as f:
        f.write(f"\nENCRYPTION_KEY={new_key.decode()}\n")
        
    print(f"[*] Generated new persistent file encryption key and saved to {env_file}")
    return new_key

# Initialize Fernet cipher
_fernet_key = resolve_encryption_key()
cipher = Fernet(_fernet_key)

def encrypt_data(data: bytes) -> bytes:
    """Encrypts bytes data using Fernet (AES-128 in CBC mode with HMAC-SHA256)"""
    return cipher.encrypt(data)

def decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypts bytes data using Fernet"""
    return cipher.decrypt(encrypted_data)
