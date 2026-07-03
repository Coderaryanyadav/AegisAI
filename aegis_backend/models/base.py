from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Text, TypeDecorator
from cryptography.fernet import Fernet
import os

class Base(DeclarativeBase):
    pass

class EncryptedText(TypeDecorator):
    """Saves transparently AES-256 encrypted fields in SQLite."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from aegis_backend.database import cipher
        encrypted_bytes = cipher.encrypt(value.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        from aegis_backend.database import cipher
        decrypted_bytes = cipher.decrypt(value.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
