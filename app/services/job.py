import json
import logging
import uuid

from aiokafka import AIOKafkaProducer
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import StorageBackend
from app.exceptions import (
    DatabaseCommitError,
    FileIOError,
    ObjectNotFoundError,
)
from app.models.job import Job
from app.schemas.model.job import JobAcceptedSchema, JobSchema
from app.schemas.req.upload import UploadImageMeta

logger = logging.getLogger(__name__)


class JobService:
    """Job 도메인 서비스 (업로드 접수 + 조회)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------
    # CREATE
    # ---------------------------
    async def create_from_uploads(
        self,
        files: list[UploadFile],
        storage: StorageBackend,
        producer: AIOKafkaProducer,
    ) -> list[dict]:
        """
        업로드 이미지들을 접수한다.

        순서: 전체 이미지 검증 → 저장 + job(pending) 적재 → DB commit → Kafka produce.
        (commit 을 produce 보다 먼저 해 워커가 메시지 수신 후 DB 조회 시 race 방지)

        Returns: [{job_id, filename, status}]
        """
        logger.info(f"[JobService] Upload accept request ({len(files)} files)")

        if not files:
            raise UnprocessableEntityError(message="MSG_NO_FILES")

        # 1) 메타(파일명 길이·공백, content-type) 검증을 스키마에서 일괄 처리 (부분 저장 방지)
        metas = [
            UploadImageMeta(filename=file.filename or "", content_type=file.content_type or "")
            for file in files
        ]

        # 2) 저장 + job(pending) 적재
        accepted = []
        try:
            for file, meta in zip(files, metas):
                image_path = await storage.save(file)
                job_id = uuid.uuid4().hex
                self.db.add(
                    Job(
                        job_id=job_id,
                        filename=meta.filename,
                        image_path=image_path,
                        status="pending",
                    )
                )
                accepted.append(
                    {"job_id": job_id, "filename": meta.filename, "image_path": image_path}
                )
        except Exception as e:
            logger.exception(f"[JobService] File save failed : {e}")
            await self.db.rollback()
            raise FileIOError(message="MSG_FILE_IO_FAIL")

        # 3) job 을 먼저 커밋해 DB 에 존재시킨 뒤 produce
        try:
            await self.db.commit()
        except Exception as e:
            logger.exception(f"[JobService] DB commit failed while creating jobs : {e}")
            await self.db.rollback()
            raise DatabaseCommitError(message="MSG_DB_COMMIT_FAIL")

        # 4) Kafka produce — 메시지는 {job_id, image_path} 만 (경량)
        for item in accepted:
            payload = json.dumps(
                {"job_id": item["job_id"], "image_path": item["image_path"]}
            ).encode("utf-8")
            await producer.send_and_wait(settings.KAFKA_TOPIC, payload)
            logger.info(
                f"[JobService] produced job_id={item['job_id']} to {settings.KAFKA_TOPIC}"
            )

        return [
            JobAcceptedSchema(
                job_id=item["job_id"], filename=item["filename"], status="pending"
            ).model_dump()
            for item in accepted
        ]

    # ---------------------------
    # READ
    # ---------------------------
    async def _get_or_404(self, job_id: str) -> Job:
        job = await self.db.scalar(select(Job).where(Job.job_id == job_id))
        if job is None:
            logger.warning(f"[JobService] Job not found (job_id={job_id})")
            raise ObjectNotFoundError(message="MSG_JOB_NOT_FOUND")
        return job

    async def get_by_job_id(self, job_id: str) -> dict:
        """job_id 로 단일 job 조회 (폴링용)."""
        logger.info(f"[JobService] Job Get request (job_id={job_id})")
        job = await self._get_or_404(job_id)
        return JobSchema.model_validate(job).model_dump()
