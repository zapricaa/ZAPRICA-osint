from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend


_storage_singleton: StorageBackend = None


def get_storage() -> StorageBackend:
    global _storage_singleton
    if _storage_singleton is None:
        if settings.STORAGE_BACKEND == "local":
            _storage_singleton = LocalStorageBackend(settings.LOCAL_STORAGE_PATH)
        else:
            # Fallback to local if S3 is not configured
            _storage_singleton = LocalStorageBackend(settings.LOCAL_STORAGE_PATH)
    return _storage_singleton
