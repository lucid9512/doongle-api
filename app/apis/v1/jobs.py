import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
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
