from fastapi_users.db import SQLAlchemyBaseUserTable
import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey
from app.models.base import BaseModel


class UserRole(BaseModel):
    """
    User ↔ Role 의 M:N 매핑 테이블.
    현재는 1user-1role 만 허용 (FE/Service 단에서 제어).
    """
    __tablename__ = "roles_users"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=True)

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="roles_users",
        primaryjoin=lambda: Role.id == UserRole.role_id,
        secondaryjoin=lambda: UserRole.user_id == User.id,
        back_populates="roles",
    )


class User(SQLAlchemyBaseUserTable[int], BaseModel):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # 실제 로그인 아이디
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_pwreset: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=sqlalchemy.true())
    profile_img: Mapped[str] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="eng")
    theme: Mapped[str] = mapped_column(String(20), nullable=False, server_default="basic")

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="roles_users",
        primaryjoin=lambda: User.id == UserRole.user_id,
        secondaryjoin=lambda: UserRole.role_id == Role.id,
        back_populates="users",
        lazy="selectin",
    )
