from fastapi_users import schemas
from datetime import datetime

class RoleSchema(schemas.BaseModel):
    """Role 직렬화 스키마"""
    id: int
    name: str
    description: str | None
    
    class Config:
        from_attributes = True  # ORM -> Pydantic 변환 허용


class UserSchema(schemas.BaseUser[int]):
    """User 직렬화 스키마"""
    id: int
    user_id: str
    name: str
    email: str
    is_active: bool
    is_superuser: bool
    is_pwreset: bool
    profile_img: str | None
    language: str
    theme: str
    created_at: datetime
    updated_at: datetime
    roles: list[RoleSchema] = [] # Role 이 여러 개가 될 수도 있음
    
    class Config:
        from_attributes = True  # ORM -> Pydantic 변환 허용
