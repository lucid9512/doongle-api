import typer
import asyncio
from sqlalchemy import select
from app.core.db import async_session_maker
from app.models.user import Role, User, UserRole
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher


cli = typer.Typer()
# Argon2 + Bcrypt 둘 다 지원 (fastapi-users 기본 설정과 일치)
hasher = PasswordHash([Argon2Hasher(), BcryptHasher()])


@cli.command()
def create_roles(names: list[str] = typer.Argument(..., help="생성할 Role 이름들")):
    """
    여러 Role 생성
    예:
      poetry run python -m app.cli create-roles admin manager user
    """
    async def _create():
        async with async_session_maker() as session:
            for role_name in names:
                result = await session.execute(select(Role).where(Role.name == role_name))
                existing = result.scalar_one_or_none()
                if existing:
                    print(f"Role '{role_name}' 이미 존재함")
                    continue

                role = Role(name=role_name)
                session.add(role)
                print(f"Role 생성됨: {role_name}")

            await session.commit()

    asyncio.run(_create())


@cli.command()
def create_user(
    user_id: str = typer.Argument(..., help="사용자 아이디"),
    name: str = typer.Argument(..., help="사용자 이름"),
    email: str = typer.Argument(..., help="사용자 이메일"),
    role: str = typer.Argument(..., help="부여할 Role (하나만)"),
    password: str = typer.Option(
        ...,
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="비밀번호 (입력 시 화면에 표시되지 않음)",
    ),
):
    """
    새 User 생성 + Role 매핑

    비밀번호는 위치 인자 대신 인터랙티브 prompt 로 입력받아 shell history / `ps` 노출을 피합니다.

    사용 예:
      poetry run python -m app.cli create-user user_id name email@example.com admin
    """
    async def _create():
        async with async_session_maker() as session:
            is_superuser_flag = role.strip().lower() == "admin"
            user = User(
                user_id=user_id,
                name=name,
                email=email,
                hashed_password=hasher.hash(password),
                is_active=True,
                is_superuser=is_superuser_flag,
            )
            session.add(user)
            await session.flush()  # user.id 확보

            result = await session.execute(select(Role).where(Role.name == role))
            role_obj = result.scalar_one_or_none()
            if not role_obj:
                print(f"Role '{role}' 이(가) 존재하지 않습니다. 먼저 create-roles 로 생성하세요.")
                await session.rollback()
                return

            session.add(UserRole(user_id=user.id, role_id=role_obj.id))
            await session.commit()
            print(f"User 생성됨: {user_id}({name}), Role={role}")

    asyncio.run(_create())


if __name__ == "__main__":
    cli()
