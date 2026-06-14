import io
import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend
from app.deps import get_db
from app.deps.storage import get_storage
from app.schemas.res.common import SuccessJsonRes
from app.services.job import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger("app.apis.jobs")


@router.get(
    "/{job_id}",
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Read a job by job_id (polling)",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    job_id 로 단일 job 조회. 화면이 주기적으로 폴링한다.

    Returns
    - job_id, filename, status, result (처리 전이면 status="pending", result=None)
    """
    service = JobService(db)
    job = await service.get_by_job_id(job_id)
    return SuccessJsonRes(data=job)


@router.get(
    "/{job_id}/image",
    status_code=status.HTTP_200_OK,
    summary="Read a job's uploaded image (thumbnail)",
)
async def get_job_image(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    """job 의 원본 이미지 바이트를 반환(화면 썸네일 미리보기용)."""
    service = JobService(db)
    content, media_type = await service.load_image(job_id, storage)
    return StreamingResponse(io.BytesIO(content), media_type=media_type)
