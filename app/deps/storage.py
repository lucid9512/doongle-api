"""
스토리지 의존성

STORAGE_BACKEND 설정값(local | minio)에 따라 적절한 StorageBackend 구현체를 반환한다.
"""
from functools import lru_cache

from app.core.config import settings
from app.core.storage import LocalStorage, MinioStorage, StorageBackend


@lru_cache
def _build_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorage(settings.LOCAL_STORAGE_PATH)
    if backend == "minio":
        return MinioStorage(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET,
            secure=settings.MINIO_SECURE,
        )
    raise ValueError(f"Unsupported STORAGE_BACKEND: {settings.STORAGE_BACKEND}")


def get_storage() -> StorageBackend:
    """FastAPI Depends 로 주입할 스토리지 의존성"""
    return _build_storage()
