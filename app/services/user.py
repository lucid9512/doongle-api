import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select, update, or_
from sqlalchemy.orm import selectinload
from app.models.user import User, Role, UserRole
from app.schemas.model.user import UserSchema, RoleSchema
from app.schemas.req.user import UserUpdateReq
from app.exceptions import DatabaseCommitError, ObjectNotFoundError, DuplicateError

logger = logging.getLogger(__name__)

class RoleService:
    """Role 도메인 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db


    # ---------------------------
    # CREATE
    # ---------------------------
    async def create(self, info):
        """
        UserRole 관계 생성
        """
        logger.info(f"[RoleService] UserRole Create request")
        user_role = UserRole(user_id=info.user_id, role_id=info.role_id)
        
        try:
            self.db.add(user_role)
            await self.db.commit()
            await self.db.refresh(user_role)
            logger.info(f"[RoleService] UserRole Create successfully (user_id={info.user_id}, role_id={info.role_id})")
        except Exception as e:
            logger.exception(f"[RoleService] DB commit failed while creating UserRole : {e}")
            await self.db.rollback()
            raise DatabaseCommitError(message="Role Servcie Error : Database commit failed")


    # ---------------------------
    # READ
    # ---------------------------
    async def get(self, role_id: int) -> Role | None:
        return await self.db.get(Role, role_id)


class UserService:
    """User 도메인 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db


    # ---------------------------
    # CREATE
    # ---------------------------


    # ---------------------------
    # READ
    # ---------------------------
    async def get(self, params) -> Page[UserSchema]:
        """
        User 전체 조회
        """
        logger.info(f"[UserService] User list Get request")
        
        stmt = select(User).options(selectinload(User.roles)).order_by(User.id)
        result = await paginate(self.db, stmt, params=params)
        # paginate를 사용하기 위해 결과를 Pydantic 객체로 변환
        result.items = [UserSchema.model_validate(user) for user in result.items]
        logger.info(f"[UserService] User list Get successfully")
        
        return result.model_dump()
    
    async def get_role(self, params) -> Page[RoleSchema]:
        """
        Role 전체 조회
        """
        logger.info(f"[UserService] Role list Get request")
        
        stmt = select(Role).order_by(Role.id)
        result = await paginate(self.db, stmt, params=params)
        # paginate를 사용하기 위해 결과를 Pydantic 객체로 변환
        result.items = [RoleSchema.model_validate(role) for role in result.items]
        logger.info(f"[UserService] Role list Get successfully")
        
        return result.model_dump()
    
    async def get_through_keyword(self, params, keyword: str) -> Page[UserSchema]:
        """
        키워드를 통한 User 조회
        """
        logger.info(f"[UserService] User list Get through keyword request")
        filters = []

        filters.append(
            or_(
                User.user_id.contains(keyword),
                User.name.contains(keyword),
                User.email.contains(keyword),
                User.roles.any(Role.name.contains(keyword))
            )
        )
        
        stmt = select(User).where(or_(*filters)).options(selectinload(User.roles)).order_by(User.id)
        result = await paginate(self.db, stmt, params=params)
        # paginate를 사용하기 위해 결과를 Pydantic 객체로 변환
        result.items = [UserSchema.model_validate(user) for user in result.items]
        logger.info(f"[UserService] User list Get successfully")
        
        return result.model_dump()
    
    async def get_by_user_id(self, user_id: int) -> UserSchema | None:
        """
        UserID로 조회
        """
        logger.info(f"[UserService] User Get request")
        
        user = await self.db.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.user_id == user_id)
        )
        
        if not user:
            logger.warning(f"[UserService] User Get fail (user_id={user_id})")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        
        logger.info(f"[UserService] User Get successfully (user_id={user.user_id})")
        return UserSchema.model_validate(user).model_dump()
    
    async def check_by_user_id(self, user_id: int) -> bool:
        """
        UserID로 중복 조회
        """
        logger.info(f"[UserService] UserID Check request")
        
        result = await self.db.execute(
            select(User)
            .where(User.user_id == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            logger.warning(f"[UserService] UserID Check fail (user_id={user_id})")
            return False
        
        logger.info(f"[UserService] UserID Check successfully (user_id={user.user_id})")
        return True
    
    async def get_by_email(self, email: str) -> UserSchema | None:
        """
        User Email로 조회
        """
        logger.info(f"[UserService] User email Get request")
        
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == email)
        )
        user = result.scalars().first()
        
        if not user:
            logger.info(f"[UserService] User email Get fail (user_email={email})")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        
        logger.info(f"[UserService] User email Get successfully (user_email={user.email})")
        return UserSchema.model_validate(user).model_dump()
    
    async def check_by_email(self, email: str) -> bool:
        """
        User Email로 중복 체크
        """
        logger.info(f"[UserService] User email Check request")
        
        user = await self.db.scalar(
            select(User)
            .where(User.email == email)
        )
        
        if not user:
            logger.info(f"[UserService] User email Check fail (user_email={email})")
            return False
        
        logger.info(f"[UserService] User email Check successfully (user_email={user.email})")
        return True
    
    
    # ---------------------------
    # UPDATE
    # ---------------------------
    async def update(self, user_id: str, new_input: UserUpdateReq) -> UserSchema | None:
        """
        UserID로 수정
        """
        logger.info(f"[UserService] User Update request")
        
        # 사용자 검증
        user = await self.db.scalar(select(User).where(User.user_id == user_id))
        if not user:
            logger.exception(f"[UserService] User not found")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        
        # Role 변경 (검증은 FE에서 했다는 가정)
        old_role_name = user.roles[0].name
        new_role_id = new_input.role_id
        if new_role_id:
            new_role = await self.db.get(Role, new_role_id)
            new_role_name = new_role.name
            
            # fastapi_users 의 is_superuser 수동 변경
            if old_role_name == "admin" and new_role_name == "user":
                # Admin -> User
                setattr(user, "is_superuser", False)
            elif old_role_name == "user" and new_role_name == "admin":
                # User -> Admin
                setattr(user, "is_superuser", True)
            
            # UserRole 갱신
            await self.db.execute(update(UserRole).where(UserRole.user_id == user.id).values(role_id=new_role_id))
        
        # 이메일 중복 체크
        if await self.db.scalar(
            select(User)
            .where(User.email == new_input.email)
        ):
            logger.warning("[UserManager] User email already exists")
            raise DuplicateError(message="EMAIL_DUPL_ERROR")
        
        # 사용자 갱신
        for var, value in vars(new_input).items():
            setattr(user, var, value) if value is not None else None
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"[UserService] User Update successfully")
            
            return UserSchema.model_validate(user).model_dump()
        except Exception as e:
            logger.exception(f"[UserService] DB commit failed while updating User : {e}")
            await self.db.rollback()
            raise DatabaseCommitError(message="DB_COMMIT_ERROR")
    
    
    # ---------------------------
    # DELETE
    # ---------------------------
    async def delete(self, user_id: str) -> bool:
        """
        UserID로 삭제
        """
        logger.info(f"[UserService] User Delete request")
        
        user = await self.db.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()
        
        if not user:
            logger.warning(f"[UserService] User not found")
            raise ObjectNotFoundError(message="USER_NOT_FOUND_ERROR")
        
        # 트랜잭션 처리
        try:
            await self.db.delete(user)
            await self.db.commit()
            logger.info(f"[UserService] User Delete sucessfully (user_id={user_id})")
        except Exception as e:
            logger.exception(f"[UserService] DB commit failed while deleting User : {e}")
            await self.db.rollback()
            raise DatabaseCommitError(message="DB_COMMIT_ERROR")
        
        return True