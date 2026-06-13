"""
sqladmin 통합 (현재 비활성)

- `init_admin(app)` 호출 시 `/admin` 경로에 Admin UI 가 노출됩니다.
- 인증이 필요하면 `sqladmin.AuthenticationBackend` 를 구현해 `Admin(authentication_backend=...)` 에 전달하세요.
- 활성화하려면 `app/main.py` 에 `from app.admin import init_admin; init_admin(app)` 를 추가합니다.
"""
from fastapi import FastAPI
from sqladmin import Admin

from app.core.db import engine
from .views import UserAdmin, RoleAdmin


def init_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(RoleAdmin)
    return admin
