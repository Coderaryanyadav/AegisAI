import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from aegis_backend.database import get_db, User, TwoFactorSecret
from aegis_backend.schemas.models import UserRegister, UserResponse, FirmSettingsUpdate, TwoFASetupVerify
from aegis_backend.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token, get_current_user,
    rate_limit_auth, verify_offline_mode, log_audit_trail, verify_admin, SECRET_KEY, ALGORITHM
)
import jwt

router = APIRouter(tags=["auth"])

@router.post("/auth/register", response_model=UserResponse, dependencies=[Depends(rate_limit_auth)])
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.email == user_in.email)
    res = await db.execute(stmt)
    existing = res.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="User already registered")
    
    # Automatically register first user as admin, others as default lawyer
    count_stmt = select(func.count(User.id))
    count_res = await db.execute(count_stmt)
    user_count = count_res.scalar()
    assigned_role = "admin" if user_count == 0 else "lawyer"
    
    hashed = hash_password(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed,
        role=assigned_role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await log_audit_trail(db, user.email, "REGISTER", "users", str(user.id))
    return user

@router.post("/auth/token", dependencies=[Depends(rate_limit_auth)])
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    totp_code: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).filter(User.email == form_data.username)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if user.is_disabled:
        raise HTTPException(status_code=400, detail="User account is disabled")
    
    if user.must_change_password:
        access_token = create_access_token(data={"sub": user.email})
        return {
            "must_change_password": True,
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Password change required. Please use /api/auth/change-default-password."
        }

    # Check if 2FA is enabled for this user
    stmt_2fa = select(TwoFactorSecret).filter(TwoFactorSecret.user_id == user.id)
    res_2fa = await db.execute(stmt_2fa)
    two_fa = res_2fa.scalars().first()
    if two_fa and two_fa.is_enabled:
        if not totp_code:
            response.status_code = status.HTTP_202_ACCEPTED
            return {
                "two_factor_required": True,
                "message": "Two-factor authentication required."
            }
        
        import pyotp
        import json
        import hashlib
        totp = pyotp.TOTP(two_fa.totp_secret)
        verified = totp.verify(totp_code)
        
        # If TOTP fails, check recovery codes
        if not verified and two_fa.recovery_codes:
            try:
                hashed_codes = json.loads(two_fa.recovery_codes)
                hashed_input = hashlib.sha256(totp_code.encode()).hexdigest()
                if hashed_input in hashed_codes:
                    # Match! Remove the used recovery code
                    hashed_codes.remove(hashed_input)
                    two_fa.recovery_codes = json.dumps(hashed_codes)
                    await db.commit()
                    verified = True
                    await log_audit_trail(db, user.email, "USED_RECOVERY_CODE", "user", str(user.id))
            except Exception:
                pass
                
        if not verified:
            raise HTTPException(status_code=400, detail="Invalid TOTP code or recovery code")
            
    user_email = user.email
    user_id = user.id
    user_role = user.role
    access_token = create_access_token(data={"sub": user_email})
    refresh_token = create_refresh_token(data={"sub": user_email})
    await log_audit_trail(db, user_email, "LOGIN", "users", str(user_id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user_role}

@router.post("/auth/change-default-password", dependencies=[Depends(rate_limit_auth)])
async def change_default_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        UserRegister.validate_password_strength(new_password)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    if not current_user.must_change_password:
        raise HTTPException(status_code=400, detail="Password change is not required for this user")
        
    user_email = current_user.email
    user_id = current_user.id
    current_user.hashed_password = hash_password(new_password)
    current_user.must_change_password = False
    await db.commit()
    await log_audit_trail(db, user_email, "CHANGE_DEFAULT_PASSWORD", "users", str(user_id))
    return {"message": "Password updated successfully. You can now login."}

@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/user/firm-settings")
@router.post("/user/firm-settings")
async def update_firm_settings(req: FirmSettingsUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _ = Depends(verify_offline_mode)):
    user_email = current_user.email
    user_id = current_user.id
    
    if req.firm_logo:
        import base64
        try:
            b64_data = req.firm_logo
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            decoded = base64.b64decode(b64_data)
            if len(decoded) > 2 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Firm logo size exceeds 2MB limit.")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail="Invalid base64 encoding for firm logo.")

    current_user.firm_name = req.firm_name
    current_user.firm_logo = req.firm_logo
    if req.gst_rate is not None:
        current_user.gst_rate = req.gst_rate
    await db.commit()
    await db.refresh(current_user)
    await log_audit_trail(db, user_email, "UPDATE_SETTINGS", "users", str(user_id), "Updated custom firm settings.")
    return {"message": "Firm settings updated successfully"}

@router.post("/2fa/setup")
async def setup_2fa(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        import pyotp, qrcode, io, base64
        stmt = select(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id)
        res = await db.execute(stmt)
        existing = res.scalars().first()
        if existing and existing.is_enabled:
            raise HTTPException(status_code=400, detail="2FA already enabled. Disable first.")
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=current_user.email, issuer_name="AegisAI")
        # Generate QR code
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        # Store secret (not yet enabled)
        if existing:
            existing.totp_secret = secret
            existing.is_enabled = False
        else:
            db.add(TwoFactorSecret(user_id=current_user.id, totp_secret=secret, is_enabled=False))
        await db.commit()
        return {"secret": secret, "qr_code_base64": qr_b64, "uri": uri}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp/qrcode not installed. Run: pip install pyotp qrcode[pil]")

@router.post("/2fa/enable")
async def enable_2fa(req: TwoFASetupVerify, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        import pyotp
        import uuid
        import json
        import hashlib
        stmt = select(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id)
        res = await db.execute(stmt)
        rec = res.scalars().first()
        if not rec:
            raise HTTPException(status_code=404, detail="Run /api/2fa/setup first")
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(req.totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
            
        # Generate 8 random recovery codes
        recovery_codes = [uuid.uuid4().hex[:8] for _ in range(8)]
        hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in recovery_codes]
        
        user_email = current_user.email
        user_id = current_user.id
        rec.is_enabled = True
        rec.recovery_codes = json.dumps(hashed_codes)
        await db.commit()
        await log_audit_trail(db, user_email, "ENABLE_2FA", "user", str(user_id))
        return {"message": "2FA enabled successfully", "recovery_codes": recovery_codes}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

@router.post("/2fa/disable")
async def disable_2fa(req: TwoFASetupVerify, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        import pyotp
        stmt = select(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id)
        res = await db.execute(stmt)
        rec = res.scalars().first()
        if not rec or not rec.is_enabled:
            raise HTTPException(status_code=400, detail="2FA not enabled")
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(req.totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
        rec.is_enabled = False
        await db.commit()
        return {"message": "2FA disabled"}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

@router.get("/2fa/status")
async def get_2fa_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id)
    res = await db.execute(stmt)
    rec = res.scalars().first()
    return {"enabled": rec.is_enabled if rec else False}

@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    stmt = select(User).order_by(User.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.put("/users/{id}/role", response_model=UserResponse)
async def update_user_role(id: int, role: str = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    if role not in ["admin", "lawyer", "auditor"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'lawyer', or 'auditor'.")
    
    stmt = select(User).filter(User.id == id)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = role
    await db.commit()
    await db.refresh(user)
    await log_audit_trail(db, current_user.email, "UPDATE_USER_ROLE", "users", str(id), f"Changed role to {role}")
    return user

@router.put("/users/{id}/disable", response_model=UserResponse)
async def update_user_disable(id: int, is_disabled: bool = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    if id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable or enable your own account.")
        
    stmt = select(User).filter(User.id == id)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_disabled = is_disabled
    await db.commit()
    await db.refresh(user)
    action = "DISABLE_USER" if is_disabled else "ENABLE_USER"
    await log_audit_trail(db, current_user.email, action, "users", str(id))
    return user

@router.post("/auth/refresh", dependencies=[Depends(rate_limit_auth)])
async def refresh_token(refresh_token: str = Form(...), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    stmt = select(User).filter(User.email == email)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user or user.is_disabled:
        raise HTTPException(status_code=401, detail="User not found or disabled")
        
    access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer", "role": user.role}

from aegis_backend.core.security import oauth2_scheme, get_redis

@router.post("/auth/logout")
async def logout(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    # 1. Blacklist token in Redis if active
    try:
        redis_client = await get_redis()
        await redis_client.setex(f"revoked_token:{token}", 3600, "1")
    except Exception:
        pass
        
    # 2. Blacklist token in Database as persistent fallback
    from aegis_backend.database import RevokedToken
    db_token = RevokedToken(token=token)
    db.add(db_token)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        
    await log_audit_trail(db, current_user.email, "LOGOUT", "users", str(current_user.id))
    return {"message": "Successfully logged out"}


