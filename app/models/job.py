import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Job(BaseModel):
    """
    이미지 추론 작업(job).

    - api: 업로드 시 status="pending" 으로 insert 하고 Kafka 에 produce.
    - 워커(doongle-ai): job_id 로 조회해 추론 후 status/result 를 update.
    - 화면: job_id 로 조회 API 를 폴링해 상태/결과 표시.
    """
    __tablename__ = "jobs"

    # 외부 식별자(uuid). Kafka 메시지·조회 API 에서 사용하는 공개 키.
    job_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False,
        default=lambda: uuid.uuid4().hex,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", index=True,
    )
    # 추론 결과. 워커가 채운다. JSON 문자열/텍스트 모두 수용하도록 Text.
    result: Mapped[str] = mapped_column(Text, nullable=True)
