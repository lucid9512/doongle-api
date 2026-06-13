"""
AuthService
- Access / Refresh 토큰 발급 및 재발급 로직 관리
- Refresh Token은 HttpOnly 쿠키에 저장
"""
import logging
from datetime import timedelta
from fastapi import Response
from app.core.auth.tokens import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.config import settings
from app.exceptions import DomainError, ObjectNotFoundError, UnauthenticatedError

logger = logging.getLogger(__name__)

class AuthService:
    # ------------------------------------------------------------
    # 로그인: Access / Refresh 발급 및 쿠키 저장
    # ------------------------------------------------------------
    @staticmethod
    async def login(response: Response, user_manager, form_data) -> dict:
        """
        로그인 성공 시:
        - Access Token (JSON 응답)
        - Refresh Token (HttpOnly Cookie)
        """
        logger.info(f"[AuthService] Login request")
        
        user = await user_manager.authenticate(form_data)
        if not user:
            logger.warning(f"[AuthService] Login fail : User not found")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        await user_manager.user_db.session.refresh(user)  # 세션 동기화 (optional)
        
        # 권한 정보 조회 (필요하면 추가)
        # roles = [r.name for r in user.roles] if hasattr(user, "roles") else []

        access_token = create_access_token(
            {
                "sub": str(user.id),
                # "roles": roles,
                # "is_superuser": user.is_superuser
            },
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(
            {"sub": str(user.id)},
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        
        # Refresh Token을 HttpOnly 쿠키에 저장
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,  # 운영 HTTPS에서는 True로 변경
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )
        
        logger.info(f"[AuthService] Login successfully")

        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "is_pwreset": user.is_pwreset # 비밀번호 초기화 여부
        }

    # ------------------------------------------------------------
    # Refresh: 쿠키에 있는 Refresh Token으로 Access 재발급
    # ------------------------------------------------------------
    @staticmethod
    async def refresh(refresh_token: str, user_manager) -> dict:
        """
        Refresh Token 검증 후 새로운 Access Token 발급
        """
        logger.info(f"[AuthService] Refresh token refresh request")
        
        if not refresh_token:
            logger.warning(f"[AuthService] Refresh token not found")
            # Token 부재 -> 401
            raise UnauthenticatedError(message="REFRESH_TOKEN_NOT_FOUND_ERROR")

        # refresh token 검증
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning(f"[AuthService] Invalid Refresh token")
            raise DomainError(message="INVALID_REFRESH_TOKEN_ERROR")

        # token에서 정보 추출
        id = payload.get("sub")
        user = await user_manager.get(int(id))
        if not user:
            logger.warning(f"[AuthService] User not found")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        if not user.is_active:
            logger.warning(f"[AuthService] User is inactive")
            raise DomainError(message="USER_INACTIVE_ERROR")
        await user_manager.user_db.session.refresh(user)  # 세션 동기화 (optional)
        
        # 권한 정보 조회 (필요하면 추가)
        # roles = [r.name for r in user.roles] if hasattr(user, "roles") else []
        
        new_access_token = create_access_token(
            {
                "sub": str(user.id),
                # "roles": roles,
                # "is_superuser": user.is_superuser
            },
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        
        logger.info(f"[AuthService] Refresh token refresh successfully")
        
        return {"access_token": new_access_token, "token_type": "bearer"}

    # ------------------------------------------------------------
    # 로그아웃: Refresh 쿠키 삭제
    # ------------------------------------------------------------
    @staticmethod
    async def logout(response: Response) -> bool:
        """
        Refresh Token 쿠키 삭제 (로그아웃 처리)
        """
        logger.info(f"[AuthService] Logout request")
        
        response.delete_cookie("refresh_token")
        logger.info(f"[AuthService] Logout successfully")
        
        return True
