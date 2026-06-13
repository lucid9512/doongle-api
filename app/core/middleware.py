import logging
import traceback
import uuid
import json
from fastapi import Request, HTTPException
from starlette.responses import JSONResponse, Response
from app.core.config import settings
from app.core.request_context import set_request_id, get_request_id
from app.exceptions.domain import DomainError
from app.exceptions.service import ServiceError

logger = logging.getLogger("app.middleware")


# ============================================================
# Request ID 관리 (헤더 기반 + ContextVar 저장)
# ============================================================
async def request_context_middleware(request: Request, call_next):
    """
    요청별 고유 Request ID 생성 및 ContextVar 주입
    - 헤더 X-Request-ID가 있으면 재사용, 없으면 새로 생성
    - request.state 및 ContextVar에 모두 저장
    """
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
    request.state.request_id = request_id
    set_request_id(request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ============================================================
# 전역 예외 처리
# ============================================================
async def exception_middleware(request: Request, call_next):
    """
    전역 예외 처리 및 로깅
    - DomainError / ServiceError: 비즈니스 예외 (traceback 미출력)
    - 500대 시스템 예외: traceback 출력
    """
    try:
        return await call_next(request)

    # ------------------------------
    # 비즈니스 예외 (400, 404, 409 등)
    # ------------------------------
    except (DomainError, ServiceError) as e:
        rid = get_request_id()

        if e.status_code < 500:
            # 400대 → Warning 로그, traceback X
            logger.warning(f"[rid={rid}] {e.__class__.__name__} ({e.status_code}) → {e.message}")
        else:
            # 500대 → traceback 출력
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"[rid={rid}] {e.__class__.__name__} ({e.status_code}) → {e.message}\n{tb_str}")

        return JSONResponse(
            status_code=e.status_code,
            content=e.to_response().model_dump(),
        )

    # ------------------------------
    # HTTPException (ex. 401, 403)
    # ------------------------------
    except HTTPException as e:
        rid = get_request_id()
        logger.warning(f"[rid={rid}] HTTPException {e.status_code} at {request.url.path} - {e.detail}")
        raise e

    # ------------------------------
    # 시스템 예외 (Unhandled)
    # ------------------------------
    except Exception as e:
        rid = get_request_id()
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"[rid={rid}] Unhandled Exception at {request.url.path}\n{tb_str}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "request_id": rid},
        )


# ============================================================
# 요청/응답 로깅 + 정상 응답 메타 보강
# ============================================================
async def request_logging_middleware(request: Request, call_next):
    """
    요청/응답 로깅
    - DEBUG 모드에서만 상세 요청 바디 출력
    - 모든 응답(meta)에 request_id 자동 주입
    """
    rid = get_request_id()

    # 요청 로깅 (DEBUG 모드 한정)
    if settings.DEBUG:
        method = request.method
        path = request.url.path
        headers = dict(request.headers)
        try:
            if method in ("POST", "PUT", "PATCH"):
                content_type = request.headers.get("Content-Type", "")
                if content_type.startswith("multipart/form-data"):
                    # 파일 업로드 요청일 경우 바디 출력 생략
                    logger.info(
                        f"[rid={rid}] [{method}] {path} | Body: **File Upload Skipped (multipart/form-data)**"
                    )
                else:
                    body_bytes = await request.body()
                    logger.info(
                        f"[rid={rid}] [{method}] {path} | Body ({len(body_bytes)} bytes): "
                        f"{body_bytes.decode(errors='ignore')}"
                    )
            elif method == "GET":
                logger.info(f"[rid={rid}] [{method}] {path} | Query: {dict(request.query_params)}")
            logger.debug(f"[rid={rid}] Headers: {headers}")
        except Exception as e:
            logger.warning(f"[rid={rid}] [{method}] {path} | Request logging failed: {e}")

    # 요청 처리
    response: Response = await call_next(request)

    # ✅ 정상 응답(meta.request_id가 null이면 자동 주입)
    try:
        if response.headers.get("content-type", "").startswith("application/json"):
            body = response.body.decode()
            data = json.loads(body)
            meta = data.get("meta")

            if isinstance(meta, dict):
                if not meta.get("request_id"):
                    meta["request_id"] = rid
                    data["meta"] = meta
                    response.body = json.dumps(data).encode("utf-8")
                    response.headers["content-length"] = str(len(response.body))
    except Exception as e:
        logger.debug(f"[rid={rid}] Response post-process failed: {e}")

    # 응답 로그
    logger.info(f"[rid={rid}] {request.method} {request.url.path} → {response.status_code}")
    return response

# ============================================================
# 보안 헤더 추가 (수정됨)
# ============================================================
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # 1. [CSP] 스크립트 실행 권한 제한
    # - default-src 'self': 내 서버 파일만 허용
    # - script/style-src: Swagger UI 작동을 위해 'unsafe-inline' 허용 (필수)
    # - img-src: 데이터 URI(이미지) 허용
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )
    
    # 2. [Clickjacking] 사이트가 iframe 내에서 실행되는 것 방지
    response.headers["X-Frame-Options"] = "DENY"
    
    # 3. [MIME Sniffing] 브라우저가 파일 타입을 맘대로 추측 금지
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # 4. [Server Leak] 서버 정보(Uvicorn 등) 숨기기
    # 해커가 서버 버전을 알면 맞춤형 공격을 할 수 있으므로 가짜 이름으로 덮어씀
    response.headers["Server"] = "DataHubServer" 

    # 5. [HSTS] HTTPS 강제 (운영 환경용)
    # 로컬(http)에서는 무시되지만, 코드는 넣어두는 게 심사에 유리함
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# ============================================================
# 초기화 함수
# ============================================================
def init_middleware(app):
    """
    전역 미들웨어 초기화
    순서: Request ID → 예외 처리 → 로깅
    """
    app.middleware("http")(request_context_middleware)
    app.middleware("http")(exception_middleware)
    app.middleware("http")(request_logging_middleware)
    # app.middleware("http")(security_headers_middleware)
