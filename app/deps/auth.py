from typing import Optional, Type, AsyncGenerator
from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.deps.db import get_db
from app.models.user import User
from app.services.auth.manager import get_user_manager, UserDB
from app.core.auth.authentication import auth_backend


async def get_user_db(session: AsyncSession = Depends(get_db)) -> AsyncGenerator[UserDB, None]:
    """
    FastAPI Users용 DB 의존성
    """
    yield UserDB(session, User)


# ============================================================
# FastAPI Users 기반 인증 주입
# ============================================================
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user()
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(superuser=True)
