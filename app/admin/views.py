import logging
from sqladmin import ModelView
from wtforms import PasswordField, SelectField
from markupsafe import Markup
from sqlalchemy import select, delete

from app.models.user import User, Role, UserRole
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# 비밀번호 해싱기 (argon2 + bcrypt 지원)
hasher = PasswordHash([Argon2Hasher(), BcryptHasher()])


class UserAdmin(ModelView, model=User):
    # 리스트 화면 표시 컬럼 (hashed_password는 아예 제외)
    column_list = [User.id, User.user_id, User.name, User.email, User.is_active, User.created_at]

    # 폼에서 hashed_password 제외
    form_excluded_columns = [User.hashed_password]

    # 모델 컬럼만 rules에 포함 (password는 모델에 없으므로 빼야 함)
    form_create_rules = ("user_id", "name", "email", "is_active", "role_id")
    form_edit_rules   = ("name", "email", "is_active", "is_superuser", "role_id")

    form_overrides = {
        "role_id": SelectField,  # role_id는 가상 단일 선택 필드
    }

    # 폼 정의 (가상 필드 추가)
    async def scaffold_form(self, rules=None):
        Form = await super().scaffold_form(rules)

        # 비밀번호 필드 (가상)
        if not hasattr(Form, "password"):
            Form.password = PasswordField("Password")

        # Role 필드 (가상)
        if not hasattr(Form, "role_id"):
            Form.role_id = SelectField("Role", coerce=int)

        # Role 목록 채우기
        async with self.session_maker() as session:
            roles = (await session.execute(select(Role))).scalars().all()
        Form.role_id.kwargs["choices"] = [(r.id, r.name) for r in roles]

        return Form



    # 저장 직전 비밀번호 & Role 처리
    async def on_model_change(self, data, model, is_created, request):
        # Email 보장
        email = data.get("email")
        if not email:
            raise ValueError("Email은 필수 입력 값입니다.")
        model.email = email

        # 비밀번호 처리 (가상 필드 → pop으로 제거)
        password = data.pop("password", None)
        if is_created:
            if not (password and password.strip()):
                raise ValueError("신규 생성 시 비밀번호는 필수입니다.")
            model.hashed_password = hasher.hash(password)
        elif password and password.strip():
            model.hashed_password = hasher.hash(password)

        # Role 처리 (가상 필드 → pop으로 제거)
        role_id = data.pop("role_id", None)
        if not role_id:
            raise ValueError("Role은 반드시 선택해야 합니다.")

        # Role 조회
        async with self.session_maker() as s2:
            role = await s2.get(Role, int(role_id))

        # is_superuser 값 계산
        is_superuser = True if role and role.name.lower() == "admin" else False

        # 둘 다 세팅해서 확실히 반영
        data["is_superuser"] = is_superuser
        model.is_superuser = is_superuser

        # UserRole 매핑
        if is_created:
            # 생성 시: flush로 model.id 확보
            session = request.state.session
            await session.flush()
            async with self.session_maker() as s2:
                s2.add(UserRole(user_id=model.id, role_id=int(role_id)))
                await s2.commit()
        else:
            # 수정 시: 기존 매핑 삭제 후 새 Role 추가
            async with self.session_maker() as s2:
                await s2.execute(delete(UserRole).where(UserRole.user_id == model.id))
                s2.add(UserRole(user_id=model.id, role_id=int(role_id)))
                await s2.commit()


    # 안내 문구 추가
    async def render_form(self, *args, **kwargs):
        form_html = await super().render_form(*args, **kwargs)
        notice = Markup('<p style="color:red;">* 비밀번호 입력 시에만 변경 됩니다.</p>')
        return notice + form_html


class RoleAdmin(ModelView, model=Role):
    column_list = [Role.id, Role.name, Role.description]

    form_create_rules = ("name", "description")
    form_edit_rules   = ("name", "description")
