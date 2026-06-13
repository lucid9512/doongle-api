"""
데이터베이스 초기화 및 세션 관리 모듈

- SQLAlchemy 비동기(Async) 엔진 및 세션 설정
- FastAPI 의존성 주입(get_db)으로 트랜잭션 단위 세션 관리
- asyncpg 드라이버를 사용하는 PostgreSQL 전용 구성
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ============================================================
# 1. 비동기 데이터베이스 엔진 설정
# ============================================================
# 예시 URL 형식:
#   postgresql+asyncpg://user:password@localhost:5432/dongle
# 반드시 "asyncpg" 드라이버를 사용해야 Async I/O로 동작함
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    future=True,
)

# ============================================================
# 2. 세션 팩토리 생성
# ============================================================
# async_sessionmaker는 비동기 세션 생성용 팩토리 함수
# expire_on_commit=False → commit 후 객체 속성 만료 방지
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, autoflush=False, autocommit=False
)


AsyncSessionLocal = async_session_maker