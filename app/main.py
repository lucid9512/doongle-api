from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi_pagination import add_pagination


from app.core.config import settings
from app.core.hooks import lifespan, register_all_exception_handlers
from app.core.middleware import init_middleware
from app.core.logging_config import setup_logging
from app.apis.v1 import router as api_v1_router


# ============================================================
# 1. FastAPI 앱 생성
# ============================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    debug=settings.DEBUG,
    openapi_url="/openapi.json",
    docs_url=None,
    lifespan=lifespan,  # ✅ hooks.py의 lifespan 연결
)

# ============================================================
# 2. 로깅 및 미들웨어 초기화
# ============================================================
setup_logging()
init_middleware(app)

# ============================================================
# 3. hooks 초기화 (예외/로깅/pagination)
# ============================================================
register_all_exception_handlers(app)

# FE CORSMiddleware 설정 (.env 의 CORS_ORIGINS 로 관리)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,         # 쿠키/Authorization 헤더 허용
    allow_methods=["*"],            # 모든 메서드 허용 (GET, POST 등)
    allow_headers=["*"],            # 모든 헤더 허용
)

# SessionMiddleware (sqladmin 등 세션 필요 시)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ADMIN_SECRET_KEY,
    same_site="lax",
    https_only=False,
)

# ============================================================
# 3. 라우터 등록
# ============================================================
app.include_router(api_v1_router, prefix="/api/v1")
add_pagination(app) # 라우터 등록 이후

# ============================================================
# 5. Swagger UI 및 기본 경로
# ============================================================
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_ui_parameters={"persistAuthorization": True},
    )

@app.get("/")
def read_root():
    return {"message": "Hello, Dongle!"}
