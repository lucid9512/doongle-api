from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Depends에서 사용할 DB 세션 의존성
    """
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()
