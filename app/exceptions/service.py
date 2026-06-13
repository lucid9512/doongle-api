from datetime import datetime
from app.schemas.res.common import ErrorRes, MetaData
from app.core.request_context import get_request_id


class ServiceError(Exception):
    """모든 서비스 예외의 기본 클래스"""
    status_code = 500
    message = "MSG_SERVICE_ERROR"

    def __init__(self, message: str | None = None):
        """
        - message: 커스텀 메시지 (없으면 기본 메시지)
        - request_id: 현재 요청의 ContextVar에서 자동 추출
        """
        if message:
            self.message = message

        self.error_type = self.__class__.__name__
        self.meta = MetaData(
            request_id=get_request_id(),  # ✅ ContextVar에서 자동 가져옴
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        super().__init__(self.message)

    def to_response(self) -> ErrorRes:
        """서비스 예외를 표준 응답 모델로 변환"""
        return ErrorRes(
            message=self.message,
            error_type=self.error_type,
            meta=self.meta,
        )


class DatabaseCommitError(ServiceError):
    """DB 커밋 실패"""
    status_code = 500
    message = "MSG_DB_COMMIT_FAIL"

class FileIOError(ServiceError):
    """파일 IO 실패"""
    status_code = 500
    message = "MSG_FILE_IO_FAIL"
