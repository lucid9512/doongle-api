import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger("app.exception")


def init_exception_handlers(app):
    """
    FastAPI 전역 예외 핸들러 등록
    - HTTPException, RequestValidationError 등 프레임워크 레벨 예외 처리
    - 예외 발생 시 로깅 및 표준 JSON 응답 반환
    """

    @app.exception_handler(HTTPException)
    async def http_exception_logger(request: Request, exc: HTTPException):
        """
        HTTPException 처리 핸들러
        - 상태 코드 및 요청 경로를 로깅
        - {"detail": "..."} 형태의 JSON 응답 반환
        """
        logger.warning(
            f"HTTPException {exc.status_code} at {request.method} {request.url.path} - detail={exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_logger(request: Request, exc: RequestValidationError):
        """
        RequestValidationError 처리 핸들러
        - 요청 유효성 검증 오류 발생 시 상세 오류 로그 기록
        - {"detail": [...]} 형태의 JSON 응답 반환
        """
        errors = exc.errors()
        for err in errors:
            if "ctx" in err and "error" in err["ctx"]:
                err["ctx"]["error"] = str(err["ctx"]["error"])

        logger.warning(
            f"ValidationError at {request.method} {request.url.path} - {errors}"
        )
        return JSONResponse(
            status_code=422,
            content={"detail": errors},
        )
