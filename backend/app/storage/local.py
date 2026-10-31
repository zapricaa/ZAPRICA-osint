import os
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, status

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for development and hermetic environments."""

    def __init__(self, base_directory: str = "./data/evidence"):
        self.base_dir = Path(base_directory).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_uri: str) -> Path:
        if storage_uri.startswith("local://"):
            rel_path = storage_uri[len("local://"):]
        else:
            rel_path = storage_uri

        target = (self.base_dir / rel_path).resolve()
        # Security: Prevent directory traversal
        if not str(target).startswith(str(self.base_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Illegal storage path traversal attempt."
            )
        return target

    async def store(
        self,
        data: bytes,
        media_type: str,
        filename_hint: str = "artifact.bin"
    ) -> Tuple[str, str, int]:
        sha256 = self.calculate_sha256(data)
        byte_size = len(data)

        # Store using sha256-prefixed unique path
        unique_name = f"{sha256[:16]}_{uuid.uuid4().hex[:8]}_{filename_hint}"
        dest_path = self.base_dir / unique_name

        # Write to file
        with open(dest_path, "wb") as f:
            f.write(data)

        storage_uri = f"local://{unique_name}"
        return storage_uri, sha256, byte_size

    async def retrieve(self, storage_uri: str) -> bytes:
        target = self._resolve_path(storage_uri)
        if not target.exists() or not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence artifact at {storage_uri} not found."
            )
        with open(target, "rb") as f:
            return f.read()

    async def exists(self, storage_uri: str) -> bool:
        try:
            target = self._resolve_path(storage_uri)
            return target.exists() and target.is_file()
        except HTTPException:
            return False
