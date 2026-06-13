from logging.config import fileConfig
import sys
import pathlib
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# 프로젝트 루트 경로 추가
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app.models import Base
from app.core.config import settings
from app import models  # noqa: F401  (자동 import 트리거)

# Alembic Config 객체
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 자동 생성 마이그레이션을 위한 메타데이터 대상
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """'offline' 모드에서 마이그레이션 실행"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """마이그레이션 실행"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """'online' 모드에서 마이그레이션 실행 (async engine)"""
    connectable = create_async_engine(settings.DATABASE_URL, echo=True)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
