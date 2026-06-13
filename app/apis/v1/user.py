from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi_pagination import Page, Params
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.deps import get_db, require_user  # 통합된 의존성
import logging
from app.schemas.res.common import SuccessJsonRes
from app.schemas.model.user import UserSchema
from app.schemas.req.user import (
    UserPasswordReq,
    UserUpdateReq,
)
from app.services.auth.manager import get_user_manager
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger("app.apis.user")


# ============================================================
# CREATE
# 사용자 생성은 fastapi users 전용 함수 사용
# ============================================================

# ============================================================
# READ
# ============================================================
@router.get(
    "", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Read a list of Users"
)
async def get_users(
    params: Params = Depends(), # pagination 쿼리 적용
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    전체 사용자 목록 조회
    
    Returns
    - items: 사용자 목록
    - total: 총 사용자 수
    - page: 현재 페이지
    - size: 페이지 단위
    - pages: 총 페이지 수
    """
    service = UserService(db)
    users_page = await service.get(params)
    
    return SuccessJsonRes(data=users_page)

@router.get(
    "/roles", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Read a list of Roles"
)
async def get_roles(
    params: Params = Depends(), # pagination 쿼리 적용
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["user", "admin"])),
):
    """
    전체 사용자 등급 조회
    
    Returns
    - 등급 목록
    """
    service = UserService(db)
    roles_page = await service.get_role(params)
    
    return SuccessJsonRes(data=roles_page)

@router.get(
    "/search", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Search for Users through keyword"
)
async def search_users(
    keyword: str = Query(None, description="검색 키워드"),
    params: Params = Depends(), # pagination 쿼리 적용
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    사용자 키워드 검색
    키워드 범위: user_id, email, name, role
    
    Returns
    - items: 사용자 목록
    - total: 총 사용자 수
    - page: 현재 페이지
    - size: 페이지 범위
    - pages: 총 페이지 수
    """
    service = UserService(db)
    users_page = await service.get_through_keyword(params, keyword)
    
    return SuccessJsonRes(data=users_page)

@router.get(
    "/check/user-id",
    response_model= SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Check by user id"
)
async def check_user_by_user_id(
    user_id: Optional[str] = Query(None, description="사용자 아이디"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    아이디 중복 체크
    
    Returns
    - is_duplicate: bool
    """
    service = UserService(db)
    result = await service.check_by_user_id(user_id)

    return SuccessJsonRes(data={"is_duplicate": result})

@router.get(
    "/check/email",
    response_model= SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Check by user email"
)
async def check_user_by_email(
    email: Optional[str] = Query(None, description="사용자 Email"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    Email 중복 체크
    
    Returns
    - is_duplicate: bool
    """
    service = UserService(db)
    result = await service.check_by_email(email)

    return SuccessJsonRes(data={"is_duplicate": result})

@router.get(
    "/{user_id}", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Read a User by user id"
)
async def get_user_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    사용자ID로 단일 조회
    
    Returns
    - 사용자 객체
    """
    service = UserService(db)
    find_user = await service.get_by_user_id(user_id)

    return SuccessJsonRes(data=find_user)


# ============================================================
# UPDATE
# ============================================================
@router.post(
    "/{user_id}/changepw", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Change an User password by user id"
)
async def change_password(
    user_id: str,
    body: UserPasswordReq | None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["user", "admin"])),
    user_manager=Depends(get_user_manager),
):
    """
    사용자 비밀번호 변경
    
    Returns
    - is_complete: bool
    """
    result = await user_manager.change_pw(
        user_id,
        UserPasswordReq(password=body.password, is_pwreset=False)
    )
    return SuccessJsonRes(data={"is_complete": result})


@router.post(
    "/{user_id}/resetpw", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Reset an User password by user id"
)
async def reset_password(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
    user_manager=Depends(get_user_manager),
):
    """
    비밀번호 초기화 (임의 비밀번호 발급)
    
    Returns
    - is_complete: bool
    - new_password: str
    """
    # 임의 비밀번호 발급
    tmp_pw = user_manager.generate_password()
    result = await user_manager.change_pw(
        user_id,
        UserPasswordReq(password=tmp_pw, is_pwreset=True)
    )
    
    return SuccessJsonRes(
        data={
            "is_complete": result,
            "new_password": tmp_pw
        }
    )


@router.post(
    "/{user_id}/update", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Update an User by user id"
)
async def update_user_by_user_id(
    user_id: str,
    body: UserUpdateReq,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    관리자용 사용자 정보 수정
    - email
    - is_active
    - name
    - role_id
    
    Returns
    - 변경된 사용자 객체
    """
    service = UserService(db)
    result = await service.update(user_id, body)
    
    return SuccessJsonRes(data=result)


# ============================================================
# DELETE
# ============================================================
@router.post(
    "/{user_id}/delete", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Delete an User by user id"
)
async def delete_user_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["admin"])),
):
    """
    사용자 삭제
    
    Returns
    - is_complete: 삭제 성공 시 True
    """
    service = UserService(db)
    result = await service.delete(user_id)
    
    return SuccessJsonRes(data={"is_complete": result})
