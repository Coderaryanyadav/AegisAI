import json
import hashlib
import uuid
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_backend.database import User, TwoFactorSecret
from aegis_backend.repositories.user_repository import UserRepository
from aegis_backend.schemas.models import UserRegister, FirmSettingsUpdate, TwoFASetupVerify
from aegis_backend.core.security import hash_password, verify_password, log_audit_trail

class UserService:
    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserRegister) -> User:
        repo = UserRepository(db)
        existing = await repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(status_code=400, detail="User already registered")
            
        user_count = await repo.get_user_count()
        assigned_role = "admin" if user_count == 0 else "lawyer"
        
        hashed = hash_password(user_in.password)
        user = User(
            email=user_in.email,
            hashed_password=hashed,
            role=assigned_role
        )
        return await repo.create_user(user)

    @staticmethod
    async def verify_totp_or_recovery(db: AsyncSession, user: User, totp_code: str) -> bool:
        import pyotp
        repo = UserRepository(db)
        two_fa = await repo.get_two_factor_secret(user.id)
        if not two_fa or not two_fa.is_enabled:
            return True
            
        totp = pyotp.TOTP(two_fa.totp_secret)
        verified = totp.verify(totp_code)
        
        if not verified and two_fa.recovery_codes:
            try:
                hashed_codes = json.loads(two_fa.recovery_codes)
                hashed_input = hashlib.sha256(totp_code.encode()).hexdigest()
                if hashed_input in hashed_codes:
                    hashed_codes.remove(hashed_input)
                    two_fa.recovery_codes = json.dumps(hashed_codes)
                    await repo.update_two_factor_secret(two_fa)
                    verified = True
            except Exception:
                pass
                
        return verified

    @staticmethod
    async def change_default_password(db: AsyncSession, current_user: User, current_password: str, new_password: str) -> None:
        try:
            UserRegister.validate_password_strength(new_password)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect current password")
        
        if not current_user.must_change_password:
            raise HTTPException(status_code=400, detail="Password change is not required for this user")
            
        repo = UserRepository(db)
        current_user.hashed_password = hash_password(new_password)
        current_user.must_change_password = False
        await repo.update_user(current_user)

    @staticmethod
    async def update_firm_settings(db: AsyncSession, current_user: User, req: FirmSettingsUpdate) -> None:
        repo = UserRepository(db)
        if req.firm_logo:
            import base64
            from PIL import Image
            import io
            try:
                b64_data = req.firm_logo
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                decoded = base64.b64decode(b64_data)
                if len(decoded) > 5 * 1024 * 1024:
                    raise HTTPException(status_code=400, detail="Firm logo size exceeds 5MB limit.")
                    
                image = Image.open(io.BytesIO(decoded))
                image.thumbnail((384, 384))
                
                output_buffer = io.BytesIO()
                if image.mode in ('RGBA', 'LA') or (image.info.get('transparency') is not None):
                    image.save(output_buffer, format="PNG", optimize=True)
                    mime = "image/png"
                else:
                    image.save(output_buffer, format="JPEG", quality=85)
                    mime = "image/jpeg"
                    
                compressed_bytes = output_buffer.getvalue()
                compressed_b64 = base64.b64encode(compressed_bytes).decode("utf-8")
                req.firm_logo = f"data:{mime};base64,{compressed_b64}"
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(status_code=400, detail="Invalid base64 encoding or image format for firm logo.")

        current_user.firm_name = req.firm_name
        current_user.firm_logo = req.firm_logo
        if req.gst_rate is not None:
            current_user.gst_rate = req.gst_rate
            
        await repo.update_user(current_user)

    @staticmethod
    async def setup_2fa(db: AsyncSession, current_user: User) -> Dict[str, Any]:
        import pyotp, qrcode, io, base64
        repo = UserRepository(db)
        existing = await repo.get_two_factor_secret(current_user.id)
        if existing and existing.is_enabled:
            raise HTTPException(status_code=400, detail="2FA already enabled. Disable first.")
            
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=current_user.email, issuer_name="AegisAI")
        
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        
        if existing:
            existing.totp_secret = secret
            existing.is_enabled = False
            await repo.update_two_factor_secret(existing)
        else:
            new_secret = TwoFactorSecret(user_id=current_user.id, totp_secret=secret, is_enabled=False)
            await repo.create_two_factor_secret(new_secret)
            
        return {"secret": secret, "qr_code_base64": qr_b64, "uri": uri}

    @staticmethod
    async def enable_2fa(db: AsyncSession, current_user: User, totp_code: str) -> list[str]:
        import pyotp
        repo = UserRepository(db)
        rec = await repo.get_two_factor_secret(current_user.id)
        if not rec:
            raise HTTPException(status_code=404, detail="Run /api/2fa/setup first")
            
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
            
        recovery_codes = [uuid.uuid4().hex[:8] for _ in range(8)]
        hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in recovery_codes]
        
        rec.is_enabled = True
        rec.recovery_codes = json.dumps(hashed_codes)
        await repo.update_two_factor_secret(rec)
        return recovery_codes

    @staticmethod
    async def disable_2fa(db: AsyncSession, current_user: User, totp_code: str) -> None:
        import pyotp
        repo = UserRepository(db)
        rec = await repo.get_two_factor_secret(current_user.id)
        if not rec or not rec.is_enabled:
            raise HTTPException(status_code=400, detail="2FA not enabled")
            
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
            
        rec.is_enabled = False
        await repo.update_two_factor_secret(rec)

    @staticmethod
    async def update_user_role(db: AsyncSession, user_id: int, role: str) -> User:
        if role not in ["admin", "lawyer", "auditor"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'lawyer', or 'auditor'.")
            
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        user.role = role
        return await repo.update_user(user)

    @staticmethod
    async def update_user_disable(db: AsyncSession, user_id: int, is_disabled: bool, current_user: User) -> User:
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot disable or enable your own account.")
            
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        user.is_disabled = is_disabled
        return await repo.update_user(user)

    @staticmethod
    async def logout_user(db: AsyncSession, token: str) -> None:
        repo = UserRepository(db)
        await repo.add_revoked_token(token)
