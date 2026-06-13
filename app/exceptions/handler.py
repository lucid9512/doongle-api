import logging
import json
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.exceptions.domain import DomainError
from app.exceptions.service import ServiceError
from app.schemas.res.common import ErrorRes

logger = logging.getLogger("app")

async def request_validation_error_handler(request, exc: RequestValidationError):
    """
    Request Body Validation 오류 처리 핸들러
    - 422 상태 코드
    - ErrorRes 포맷으로 FE 전달
    - 상세 오류 내용 로그 기록
    """
    # 상세 에러 정보 추출
    error_details = exc.errors()
    raw_body = None

    try:
        raw_body = await request.body()
        raw_body = raw_body.decode("utf-8")
    except Exception:
        pass

    # 로그 기록
    logger.warning(
        "[ValidationError] %s | path=%s | body=%s",
        json.dumps(error_details, ensure_ascii=False),
        request.url.path,
        raw_body,
    )

    # FE로 내려갈 응답 (메시지는 i18n 코드로)
    payload = ErrorRes(
        message="MSG_VALIDATION_ERROR",
        error_type="RequestValidationError",
    )

    return JSONResponse(status_code=422, content=payload.model_dump())

async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().model_dump(),
    )


async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().model_dump(),
    )


def register_exception_handlers(app):
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
