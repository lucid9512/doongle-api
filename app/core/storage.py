"""
이미지 저장소 추상화

- StorageBackend 인터페이스로 저장 방식을 추상화한다.
- 지금은 LocalStorage(로컬 디렉토리) 구현만 사용한다.
- 추후 MinioStorage 등으로 교체할 수 있도록 인터페이스를 미리 정의한다.
- save() 는 api 가 사용(업로드 파일을 저장하고 image_path 반환).
  load() 는 워커(doongle-ai)가 사용(image_path 로 바이트 읽기) — 시그니처를 맞춰
  LocalStorage 에도 구현해두지만 이 레포의 api 에서는 호출하지 않는다.
"""
import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger("app.core.storage")


class StorageBackend(ABC):
    """이미지 저장소 추상 베이스"""

    @abstractmethod
    async def save(self, file: UploadFile) -> str:
        """업로드 파일을 저장하고 image_path(str) 를 반환한다."""
        raise NotImplementedError

    @abstractmethod
    def load(self, image_path: str) -> bytes:
        """image_path 로 저장된 이미지 바이트를 반환한다. (워커용)"""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """로컬 파일시스템 저장소"""

    def __init__(self, base_path: str):
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile) -> str:
        # 원본 확장자 보존, 고유 파일명 생성
        suffix = Path(file.filename or "").suffix
        name = f"{uuid.uuid4().hex}{suffix}"
        dest = self._base / name

        content = await file.read()
        dest.write_bytes(content)

        logger.info("이미지 저장: %s (%d bytes)", dest, len(content))
        return str(dest)

    def load(self, image_path: str) -> bytes:
        return Path(image_path).read_bytes()
