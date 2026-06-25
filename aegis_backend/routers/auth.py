import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, TwoFactorSecret
from aegis_backend.schemas.models import UserRegister, UserResponse, FirmSettingsUpdate, TwoFASetupVerify
from aegis_backend.core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
    rate_limit_auth, verify_offline_mode, log_audit_trail
)

router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/auth/register", response_model=UserResponse, dependencies=[Depends(rate_limit_auth)])
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already registered")
    
    # Automatically register first user as admin, others as user's requested role (or default lawyer)
    user_count = db.query(User).count()
    assigned_role = "admin" if user_count == 0 else user_in.role
    
    hashed = hash_password(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed,
        role=assigned_role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit_trail(db, user.email, "REGISTER", "users", str(user.id))
    return user

@router.post("/auth/token", dependencies=[Depends(rate_limit_auth)])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    totp_code: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Check if 2FA is enabled for this user
    two_fa = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == user.id).first()
    if two_fa and two_fa.is_enabled:
        if not totp_code:
            return {
                "two_factor_required": True,
                "message": "Two-factor authentication required."
            }
        
        import pyotp
        totp = pyotp.TOTP(two_fa.totp_secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
            
    access_token = create_access_token(data={"sub": user.email})
    log_audit_trail(db, user.email, "LOGIN", "users", str(user.id))
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/user/firm-settings")
def update_firm_settings(req: FirmSettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _ = Depends(verify_offline_mode)):
    current_user.firm_name = req.firm_name
    current_user.firm_logo = req.firm_logo
    db.commit()
    db.refresh(current_user)
    log_audit_trail(db, current_user.email, "UPDATE_SETTINGS", "users", str(current_user.id), "Updated custom firm settings.")
    return {"message": "Firm settings updated successfully"}

@router.post("/2fa/setup")
def setup_2fa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        import pyotp, qrcode, io, base64
        existing = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id).first()
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
        db.commit()
        return {"secret": secret, "qr_code_base64": qr_b64, "uri": uri}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp/qrcode not installed. Run: pip install pyotp qrcode[pil]")

@router.post("/2fa/enable")
def enable_2fa(req: TwoFASetupVerify, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        import pyotp
        rec = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Run /api/2fa/setup first")
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(req.totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
        rec.is_enabled = True
        db.commit()
        log_audit_trail(db, current_user.email, "ENABLE_2FA", "user", str(current_user.id))
        return {"message": "2FA enabled successfully"}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

@router.post("/2fa/disable")
def disable_2fa(req: TwoFASetupVerify, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        import pyotp
        rec = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id).first()
        if not rec or not rec.is_enabled:
            raise HTTPException(status_code=400, detail="2FA not enabled")
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(req.totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
        rec.is_enabled = False
        db.commit()
        return {"message": "2FA disabled"}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

@router.get("/2fa/status")
def get_2fa_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rec = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == current_user.id).first()
    return {"enabled": rec.is_enabled if rec else False}
