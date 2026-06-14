"""
스토리지 의존성

STORAGE_BACKEND 설정값에 따라 적절한 StorageBackend 구현체를 반환한다.
현재는 local 만 지원하며, 추후 minio 등을 분기로 추가할 수 있다.
"""
from functools import lru_cache

from app.core.config import settings
from app.core.storage import LocalStorage, StorageBackend


@lru_cache
def _build_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorage(settings.LOCAL_STORAGE_PATH)
    raise ValueError(f"Unsupported STORAGE_BACKEND: {settings.STORAGE_BACKEND}")


def get_storage() -> StorageBackend:
    """FastAPI Depends 로 주입할 스토리지 의존성"""
    return _build_storage()
