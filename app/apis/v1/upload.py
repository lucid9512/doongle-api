import json
import logging
import uuid

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import StorageBackend
from app.deps import get_db
from app.deps.kafka import get_producer
from app.deps.storage import get_storage
from app.models.job import Job
from app.schemas.res.common import SuccessJsonRes

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger("app.apis.upload")


@router.post(
    "",
    response_model=SuccessJsonRes,
    status_code=status.HTTP_201_CREATED,
    summary="Upload images for inference (async gateway)",
)
async def upload_images(
    files: list[UploadFile] = File(..., description="추론할 이미지 파일들"),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    producer: AIOKafkaProducer = Depends(get_producer),
):
    """
    이미지를 업로드받아 (1) 저장소 저장, (2) job 을 pending 으로 DB 기록,
    (3) Kafka 에 `{job_id, image_path}` produce, (4) 접수 결과 반환.

    실제 추론은 워커(doongle-ai)가 비동기로 처리하므로 결과가 아니라
    "접수됨(pending)" 상태의 job 목록을 돌려준다.

    Returns
    - jobs: [{job_id, filename, status}] — 접수된 job 목록
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded.",
        )

    # 1) 먼저 전부 이미지인지 검증 (부분 저장 방지)
    for file in files:
        if not (file.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not an image file: {file.filename} ({file.content_type})",
            )

    # 2) 저장 + job(pending) 적재
    accepted = []
    for file in files:
        image_path = await storage.save(file)
        job_id = uuid.uuid4().hex
        db.add(
            Job(
                job_id=job_id,
                filename=file.filename or "",
                image_path=image_path,
                status="pending",
            )
        )
        accepted.append(
            {"job_id": job_id, "filename": file.filename, "image_path": image_path}
        )

    # 3) job 을 먼저 커밋해 DB 에 존재시킨 뒤 produce (워커가 DB 조회 시 race 방지)
    await db.commit()

    # 4) Kafka produce — 메시지는 {job_id, image_path} 만 (경량)
    for item in accepted:
        payload = json.dumps(
            {"job_id": item["job_id"], "image_path": item["image_path"]}
        ).encode("utf-8")
        await producer.send_and_wait(settings.KAFKA_UPLOAD_TOPIC, payload)
        logger.info("produced job_id=%s to %s", item["job_id"], settings.KAFKA_UPLOAD_TOPIC)

    jobs = [
        {"job_id": item["job_id"], "filename": item["filename"], "status": "pending"}
        for item in accepted
    ]
    return SuccessJsonRes(data={"jobs": jobs})
