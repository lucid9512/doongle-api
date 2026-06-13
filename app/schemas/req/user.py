import logging
import re
from fastapi_users import schemas
from app.schemas.__base__ import VaModelReq
from pydantic import field_validator, model_validator
from datetime import datetime
from app.exceptions import DomainError, UnprocessableEntityError

logger = logging.getLogger("app")

# ============================================================
# Create
# ============================================================
class RoleCreateReq(VaModelReq):
    """역할 생성 요청 스키마"""
    id: int
    name: str
    description: str | None

class UserRoleCreateReq(VaModelReq):
    """사용자 + 역할 생성 요청 스키마"""
    user_id: int
    role_id: int

class UserCreateReq(schemas.BaseUserCreate):
    """사용자 생성 요청 스키마"""
    user_id: str
    name: str
    email: str
    password: str
    role_id: int | None = None
    
    # password 유효성 검사는 당장 없음
    
    # Email 유효성 검사
    @field_validator("email")
    @classmethod
    def valid_email(cls, val):
        if val is None:
            return val
        
        # 이메일 길이 검사
        if len(val) > 254:
            raise UnprocessableEntityError(message="EMAIL_TOO_LONG")
        
        # 정규 표현식 패턴 적용
        if not re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").match(val):
            raise UnprocessableEntityError(message="INVALID_EMAIL")
        
        return val


# ============================================================
# Update
# ============================================================
class UserUpdateReq(schemas.BaseUserUpdate):
    """
    사용자 수정 요청 모델
    """
    is_superuser: bool | None = None
    is_verified: bool | None = None
    
    name: str | None = None
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role_id: int | None = None
    
    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, data):
        if not isinstance(data, dict):
            return data

        fields = [
            "name", "email", "is_active", "role_id", "password"
        ]

        # 전달된 모든 필드가 None이면 예외 발생
        if all(data.get(k) is None for k in fields):
            raise DomainError("ALL_FIELD_BLANK")
        return data

class UserPasswordReq(schemas.BaseUserUpdate):
    """사용자 비밀번호 요청 스키마"""
    # fastapi users에 의한 에러 방지
    is_superuser: bool | None = None
    is_verified: bool | None = None
    password: str # 필수
    is_pwreset: bool | None = None
