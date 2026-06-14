from app.schemas.__base__ import VaModelRes


class JobSchema(VaModelRes):
    """Job 직렬화 스키마 (조회 응답). ORM Job -> 응답 data."""
    job_id: str
    filename: str
    status: str
    result: str | None = None


class JobAcceptedSchema(VaModelRes):
    """업로드 접수 응답 항목 (결과가 아니라 '접수됨'을 표현)."""
    job_id: str
    filename: str
    status: str
