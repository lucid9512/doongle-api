"""
사용자 주입 및 접근 권한 의존성
"""
import logging
from fastapi import Depends
from app.deps.auth import current_active_user
from app.models.user import User
from app.exceptions import ForbiddenError, ObjectNotFoundError

logger = logging.getLogger(__name__)

def require_user(roles: list[str] | None = None):
    """
    인증된 사용자 + 선택적 역할(role) 검증
    - JWT 인증은 current_active_user에서 이미 처리됨
    - roles 지정 시 해당 역할만 접근 허용
      예: Depends(require_user(["staff", "admin"]))
    """
    async def _verify(user: User = Depends(current_active_user)) -> User:
        # 사용자 검증
        if not user:
            logger.error("[Access Denied] User Not Found")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")

        # Role 검증
        if roles:
            user_roles = [r.name for r in user.roles] if user.roles else []
            if not any(role in roles for role in user_roles):
                logger.error("[Permission Denied]")
                raise ForbiddenError(message="UNAUTHORIZE_USER")

        return user

    return _verify
