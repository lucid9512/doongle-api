# Project Structure

FastAPI 기반 인증/사용자 관리 보일러플레이트.
의료 도메인을 모두 제거하고, 로그인·사용자·권한(Role)·관리자 기능만 남긴 초기 상태입니다.

## 기술 스택

- **Web**: FastAPI + Uvicorn
- **DB**: PostgreSQL (asyncpg, SQLAlchemy 2.x async)
- **Migration**: Alembic
- **Auth**: fastapi-users (JWT Bearer + Refresh Cookie)
- **Admin UI**: sqladmin
- **Pagination**: fastapi-pagination
- **CLI**: typer

## 디렉토리 구조

```
dongle-be/
├── .env                       # 환경 변수 (DATABASE_URL, JWT_SECRET 등)
├── .gitignore
├── alembic.ini                # Alembic 설정
├── docker-compose.yaml        # Postgres 17.6 컨테이너 정의
├── pyproject.toml             # Poetry 프로젝트/의존성 정의
├── poetry.lock
├── README.md
├── PROJECT_STRUCTURE.md       # ← 본 파일
│
├── migrations/                # Alembic 마이그레이션
│   ├── env.py
│   ├── script.py.mako
│   └── versions/              # (현재 비어있음 — 초기화 후 새로 생성)
│
└── app/
    ├── __init__.py
    ├── main.py                # FastAPI 앱 엔트리 (CORS, 미들웨어, 라우터 등록)
    ├── cli.py                 # typer CLI (create-roles, create-user)
    │
    ├── core/                  # 인프라 / 횡단 관심사
    │   ├── config.py          # pydantic-settings 기반 환경변수 로더
    │   ├── db.py              # SQLAlchemy async engine / session_maker
    │   ├── clickhouse.py      # ClickHouse 클라이언트 (lazy import — 미설치 시에도 부팅 OK)
    │   ├── hooks.py           # FastAPI lifespan / 예외 핸들러 등록
    │   ├── middleware.py      # request-id, 전역 예외, 요청/응답 로깅, 보안 헤더
    │   ├── exception_handler.py  # HTTPException / RequestValidationError 핸들러
    │   ├── logging_config.py  # dictConfig 기반 로거 설정
    │   ├── request_context.py # ContextVar 기반 request_id 전파
    │   └── auth/
    │       ├── authentication.py  # fastapi-users JWT BearerTransport / AuthenticationBackend
    │       ├── tokens.py          # PyJWT access/refresh 토큰 생성·검증 유틸
    │       └── hashing.py         # passlib bcrypt 해셔
    │
    ├── models/                # SQLAlchemy ORM 모델
    │   ├── __init__.py        # Base = declarative_base() + 자동 import
    │   ├── base.py            # BaseModel, CompositePKBaseModel, TimestampMixin
    │   └── user.py            # User, Role, UserRole(M:N)
    │
    ├── schemas/               # Pydantic 스키마
    │   ├── __base__.py        # camelCase ↔ snake_case 변환 유틸 + Va 베이스
    │   ├── req/               # 요청 스키마
    │   │   ├── auth.py        # RefreshRequest, AdminLoginSchema
    │   │   └── user.py        # UserCreateReq, UserUpdateReq, UserPasswordReq, RoleCreateReq, UserRoleCreateReq
    │   ├── model/             # 도메인/DTO 스키마
    │   │   └── user.py        # UserSchema, RoleSchema
    │   └── res/               # 응답 스키마
    │       └── common.py      # SuccessJsonRes, ErrorRes, MetaData
    │
    ├── exceptions/            # 비즈니스 예외 + 핸들러
    │   ├── domain.py          # DomainError, UnAuthorizeError, ObjectNotFoundError, DuplicateError, UnprocessableEntityError
    │   ├── service.py         # ServiceError, DatabaseCommitError, FileIOError
    │   └── handler.py         # 예외 → 표준 ErrorRes JSONResponse
    │
    ├── deps/                  # FastAPI Depends 의존성 주입
    │   ├── db.py              # get_db (AsyncSession)
    │   ├── auth.py            # fastapi-users 인스턴스, current_user / current_active_user / current_superuser
    │   ├── user.py            # require_user(roles=[...]) — Role 기반 가드
    │   └── clickhouse.py      # get_ch_db (요청 시점에만 ClickHouse 클라이언트 생성)
    │
    ├── services/              # 비즈니스 로직
    │   ├── user.py            # UserService, RoleService (조회/수정/삭제)
    │   └── auth/
    │       ├── manager.py     # UserDB, UserManager (fastapi-users) — 계정 생성/비밀번호 변경
    │       ├── service.py     # AuthService — 로그인/로그아웃/토큰 재발급
    │       └── admin_service.py  # (전체 주석 처리 — sqladmin 세션 인증 백엔드 보류 중)
    │
    ├── apis/                  # REST 라우터
    │   └── v1/
    │       ├── __init__.py    # /api/v1 하위 라우터 통합
    │       ├── auth.py        # /api/v1/auth — register, login, logout, /me, jwt/refresh
    │       └── user.py        # /api/v1/users — 목록/검색/중복체크, 비밀번호 변경/리셋, 수정/삭제
    │
    └── admin/                 # sqladmin 설정 (현재 init_admin은 주석 처리)
        ├── __init__.py
        └── views.py           # UserAdmin, RoleAdmin
```

## 요청 흐름

```
Client
  │
  ▼
[CORS] → [SessionMiddleware] → [request_context_middleware]
                                   │ X-Request-ID 헤더 / ContextVar 주입
                                   ▼
                               [exception_middleware]
                                   │ DomainError / ServiceError → ErrorRes 변환
                                   ▼
                               [request_logging_middleware]
                                   │ DEBUG 모드에서 요청/응답 로깅
                                   ▼
                               Router (/api/v1/...)
                                   │ Depends(get_db), Depends(require_user([...]))
                                   ▼
                               Service (UserService / AuthService / UserManager)
                                   │
                                   ▼
                               SQLAlchemy AsyncSession
```

## 인증·권한 모델

- 로그인 ID는 `User.user_id` (이메일 아님). `UserDB.get_by_email`을 오버라이딩해서 `user_id` 기반 인증.
- JWT Access Token은 응답 본문, Refresh Token은 HttpOnly 쿠키.
- Role은 `users` ↔ `roles_users` ↔ `roles` 의 M:N 관계. 현재는 1user-1role 관용 사용.
- `is_superuser`는 Role 이름이 `"admin"` 일 때 자동 True.
- 라우터에서 `Depends(require_user(["user", "admin"]))` 형태로 권한 게이팅.

## 응답 포맷

성공:

```json
{
  "result": true,
  "message": "MSG_SUCCESS",
  "data": { ... },        // 키는 camelCase로 자동 변환
  "meta": {
    "requestId": "abc12345",
    "timestamp": "...",
    "elapsedMs": null,
    "version": "v1.0.0"
  }
}
```

실패 (`ErrorRes`):

```json
{
  "result": false,
  "message": "MSG_OBJECT_NOT_FOUND",
  "errorType": "ObjectNotFoundError",
  "meta": { ... }
}
```

## 로컬 개발

```bash
# 1) 의존성 설치
poetry install

# 2) Postgres 컨테이너 (선택)
docker compose up -d

# 3) (DB가 살아있는 경우) 첫 마이그레이션 생성
poetry run alembic revision --autogenerate -m "init"
poetry run alembic upgrade head

# 4) 개발 서버
poetry run uvicorn app.main:app --reload

# 5) 초기 데이터
poetry run python -m app.cli create-roles admin user
poetry run python -m app.cli create-user admin Admin Pass1234! admin@example.com admin
```

- Swagger: <http://127.0.0.1:8000/docs>
- OpenAPI: <http://127.0.0.1:8000/openapi.json>

## 주의 사항

- **ClickHouse 미설치 OK**: `app/core/clickhouse.py` 가 lazy import 처리되어, `clickhouse-connect` 패키지가 없어도 FastAPI 앱은 정상 부팅됩니다. ClickHouse를 실제로 호출할 때만 RuntimeError가 발생합니다.
- **migrations/versions 비어있음**: 초기화 과정에서 기존 의료 도메인 마이그레이션을 모두 삭제했습니다. 새 스키마 작업 전에 `alembic revision --autogenerate` 로 첫 리비전을 만들어야 합니다.
- **`.git` 미존재`**: 초기화 시 함께 제거되었습니다. 필요 시 `git init` 으로 새로 시작하세요.

## 프레임워크 강점·특이점

다른 FastAPI 보일러플레이트와 비교했을 때 잘 갖춰져 있는 부분들.

### 1. 모델 자동 등록
`app/models/__init__.py` 가 `Base = declarative_base()` 를 정의하고 디렉토리 내 모든 `.py` 파일을 `importlib` 로 자동 import 합니다. 새 모델 파일만 추가하면 어디서도 import 하지 않아도 Alembic autogenerate가 곧바로 인식합니다.

### 2. 로그인 식별자를 자유롭게 교체 가능
`UserDB.get_by_email` 을 오버라이딩해서 fastapi-users 의 email 기본을 `User.user_id` 로 치환했습니다. 같은 패턴으로 phone / employee_no / 사번 등 어떤 식별자로든 손쉽게 변경할 수 있습니다.

### 3. 요청·응답 케이스 자동 변환
- **요청**: `VaModelReq` 가 `alias_generator=to_camel`, `populate_by_name=True` 를 적용 — FE가 camelCase로 보내도 자동으로 snake_case 필드에 매핑.
- **응답**: `SuccessJsonRes.data` 가 `field_serializer` 로 재귀 camelCase 변환 — 서비스 코드에서는 snake_case만 다루면 FE에 일관된 camelCase로 나갑니다.

서버 코드는 Python 컨벤션, 프론트는 JS 컨벤션 그대로 가져갈 수 있어서 양쪽 다 깨끗합니다.

### 4. Role 시스템과 fastapi-users `is_superuser` 자동 동기화
`roles` ↔ `roles_users` ↔ `users` M:N 구조에 더해, Role 이름이 "admin" 이면 fastapi-users의 `is_superuser=True` 가 UserManager / UserService 레벨에서 자동으로 맞춰집니다. 라우터에서는 `Depends(require_user(["admin"]))` 처럼 Role 이름으로 깔끔하게 가드.

### 5. request_id 자동 전파
- 미들웨어에서 `X-Request-ID` 헤더 재사용 또는 8자리 hex 신규 생성 → `ContextVar` + `request.state` 동시 저장.
- `MetaData`, `DomainError`, `ServiceError` 가 ContextVar에서 request_id 를 알아서 가져옵니다. 서비스 코드에서 따로 넘겨주지 않아도 로그·에러·응답이 같은 ID로 묶입니다.
- 응답 미들웨어가 JSON 응답 본문의 `meta.request_id` 가 비어있으면 자동 주입.

### 6. 이중 예외 체계 + 표준 응답
- `DomainError` (4xx, 비즈니스) / `ServiceError` (5xx, 시스템) 두 갈래로 명확히 분리.
- 양쪽 모두 `to_response()` → 표준 `ErrorRes` 로 변환되며, 미들웨어와 FastAPI exception handler 양쪽에 등록되어 어느 경로로 빠져나가도 응답 포맷이 동일.
- 새 예외는 `status_code`, `message` 만 오버라이드하면 끝.

### 7. Access(JSON) + Refresh(HttpOnly Cookie) 분리
`/auth/login` 응답 본문에는 `access_token` 만, `refresh_token` 은 `httponly + samesite=lax` 쿠키로 자동 세팅 → XSS로부터 refresh를 보호하면서 SPA에 access만 노출. JWT 페이로드에 `aud: "fastapi-users:auth"` 가 항상 포함되어 라이브러리와의 호환도 검증됨.

### 8. ClickHouse는 옵셔널 의존성
`app/core/clickhouse.py` 가 함수 내부 lazy import 로 처리되어, `clickhouse-connect` 패키지가 없어도 FastAPI 부팅·테스트가 정상입니다. 분석 워크로드를 켜고 끄는 게 환경별로 자유롭습니다.

### 9. 깔끔한 의존성 주입 레이어
`app/deps/` 가 DB 세션, fastapi-users 인스턴스, Role 가드, ClickHouse 클라이언트를 한 곳에 모아서 export — 라우터에서는 `from app.deps import get_db, require_user` 한 줄로 끝납니다.

### 10. 응답 메타데이터 자동 보강
모든 성공 응답이 `result / message / data / meta` 네 필드로 통일되어 있고, `meta` 에는 `requestId`, `timestamp`, `version` 이 자동으로 채워집니다. FE에서 i18n 키(`MSG_SUCCESS`, `MSG_OBJECT_NOT_FOUND` …) 만 보고도 메시지 처리 가능.

### 11. CLI 통합 (`typer`)
`poetry run python -m app.cli create-roles ...` / `create-user ...` 만으로 초기 Role / Admin 계정 시드를 만들 수 있습니다. 별도 스크립트 디렉토리 없이 앱 코드와 같은 컨텍스트(SQLAlchemy 세션, 모델)를 그대로 재사용.
