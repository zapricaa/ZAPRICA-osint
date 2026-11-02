"""Browser Profile Manager: manages dedicated persistent browser profile paths per authorized user."""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status

from app.core.config import settings


class BrowserProfileManager:
    """Manages isolated browser profile directory storage on disk outside git tracking."""

    @classmethod
    def get_base_dir(cls) -> Path:
        base_path = Path(settings.BROWSER_PROFILES_DIR).resolve()
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path

    @classmethod
    def get_user_profile_dir(cls, user_id: uuid.UUID, profile_name: str = "default") -> Path:
        """
        Computes and validates the isolated filesystem path for a user's browser profile.
        Prevents directory traversal attacks.
        """
        # Explicitly block path traversal characters
        if ".." in profile_name or "/" in profile_name or "\\" in profile_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid profile name or directory traversal detected."
            )

        # Validate profile name
        safe_name = "".join(c for c in profile_name if c.isalnum() or c in ("-", "_")).strip()
        if not safe_name:
            safe_name = "default"

        base = cls.get_base_dir()
        user_dir = base / str(user_id)
        profile_path = user_dir / safe_name

        # Ensure resolved path is strictly within base dir
        resolved = profile_path.resolve()
        if not str(resolved).startswith(str(base)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid profile name or directory traversal detected."
            )

        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    @classmethod
    def delete_profile(cls, user_id: uuid.UUID, profile_name: str = "default") -> bool:
        """Deletes persistent browser profile storage for cleanup or session revocation."""
        path = cls.get_user_profile_dir(user_id, profile_name)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            return True
        return False
