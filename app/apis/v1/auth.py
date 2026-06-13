from fastapi import APIRouter, Depends, Body, Response, status, Request, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth.service import AuthService
from app.deps import get_db, require_user
from app.schemas.req.user import UserCreateReq, UserUpdateReq, UserPasswordReq
from app.schemas.model.user import UserSchema
from app.schemas.res.common import SuccessJsonRes
from app.services.auth.manager import get_user_manager
from app.core.auth.authentication import auth_backend

router = APIRouter(prefix="/auth", tags=["auth"])

# ============================================================
# 회원가입
# ============================================================
# router.include_router(
#     fastapi_users.get_auth_router(auth_backend),
#     prefix="/jwt",
#     tags=["auth (Unused)"],
# )

# router.include_router(
#     # SuccessJsonRes 을 통한 response 불가
#     fastapi_users.get_register_router(UserSchema, UserCreateWithRoleID), 
#     prefix="/jwt",
#     tags=["auth"],
#     dependencies=[Depends(current_superuser)]  # 관리자만 회원가입 가능
# )

@router.post(
    "/register",
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="User register"
)
async def register(
    request: Request,
    user_create: UserCreateReq,
    user_manager=Depends(get_user_manager),
):
    """
    회원가입
    
    Returns
    - 새로운 사용자 객체
    """
    new_user = await user_manager.create(user_create, False, request)
    
    return SuccessJsonRes(data=new_user)

# ============================================================
# 로그인 (Access + Refresh Token 발급)
# ============================================================
@router.post(
    "/login",
    # Token 자동 등록이 되려면 response_model 사용 X
    summary="로그인 (Access + Refresh 토큰 발급)"
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager),
):
    """
    사용자 인증 후 Access Token + Refresh Token 발급
    
    Required Request
    - username
    - password
    
    Returns
    - access_token
    - token_type
    - Refresh Token은 HttpOnly 쿠키에 저장
    """

    return await AuthService.login(response, user_manager, form_data)

# ============================================================
# 로그아웃 (쿠키 삭제)
# ============================================================
@router.post(
    "/logout",
    summary="로그아웃 (Refresh 쿠키 삭제)"
)
async def logout(response: Response):
    """
    로그아웃
    - Refresh Token 쿠키 삭제
    
    - 프론트엔드는 Access Token 제거 필요
    """

    return await AuthService.logout(response)

# ============================================================
# 사용자 정보 관련 (JWT 로그인된 유저 기준)
# ============================================================
@router.get(
    "/me", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Read my account",
)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user(["user", "admin"])),
):
    """
    자신의 계정 정보 조회
    
    Returns
    - 사용자 객체
    """
    me = UserSchema.model_validate(user).model_dump()
    return SuccessJsonRes(data=me)

@router.post(
    "/me/verify", 
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Verify my account's password",
)
async def verify_current_user(
    body: UserPasswordReq | None,
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager),
    user=Depends(require_user(["user", "admin"])),
):
    """
    자신의 패스워드 일치 여부 확인
    
    Returns
    - is_verify : bool
    """
    result = await user_manager.verify_pw(user, UserPasswordReq(password=body.password), safe=True)
    return SuccessJsonRes(data={"is_verify": result})

@router.post(
    "/me/update",
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Update my account"
)
async def update_current_user(
    body: UserUpdateReq | None,
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager),
    user=Depends(require_user(["user", "admin"]))
):
    """
    자신의 계정 정보 수정
    
    fastapi users 상속으로 swagger 에 불필요한 body 요소가 존재함
    수정 가능한 요소
    - email
    - name
    
    Returns
    - is_complete: bool
    """
    await user_manager.update(body, user, safe=True)
    
    return SuccessJsonRes(data={"is_complete": True})

@router.post(
    "/me/delete",
    response_model=SuccessJsonRes,
    status_code=status.HTTP_200_OK,
    summary="Delete my account",
)
async def delete_current_user(
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager),
    user=Depends(require_user(["user", "admin"])),
):
    """
    자신의 계정 정보 삭제
    
    Returns
    - is_complete: bool
    """
    await user_manager.delete(user)
    
    return SuccessJsonRes(data={"is_complete": True})

# ============================================================
# Refresh Token → Access Token 재발급
# ============================================================
@router.post(
    "/jwt/refresh",
    summary="Token refresh(verify&issue)"
)
async def refresh_access_token(
    refresh_token: str = Cookie(None), 
    user_manager=Depends(get_user_manager),
):
    """
    Refresh Token 검증 후 Access Token 재발급
    
    Required Request
    - refresh_token
    
    Returns
    - access_token
    - token_type
    """

    return await AuthService.refresh(refresh_token, user_manager)
