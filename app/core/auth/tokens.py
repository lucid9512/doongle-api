"""
JWT 토큰 생성 및 검증 유틸리티

- Access / Refresh 토큰을 각각 생성 및 검증하는 함수 제공
- PyJWT 기반으로 HS256 서명 및 만료 검증 수행
- core 레벨의 순수 유틸리티로, 비즈니스 로직(Service)과 분리됨
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from app.core.config import settings
import logging


# ============================================================
# 1. 내부 유틸리티
# ============================================================
def _now() -> datetime:
    """
    현재 UTC 시간을 반환.
    JWT의 iat(issued at), exp(expiration) 필드 계산에 사용.
    """
    return datetime.now(timezone.utc)


def _create_token(data: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    """
    공통 JWT 생성 로직 (Access/Refresh 모두 사용)
    
    Args:
        data: 토큰에 포함할 사용자 정보 (예: {"sub": user_id})
        expires_delta: 만료 시간 (timedelta)
        token_type: "access" 또는 "refresh"

    Returns:
        서명된 JWT 문자열
    """
    payload = data.copy()
    payload.update({
        "type": token_type,
        "iat": int(_now().timestamp()),
        "exp": int((_now() + expires_delta).timestamp()),
        "aud": "fastapi-users:auth",
    })

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ============================================================
# 2. Access Token 생성
# ============================================================
def create_access_token(
    data: Dict[str, Any],
    expires: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
) -> str:
    """
    Access Token 생성

    Args:
        data: 토큰에 포함할 사용자 정보 (예: {"sub": user_id})
        expires: 만료 기간 (기본 1시간)

    Returns:
        str: 서명된 Access Token (JWT 문자열)
    """
    return _create_token(data, expires, token_type="access")


# ============================================================
# 3. Refresh Token 생성
# ============================================================
def create_refresh_token(
    data: Dict[str, Any],
    expires: timedelta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
) -> str:
    """
    Refresh Token 생성

    Args:
        data: 토큰에 포함할 사용자 정보 (예: {"sub": user_id})
        expires: 만료 기간 (기본 7일)

    Returns:
        str: 서명된 Refresh Token (JWT 문자열)
    """
    return _create_token(data, expires, token_type="refresh")


# ============================================================
# 4. JWT 토큰 검증
# ============================================================
def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰 검증

    Args:
        token (str): 클라이언트로부터 전달받은 JWT 문자열

    Returns:
        Optional[Dict[str, Any]]:
            - 유효한 경우: 디코딩된 payload(dict)
            - 무효하거나 만료된 경우: None

    예외 처리:
        - ExpiredSignatureError: 토큰 만료
        - InvalidTokenError: 구조 또는 서명 불일치
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], audience="fastapi-users:auth")
        return payload
    except jwt.ExpiredSignatureError:
        logging.error("ExpiredSignatureError")
        return None
    except jwt.InvalidTokenError:
        logging.error("InvalidTokenError")
        return None
    except Exception:
        logging.error("Exception")
        return None
