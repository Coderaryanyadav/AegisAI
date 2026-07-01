import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from aegis_backend.database import get_db, User
from aegis_backend.schemas.models import UserRegister, UserResponse, FirmSettingsUpdate, TwoFASetupVerify
from aegis_backend.core.security import (
    verify_password, create_access_token, create_refresh_token, get_current_user,
    rate_limit_auth, verify_offline_mode, log_audit_trail, verify_admin, SECRET_KEY, ALGORITHM, oauth2_scheme
)
from aegis_backend.services.user_service import UserService
from aegis_backend.repositories.user_repository import UserRepository

router = APIRouter(tags=["auth"])

@router.post("/auth/register", response_model=UserResponse, dependencies=[Depends(rate_limit_auth)])
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    user = await UserService.register_user(db, user_in)
    await log_audit_trail(db, user.email, "REGISTER", "users", str(user.id))
    return user

@router.post("/auth/token", dependencies=[Depends(rate_limit_auth)])
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    totp_code: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    user = await repo.get_by_email(form_data.username)
    
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

    # Verify 2FA if enabled
    two_fa = await repo.get_two_factor_secret(user.id)
    if two_fa and two_fa.is_enabled:
        if not totp_code:
            response.status_code = status.HTTP_202_ACCEPTED
            return {
                "two_factor_required": True,
                "message": "Two-factor authentication required."
            }
            
        verified = await UserService.verify_totp_or_recovery(db, user, totp_code)
        if not verified:
            raise HTTPException(status_code=400, detail="Invalid TOTP code or recovery code")

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    await log_audit_trail(db, user.email, "LOGIN", "users", str(user.id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user.role}

@router.post("/auth/change-default-password", dependencies=[Depends(rate_limit_auth)])
async def change_default_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await UserService.change_default_password(db, current_user, current_password, new_password)
    await log_audit_trail(db, current_user.email, "CHANGE_DEFAULT_PASSWORD", "users", str(current_user.id))
    return {"message": "Password updated successfully. You can now login."}

@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/user/firm-settings")
@router.post("/user/firm-settings")
async def update_firm_settings(req: FirmSettingsUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _ = Depends(verify_offline_mode)):
    await UserService.update_firm_settings(db, current_user, req)
    await log_audit_trail(db, current_user.email, "UPDATE_SETTINGS", "users", str(current_user.id), "Updated custom firm settings.")
    return {"message": "Firm settings updated successfully"}

@router.post("/2fa/setup")
async def setup_2fa(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return await UserService.setup_2fa(db, current_user)
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp/qrcode not installed. Run: pip install pyotp qrcode[pil]")

@router.post("/2fa/enable")
async def enable_2fa(req: TwoFASetupVerify, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        recovery_codes = await UserService.enable_2fa(db, current_user, req.totp_code)
        await log_audit_trail(db, current_user.email, "ENABLE_2FA", "user", str(current_user.id))
        return {"message": "2FA enabled successfully", "recovery_codes": recovery_codes}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

@router.post("/2fa/disable")
async def disable_2fa(req: TwoFASetupVerify, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        await UserService.disable_2fa(db, current_user, req.totp_code)
        await log_audit_trail(db, current_user.email, "DISABLE_2FA", "user", str(current_user.id))
        return {"message": "2FA disabled"}
    except ImportError:
        raise HTTPException(status_code=501, detail="pyotp not installed")

@router.get("/2fa/status")
async def get_2fa_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    repo = UserRepository(db)
    rec = await repo.get_two_factor_secret(current_user.id)
    return {"enabled": rec.is_enabled if rec else False}

@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    repo = UserRepository(db)
    return await repo.list_users()

@router.put("/users/{id}/role", response_model=UserResponse)
async def update_user_role(id: int, role: str = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    user = await UserService.update_user_role(db, id, role)
    await log_audit_trail(db, current_user.email, "UPDATE_USER_ROLE", "users", str(id), f"Changed role to {role}")
    return user

@router.put("/users/{id}/disable", response_model=UserResponse)
async def update_user_disable(id: int, is_disabled: bool = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    user = await UserService.update_user_disable(db, id, is_disabled, current_user)
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
        
    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if not user or user.is_disabled:
        raise HTTPException(status_code=401, detail="User not found or disabled")
        
    access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer", "role": user.role}

@router.post("/auth/logout")
async def logout(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    await UserService.logout_user(db, token)
    await log_audit_trail(db, current_user.email, "LOGOUT", "users", str(current_user.id))
    return {"message": "Successfully logged out"}


