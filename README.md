# Dongle — FastAPI Starter

프로덕션을 염두에 두고 구성한 재사용 가능한 FastAPI 보일러플레이트입니다.
인증·어드민·마이그레이션·예외 처리·로깅 등 백엔드에 반복적으로 필요한 기반을 미리 갖춰 두어, 새 프로젝트를 곧바로 기능 구현부터 시작할 수 있도록 만든 베이스 템플릿입니다.

## Stack

- **FastAPI** + **Uvicorn**
- **SQLAlchemy 2.0** (async, asyncpg) + **Alembic** 마이그레이션
- **PostgreSQL**
- **fastapi-users** 기반 인증/회원 (JWT)
- **SQLAdmin** 어드민 페이지
- **Pydantic Settings** 기반 환경설정
- 공통 예외 핸들러 · 구조화 로깅 · CORS · Pagination

## Layout

```
app/
├── main.py          # 앱 진입점
├── cli.py           # Typer CLI
├── apis/            # API 라우터 (v1)
├── admin/           # SQLAdmin 어드민
├── core/            # 설정 · DB · 인증 · 미들웨어 · 로깅
├── deps/            # 의존성 주입
├── exceptions/      # 도메인/서비스 예외
├── models/          # SQLAlchemy 모델
├── schemas/         # Pydantic 스키마 (req/res/model)
└── services/        # 비즈니스 로직
```

## Requirements

- Python 3.13
- Poetry

## Setup

```bash
$ cp .env.example .env        # 환경변수 설정
$ poetry install
$ docker compose up -d        # PostgreSQL
$ poetry run alembic upgrade head
$ poetry run uvicorn app.main:app --reload
```

## API Docs

- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc