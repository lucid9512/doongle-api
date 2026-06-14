import io
import logging
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBackend
from app.deps import get_db
from app.deps.storage import get_storage
from app.models.job import Job
from app.schemas.res.common import SuccessJsonRes

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger("app.apis.jobs")


async def _get_job_or_404(db: AsyncSession, job_id: str) -> Job:
    result = await db.execute(select(Job).where(Job.job_id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )
    return job


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
    - job_id, filename, status, result
      (워커가 아직 처리 전이면 status="pending", result=None)
    """
    job = await _get_job_or_404(db, job_id)
    return SuccessJsonRes(
        data={
            "job_id": job.job_id,
            "filename": job.filename,
            "status": job.status,
            "result": job.result,
        }
    )


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
    """
    job 의 원본 이미지 바이트를 반환(화면 썸네일 미리보기용).
    """
    job = await _get_job_or_404(db, job_id)

    try:
        content = storage.load(job.image_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found for job: {job_id}",
        )

    media_type = mimetypes.guess_type(job.filename or job.image_path)[0] or "application/octet-stream"
    return StreamingResponse(io.BytesIO(content), media_type=media_type)
