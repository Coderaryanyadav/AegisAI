import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment variables before importing configs
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "TEST_SECRET_KEY_FOR_SECURITY_AUTH_TESTS"

from legal_ai.database.connection import Base
from legal_ai.auth.security import encrypt_data, decrypt_data, get_password_hash, verify_password, create_access_token, decode_access_token
from legal_ai.database import crud
from legal_ai.auth.models import User, AuditLog

def test_encryption_decryption():
    """Verify AES-256 Fernet data encryption and decryption functions."""
    original_text = b"Confidential Legal Agreement Case 12345"
    encrypted = encrypt_data(original_text)
    assert encrypted != original_text
    
    decrypted = decrypt_data(encrypted)
    assert decrypted == original_text

def test_password_hashing():
    """Verify password hashing and verification match."""
    password = "SuperSecurePassword999!"
    hashed = get_password_hash(password)
    assert hashed != password
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_token_handling():
    """Verify access token generation and decoding."""
    data = {"sub": "lawyer1@firm.com", "role": "lawyer"}
    token = create_access_token(data)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "lawyer1@firm.com"
    assert decoded["role"] == "lawyer"

def test_database_crud_and_audit():
    """Verify database CRUD operations and automated audit trail generation."""
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Create a user
        email = "testlawyer@firm.com"
        password = "lawyerpassword"
        role = "lawyer"
        
        user = crud.create_user(db, email=email, password_raw=password, role=role)
        
        assert user.id is not None
        assert user.email == email
        assert user.role == role
        
        # Verify the user exists in DB
        db_user = crud.get_user_by_email(db, email)
        assert db_user is not None
        assert db_user.id == user.id
        assert verify_password(password, db_user.hashed_password)
        
        # Verify that USER_REGISTER audit log was automatically created
        audit_logs = crud.get_audit_logs(db)
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "USER_REGISTER"
        assert audit_logs[0].target_type == "USER"
        assert audit_logs[0].target_id == str(user.id)
        
        # Test creating a manual audit log
        log = crud.create_audit_log(
            db, 
            action="RAG_QUERY", 
            user_id=user.id, 
            user_email=user.email,
            target_type="SYSTEM",
            details="User ran search query on Case File"
        )
        assert log.id is not None
        
        all_logs = crud.get_audit_logs(db)
        assert len(all_logs) == 2
        assert all_logs[0].action == "RAG_QUERY"  # Newest log first
        
    finally:
        db.close()
