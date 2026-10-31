"""Security utilities: Argon2id password hashing, TOTP MFA, and session tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import jwt
import pyotp
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# Hybrid password hasher: Argon2id primary, Bcrypt fallback for migration
_hasher = PasswordHash((Argon2Hasher(), BcryptHasher()))


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against Argon2id or legacy hash."""
    if not hashed_password:
        return False
    try:
        return _hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def generate_mfa_secret() -> str:
    """Generate cryptographically secure base32 secret for TOTP MFA."""
    return pyotp.random_base32()


def get_mfa_uri(secret: str, account_name: str, issuer_name: str = "ZAPRICA-OSINT") -> str:
    """Generate otpauth:// URI for authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account_name, issuer_name=issuer_name)


def verify_mfa_code(secret: str, code: str) -> bool:
    """Verify TOTP 6-digit MFA code with ±30s clock drift tolerance."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=1)


def generate_session_token() -> str:
    """Generate a high-entropy session token."""
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """SHA-256 hash of a session token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_invitation_token() -> str:
    """Generate a high-entropy single-use invitation token."""
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    """SHA-256 hash of an invitation token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: Union[str, Any],
    workspace_id: Optional[str] = None,
    role: Optional[str] = None,
    permissions: Optional[list[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if workspace_id:
        to_encode["workspace_id"] = str(workspace_id)
    if role:
        to_encode["role"] = role
    if permissions:
        to_encode["permissions"] = permissions

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None
