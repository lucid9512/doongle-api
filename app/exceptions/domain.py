from datetime import datetime
from app.schemas.res.common import ErrorRes, MetaData
from app.core.request_context import get_request_id


class DomainError(Exception):
    """모든 도메인 예외의 기본 클래스"""
    status_code = 400
    message = "MSG_DOMAIN_ERROR"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message

        self.error_type = self.__class__.__name__
        self.meta = MetaData(
            request_id=get_request_id(),  # ✅ 자동으로 ContextVar에서 가져옴
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        super().__init__(self.message)

    def to_response(self) -> ErrorRes:
        return ErrorRes(
            message=self.message,
            error_type=self.error_type,
            meta=self.meta,
        )


class UnauthenticatedError(DomainError):
    """
    사용자 인증 실패 (토큰 부재/만료/위조)
    """
    status_code = 401
    message = "MSG_UNAUTHENTICATED"


class ForbiddenError(DomainError):
    """
    인증은 되었으나 권한 부족
    """
    status_code = 403
    message = "MSG_FORBIDDEN"


# 하위 호환: 기존 코드에서 import 한 케이스를 위해 권한 부족(403)을 alias 로 유지
UnAuthorizeError = ForbiddenError


class ObjectNotFoundError(DomainError):
    status_code = 404
    message = "MSG_OBJECT_NOT_FOUND"


class DuplicateError(DomainError):
    status_code = 409
    message = "MSG_DUPLICATE_DATA"


class UnprocessableEntityError(DomainError):
    """
    비즈니스 의미적 오류
    """
    status_code = 422
    message = "MSG_UNPROCESSABLE_ENTITY"