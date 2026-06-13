# TO-DO

초기화 직후 점검에서 발견했던 손볼 항목들. 대부분 패치 완료, 남은 항목만 아래 정리.

## ✅ 처리 완료

### P1 — 동작 영향
- **`UnAuthorizeError` 중복 정의** → `UnauthenticatedError(401)` / `ForbiddenError(403)` 분리, 호출처(`app/services/auth/service.py`, `app/deps/user.py`) 업데이트. `UnAuthorizeError` 는 `ForbiddenError` alias 로 유지.
- **`register_all_exception_handlers` 호출 누락** → `app/main.py` 에서 `register_all_exception_handlers(app)` 로 정상 호출.
- **passlib hashing.py 사용처 없음** → `app/core/auth/hashing.py` 삭제. 비밀번호 해싱은 `pwdlib (Argon2 + Bcrypt)` 한 종류로 통일.

### P2 — 보안/운영 정합성
- **`.env` 토큰 만료 시간** → `ACCESS_TOKEN_EXPIRE_MINUTES=60` 으로 정상화.
- **`.env` 평문 시크릿** → 실제 `.env` 는 그대로 두되 `.env.example` 추가, `.gitignore` 가 이미 `.env` 제외 처리되어 있음.
- **ClickHouse 접속 정보 하드코딩** → `Settings` 에 `CH_HOST/CH_PORT/CH_USER/CH_PASSWORD/CH_DB` 추가, `app/core/clickhouse.py` 에서 settings 사용.
- **CORS 화이트리스트 하드코딩** → `Settings.CORS_ORIGINS` 로 분리 (콤마 구분 또는 JSON 배열 지원).

### P3 — 정리/일관성
- **주석으로만 남은 코드** → `app/services/auth/admin_service.py` 삭제, `app/admin/__init__.py` 깔끔하게 재작성(`init_admin(app)` 활성화 가능 형태), `app/models/user.py` 의 association_proxy 주석 제거.
- **Alembic `include_object` 의료 잔재** → `migrations/env.py` 에서 `studies_*` 파티션 제외 훅 제거.
- **`AdminLoginSchema` 사용처 없음** → 삭제. `RefreshRequest` 만 유지.
- **`LOG_DIR=../log`** → `./logs` 로 변경. 프로젝트 내부에 로그 디렉토리 생성.
- **CLI 비밀번호 위치 인자** → `typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)` 로 변경. shell history / `ps` 노출 방지.
- **`BaseMixin` `__tablename__` `+s` 단순 처리** → fallback 임을 docstring 으로 명시. 모델은 가급적 `__tablename__` 명시 권장.
- **`BaseMixin` / `CompositePKBaseModel` 분기 의도** → 두 클래스 모두 docstring 추가.

## 📌 남은 환경 정비 (한 번만 하면 되는 작업)

- [ ] `git init` + 첫 커밋
- [ ] `poetry run alembic revision --autogenerate -m "init"` → User/Role/UserRole 테이블 첫 마이그레이션 생성
- [ ] `docker compose up -d` 로 Postgres 기동 후 `poetry run alembic upgrade head`
- [ ] `poetry run python -m app.cli create-roles admin user`
- [ ] `poetry run python -m app.cli create-user <id> <name> <email> admin` (비밀번호는 prompt)
- [ ] 운영 배포 시 `.env` 의 시크릿 값들을 환경변수/secrets manager 로 교체
- [ ] 운영 환경에서는 `Settings` 에 추가했던 ClickHouse 옵션을 실제 값으로 채우거나, 사용 안 하면 `app/deps/clickhouse.py` / `app/core/clickhouse.py` 제거 검토
