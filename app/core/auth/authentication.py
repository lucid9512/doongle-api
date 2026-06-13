from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from app.core.config import settings

# Bearer 방식의 JWT 인증 트랜스포트를 정의
# - 클라이언트는 Authorization 헤더에 Bearer <token> 형태로 전달
# - tokenUrl은 JWT 로그인 엔드포인트 경로를 지정
bearer_transport = BearerTransport(tokenUrl="/api/v1/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    """
    JWT 발급 및 검증 전략 정의
    - secret: JWT 서명용 비밀키
    - lifetime_seconds: 액세스 토큰 유효기간 (분 단위를 초로 변환)
    """
    return JWTStrategy(
        secret=settings.JWT_SECRET,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# FastAPI Users용 인증 백엔드 설정
# - name: 인증 백엔드 식별자 (여기서는 'jwt')
# - transport: BearerTransport 객체
# - get_strategy: JWTStrategy 반환 함수
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
