import abc
import hashlib
from typing import Tuple


class StorageBackend(abc.ABC):
    """Abstract interface for evidence artifact storage."""

    @abc.abstractmethod
    async def store(
        self,
        data: bytes,
        media_type: str,
        filename_hint: str = "artifact.bin"
    ) -> Tuple[str, str, int]:
        """Store bytes. Returns (storage_uri, sha256_hex, byte_size)."""
        pass

    @abc.abstractmethod
    async def retrieve(self, storage_uri: str) -> bytes:
        """Retrieve bytes from storage_uri."""
        pass

    @abc.abstractmethod
    async def exists(self, storage_uri: str) -> bool:
        """Check if artifact exists."""
        pass

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Compute SHA-256 hash of data."""
        return hashlib.sha256(data).hexdigest()

    async def verify_integrity(self, storage_uri: str, expected_sha256: str) -> bool:
        """Verify that stored artifact matches expected SHA-256 hash."""
        data = await self.retrieve(storage_uri)
        actual_hash = self.calculate_sha256(data)
        return actual_hash.lower() == expected_sha256.lower()
