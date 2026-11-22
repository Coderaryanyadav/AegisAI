import base64
import hashlib
import hmac
import io
import json
import logging
import secrets
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_backend.database import User, TwoFactorSecret
from aegis_backend.repositories.user_repository import UserRepository
from aegis_backend.schemas.models import UserRegister, FirmSettingsUpdate, TwoFASetupVerify
from aegis_backend.core.security import hash_password, verify_password

logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"admin", "lawyer", "auditor"}
MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5 Megabytes
MAX_FIRM_NAME_LEN = 150
THUMBNAIL_MAX_DIMENSION = 384


class UserService:
    """Enterprise-grade service layer handling user authentication, role-based access

    control (RBAC), multi-factor authentication (MFA/2FA), and firm configuration.
    """

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserRegister) -> User:
        """Registers a new user, enforcing complexity rules, email normalization,

        and automatic initial-admin bootstrapping.
        """
        repo = UserRepository(db)
        normalized_email = user_in.email.strip().lower()

        # Enforce password strength validation at the service boundary
        try:
            UserRegister.validate_password_strength(user_in.password)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        existing = await repo.get_by_email(normalized_email)
        if existing:
            raise HTTPException(status_code=400, detail="User already registered")

        user_count = await repo.get_user_count()
        assigned_role = "admin" if user_count == 0 else "lawyer"

        hashed = hash_password(user_in.password)
        user = User(
            email=normalized_email,
            hashed_password=hashed,
            role=assigned_role
        )
        return await repo.create_user(user)

    @staticmethod
    async def verify_totp_or_recovery(db: AsyncSession, user: User, totp_code: str) -> bool:
        """Verifies a 6-digit TOTP token (accounting for clock drift) or single-use

        backup recovery codes with constant-time equality comparisons.
        """
        import pyotp

        if not totp_code:
            return False

        repo = UserRepository(db)
        two_fa = await repo.get_two_factor_secret(user.id)
        if not two_fa or not two_fa.is_enabled:
            return True

        clean_code = totp_code.replace(" ", "").replace("-", "").strip()

        # 1. Verify standard TOTP token with +/- 1 interval clock-drift window
        try:
            totp = pyotp.TOTP(two_fa.totp_secret)
            if totp.verify(clean_code, valid_window=1):
                return True
        except Exception as e:
            logger.debug("TOTP algorithmic verification failure: %s", e)

        # 2. Check single-use emergency backup recovery codes
        if two_fa.recovery_codes:
            try:
                hashed_codes: List[str] = json.loads(two_fa.recovery_codes)
                hashed_input = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

                matched_index: Optional[int] = None
                for idx, stored_hash in enumerate(hashed_codes):
                    if hmac.compare_digest(stored_hash, hashed_input):
                        matched_index = idx
                        break

                if matched_index is not None:
                    hashed_codes.pop(matched_index)
                    two_fa.recovery_codes = json.dumps(hashed_codes)
                    await repo.update_two_factor_secret(two_fa)
                    logger.info("User %s successfully consumed a 2FA emergency recovery code.", user.id)
                    return True
            except Exception as ex:
                logger.warning("Error processing 2FA recovery codes: %s", ex)

        return False

    @staticmethod
    async def change_default_password(
        db: AsyncSession,
        current_user: User,
        current_password: str,
        new_password: str
    ) -> None:
        """Forces newly provisioned accounts or prompted accounts to update their default password."""
        try:
            UserRegister.validate_password_strength(new_password)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect current password")

        if verify_password(new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="New password must be different from current password"
            )

        if not current_user.must_change_password:
            raise HTTPException(status_code=400, detail="Password change is not required for this user")

        repo = UserRepository(db)
        current_user.hashed_password = hash_password(new_password)
        current_user.must_change_password = False
        await repo.update_user(current_user)

    @staticmethod
    async def update_firm_settings(
        db: AsyncSession,
        current_user: User,
        req: FirmSettingsUpdate
    ) -> None:
        """Validates and updates custom firm branding, letterheads, and tax rates.

        Automatically optimizes large base64 logos into compact web thumbnails.
        """
        repo = UserRepository(db)

        # 1. Sanitize firm name
        if req.firm_name:
            req.firm_name = req.firm_name.strip()
            if len(req.firm_name) > MAX_FIRM_NAME_LEN:
                raise HTTPException(
                    status_code=400,
                    detail=f"Firm name exceeds maximum length of {MAX_FIRM_NAME_LEN} characters."
                )

        # 2. Validate GST rate
        if req.gst_rate is not None:
            if req.gst_rate < 0.0 or req.gst_rate > 100.0:
                raise HTTPException(status_code=400, detail="GST rate must be between 0% and 100%.")
            current_user.gst_rate = req.gst_rate

        # 3. Process Firm Logo
        if req.firm_logo:
            b64_raw = req.firm_logo
            mime_header = "image/png"
            if "," in b64_raw:
                header_part, b64_data = b64_raw.split(",", 1)
                if ";" in header_part and ":" in header_part:
                    mime_header = header_part.split(":")[1].split(";")[0].lower()
            else:
                b64_data = b64_raw

            try:
                decoded_bytes = base64.b64decode(b64_data)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid base64 encoding for firm logo.")

            if len(decoded_bytes) > MAX_LOGO_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Firm logo size exceeds {MAX_LOGO_BYTES // (1024 * 1024)}MB limit."
                )

            # High-fidelity thumbnail optimization for larger logos (>256KB)
            if len(decoded_bytes) > 256 * 1024:
                try:
                    from PIL import Image
                    image = Image.open(io.BytesIO(decoded_bytes))
                    
                    # Pillow resize with aspect ratio preservation
                    resample_filter = getattr(Image, "Resampling", Image).LANCZOS
                    image.thumbnail((THUMBNAIL_MAX_DIMENSION, THUMBNAIL_MAX_DIMENSION), resample_filter)

                    out_buffer = io.BytesIO()
                    has_alpha = image.mode in ("RGBA", "LA") or (image.info.get("transparency") is not None)
                    if has_alpha:
                        image.save(out_buffer, format="PNG", optimize=True)
                        final_mime = "image/png"
                    else:
                        image.save(out_buffer, format="JPEG", quality=85, optimize=True)
                        final_mime = "image/jpeg"

                    compressed_b64 = base64.b64encode(out_buffer.getvalue()).decode("utf-8")
                    req.firm_logo = f"data:{final_mime};base64,{compressed_b64}"
                except Exception as img_err:
                    logger.debug("Pillow thumbnail optimization bypassed: %s", img_err)

        current_user.firm_name = req.firm_name
        current_user.firm_logo = req.firm_logo
        await repo.update_user(current_user)

    @staticmethod
    async def setup_2fa(db: AsyncSession, current_user: User) -> Dict[str, Any]:
        """Initiates TOTP 2FA enrollment: returns base32 secret and provisioning QR code."""
        import pyotp
        import qrcode

        repo = UserRepository(db)
        existing = await repo.get_two_factor_secret(current_user.id)
        if existing and existing.is_enabled:
            raise HTTPException(status_code=400, detail="2FA already enabled. Disable first.")

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=current_user.email, issuer_name="AegisAI Legal Suite")

        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        if existing:
            existing.totp_secret = secret
            existing.is_enabled = False
            await repo.update_two_factor_secret(existing)
        else:
            new_secret = TwoFactorSecret(user_id=current_user.id, totp_secret=secret, is_enabled=False)
            await repo.create_two_factor_secret(new_secret)

        return {"secret": secret, "qr_code_base64": qr_b64, "uri": uri}

    @staticmethod
    async def enable_2fa(db: AsyncSession, current_user: User, totp_code: str) -> List[str]:
        """Confirms the TOTP secret with a valid verification code, activates 2FA,

        and generates single-use emergency recovery backup codes.
        """
        import pyotp

        repo = UserRepository(db)
        rec = await repo.get_two_factor_secret(current_user.id)
        if not rec or not rec.totp_secret:
            raise HTTPException(status_code=404, detail="Run /api/v1/2fa/setup first.")

        clean_code = totp_code.replace(" ", "").replace("-", "").strip()
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(clean_code, valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid TOTP verification code.")

        # Generate 8 cryptographically secure 8-character recovery codes
        recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]
        hashed_codes = [
            hashlib.sha256(code.encode("utf-8")).hexdigest()
            for code in recovery_codes
        ]

        rec.is_enabled = True
        rec.recovery_codes = json.dumps(hashed_codes)
        await repo.update_two_factor_secret(rec)
        return recovery_codes

    @staticmethod
    async def disable_2fa(db: AsyncSession, current_user: User, totp_code: str) -> None:
        """Disables 2FA upon successful TOTP verification and purges recovery codes."""
        import pyotp

        repo = UserRepository(db)
        rec = await repo.get_two_factor_secret(current_user.id)
        if not rec or not rec.is_enabled:
            raise HTTPException(status_code=400, detail="2FA is not currently enabled.")

        clean_code = totp_code.replace(" ", "").replace("-", "").strip()
        totp = pyotp.TOTP(rec.totp_secret)
        if not totp.verify(clean_code, valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid TOTP verification code.")

        rec.is_enabled = False
        rec.recovery_codes = None
        await repo.update_two_factor_secret(rec)

    @staticmethod
    async def update_user_role(db: AsyncSession, user_id: int, role: str) -> User:
        """Modifies user access roles with protective invariant: the last remaining

        active admin cannot be demoted.
        """
        if role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{role}'. Allowed roles are: {', '.join(sorted(ALLOWED_ROLES))}."
            )

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Guard: prevent demoting the sole active admin
        if user.role == "admin" and role != "admin":
            all_users = await repo.list_users()
            active_admins = [u for u in all_users if u.role == "admin" and not u.is_disabled and u.id != user_id]
            if not active_admins:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot demote the last remaining active Administrator."
                )

        user.role = role
        return await repo.update_user(user)

    @staticmethod
    async def update_user_disable(
        db: AsyncSession,
        user_id: int,
        is_disabled: bool,
        current_user: User
    ) -> User:
        """Disables or enables user login. Prevents self-disabling and disabling the sole admin."""
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot disable or enable your own account.")

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Guard: prevent disabling the sole active admin
        if is_disabled and user.role == "admin":
            all_users = await repo.list_users()
            other_active_admins = [u for u in all_users if u.role == "admin" and not u.is_disabled and u.id != user_id]
            if not other_active_admins:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot disable the last remaining active Administrator."
                )

        user.is_disabled = is_disabled
        return await repo.update_user(user)

    @staticmethod
    async def logout_user(db: AsyncSession, token: str) -> None:
        """Revokes a JWT token by appending it to the revoked token blacklist repository."""
        if not token or not token.strip():
            return
        repo = UserRepository(db)
        await repo.add_revoked_token(token.strip())
