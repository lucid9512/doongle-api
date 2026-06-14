"""
이미지 저장소 추상화

- StorageBackend 인터페이스로 저장 방식을 추상화한다.
- 현재 LocalStorage(로컬 디렉토리) / MinioStorage(S3 호환) 구현을 제공한다.
- save() 는 api 가 사용(업로드 파일을 저장하고 image_path 반환).
  load() 는 워커(doongle-ai)가 사용(image_path 로 바이트 읽기) — 시그니처를 맞춰
  두 구현 모두에 두지만 이 레포의 api 에서는 호출하지 않는다.
"""
import io
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


class MinioStorage(StorageBackend):
    """MinIO(S3 호환) 오브젝트 스토리지

    - save() 는 오브젝트 키만 반환한다(예: "abc123.jpg"). 버킷명은 키/메시지에
      싣지 않고 env(MINIO_BUCKET)로만 관리한다 — 단일 버킷이고, 소유자별 조회는
      DB user_id + presigned URL 로 해결하므로 키에 버킷을 넣을 이득이 없다.
    - 버킷은 콘솔에서 미리 만든다고 가정하고 여기서 생성하지 않는다(존재 가정).
    - minio SDK 는 동기 라이브러리라 async save() 안에서 블로킹 호출이 일어난다.
      작은 이미지라 현재는 허용(추후 부하 시 to_thread 등으로 보강 여지).
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool,
    ):
        # minio 클라이언트는 __init__ 에서 1회 생성해 재사용한다.
        from minio import Minio

        self._bucket = bucket
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    async def save(self, file: UploadFile) -> str:
        # 원본 확장자 보존, 고유 오브젝트 키 생성
        suffix = Path(file.filename or "").suffix
        key = f"{uuid.uuid4().hex}{suffix}"

        content = await file.read()
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(content),
            length=len(content),
            content_type=file.content_type or "application/octet-stream",
        )

        logger.info("이미지 저장: %s/%s (%d bytes)", self._bucket, key, len(content))
        return key

    def load(self, image_path: str) -> bytes:
        response = self._client.get_object(self._bucket, image_path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
