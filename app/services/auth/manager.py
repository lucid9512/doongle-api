import logging
from fastapi import Depends
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import random, string

from app.models.user import User, Role
from app.core.config import settings
from app.core.db import AsyncSessionLocal           # ✅ deps 대신 core에서 직접 import
from app.schemas.req.user import UserCreateReq, UserRoleCreateReq
from app.schemas.model.user import UserSchema
from app.schemas.req.user import UserPasswordReq
from app.services.user import RoleService, UserService
from app.exceptions import ObjectNotFoundError, DatabaseCommitError, DomainError, DuplicateError

logger = logging.getLogger(__name__)

# ============================================================
# 1. UserDB (FastAPI Users용 DB adapter)
# ============================================================
class UserDB(SQLAlchemyUserDatabase[User, int]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, login: str):
        """
        기존 email 필드 대신 user_id를 사용하기 위한 함수 오버라이딩
        user_id 기반 로그인 지원
        """
        if not login:
            return None
        stmt = select(User).where(func.lower(User.user_id) == func.lower(login))
        res = await self.session.execute(stmt)
        return res.scalars().first()


# ============================================================
# 2. UserManager
# ============================================================
class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY
    
    def generate_password(self) -> str:
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = string.punctuation
        length = random.randint(12, 15)
        all_chars = lowercase + uppercase + digits + symbols
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(symbols),
        ]
        password += random.choices(all_chars, k=length - len(password))
        random.shuffle(password)
        return "".join(password)

    # ---------------------------------------------
    # CREATE
    # ---------------------------------------------
    async def create(
        self,
        user_create: UserCreateReq,
        safe: bool = False,
        request=None,
    ) -> UserSchema:
        """
        User manager create 함수 오버라이딩
        """
        safe = False  # Role 부여 시 안전 모드 비활성화
        
        # 세션 등록
        session = self.user_db.session
        user_service = UserService(session)
        role_service = RoleService(session)
        
        logger.info(f"[UserManager] User Create request")
        
        # user_id 중복 검사
        if await user_service.check_by_user_id(user_create.user_id):
            logger.error(f"[UserManager] User already exists")
            raise DuplicateError(message="USERID_DUPL_ERROR")
        
        # email 중복 검사
        if await user_service.check_by_email(user_create.email):
            logger.error(f"[UserManager] User Email already exists")
            raise DuplicateError(message="EMAIL_DUPL_ERROR")

        role_id = user_create.role_id
        # role이 "admin" 시 is_superuser 값을 True로 변경 (fastapi users)
        cur_role = await role_service.get(role_id)
        if cur_role and cur_role.name == "admin":
            user_create = user_create.model_copy(update={"is_superuser": True})
        if cur_role is None:
            logger.error(f"[UserManager] Role not found")
            raise ObjectNotFoundError(message="ROLE_NOT_FOUND_ERROR")
        
        try:
            # User 생성
            new_user = UserCreateReq(**user_create.model_dump(exclude={"role_id"}))
            user = await super().create(new_user, safe, request)
            logger.info(f"[UserManager] User Create successfully (user_id={user.user_id})")
        except Exception as e:
            logger.error(f"[UserManager] User Create fail : {e}")
            raise DatabaseCommitError(message="DB_COMMIT_ERROR")

        try:
            # UserRole 추가 (Role+User 매핑)
            await role_service.create(UserRoleCreateReq(user_id=user.id, role_id=role_id),)
            logger.info(f"[UserManager] UserRole Create successfully (user_id={user.user_id})")
        except Exception as e:
            logger.error(f"[UserManager] UserRole Create fail : {e}")
            raise DatabaseCommitError(message="DB_COMMIT_ERROR")
        
        return UserSchema.model_validate(user).model_dump()
    
    
    # ---------------------------------------------
    # READ
    # ---------------------------------------------
    async def verify_pw(
        self,
        user,
        pw_update_req: UserPasswordReq,
        safe: bool
    ) -> bool:
        """
        User manager 비밀번호 검증 함수
        """
        password_hash = PasswordHash((Argon2Hasher(),))
        password_helper = PasswordHelper(password_hash)
        is_correct, _ = password_helper.verify_and_update(
            plain_password=pw_update_req.password,
            hashed_password=user.hashed_password
        )
        return is_correct
    
    
    # ---------------------------------------------
    # UPDATE
    # ---------------------------------------------
    async def change_pw(
        self,
        user_id: str,
        pw_update_req: UserPasswordReq
    ) -> bool:
        """
        User manager 비밀번호 커스텀 함수
        
        fastapi users 스키마 상속으로 swagger 에 불필요한 body 요소가 존재함
        수정 가능한 요소
        - password
        """
        session = self.user_db.session
        
        logger.info(f"[UserManager] User pw change request")
        
        # 사용자 조회
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        if not user:
            logger.warning(f"[UserManager] User not found")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        
        try:
            # 비밀번호 갱신
            await super().update(pw_update_req, user, safe=False)
            logger.info(f"[UserManager] User pw change successfully (user_id={user.user_id})")
            return True
        except Exception as e:
            logger.warning(f"[UserManager] User pw change fail : {e}")
            raise DatabaseCommitError(message="UserManager Error : Database commit failed")


# ============================================================
# 3. Dependency 주입 함수
# ============================================================
async def get_user_manager():
    """
    FastAPI Users용 UserManager 의존성
    """
    async with AsyncSessionLocal() as session:
        user_db = UserDB(session)
        yield UserManager(user_db)
