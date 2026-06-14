import logging

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend
from app.deps import get_db
from app.deps.kafka import get_producer
from app.deps.storage import get_storage
from app.schemas.res.common import SuccessJsonRes
from app.services.job import JobService

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
    이미지를 업로드받아 저장 → job(pending) 기록 → Kafka produce → 접수 결과 반환.
    실제 추론은 워커(doongle-ai)가 비동기로 처리하므로 결과가 아니라 pending job 목록을 돌려준다.

    Returns
    - jobs: [{job_id, filename, status}]
    """
    service = JobService(db)
    jobs = await service.create_from_uploads(files, storage, producer)
    return SuccessJsonRes(data={"jobs": jobs})
