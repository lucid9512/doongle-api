# TASKS

doongle-api 구현 단계. 에이전트는 현재 단계만 수행하고 멈춰서 확인받는다.
완료 시 체크박스를 갱신하고 코드와 함께 커밋한다.

## 완료
> 완료 항목은 "무엇을 했는지" 세부 내역을 함께 남긴다.

- [x] 단계 1 — Kafka 설정
  - `pyproject.toml`에 `aiokafka` 추가
  - `config.py`에 `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_UPLOAD_TOPIC="image-upload"` 추가
  - `.env.example` 신규 생성(기존 필수 설정 전부 + Kafka 항목)

- [x] 단계 2 — Kafka Producer 모듈
  - `app/core/kafka.py`: `AIOKafkaProducer` 단일 인스턴스 관리 — `start_producer()`/`stop_producer()`/`get_producer_instance()`
  - 브로커 미가용 시에도 앱은 부팅(예외 삼키고 warning) — clickhouse와 동일 철학
  - `app/core/hooks.py` lifespan에 start/stop 연결(기존 로깅 유지)
  - `app/deps/kafka.py`: `get_producer()` 의존성(producer 없으면 503)

- [x] 단계 3 — 스토리지 추상화
  - `app/core/storage.py`: `StorageBackend`(ABC) — `save(file)->str`(async), `load(path)->bytes`
  - `LocalStorage(StorageBackend)`: uuid 파일명으로 저장, 경로 반환 / load는 파일 바이트 반환
  - `config.py`에 `STORAGE_BACKEND="local"`, `LOCAL_STORAGE_PATH="./uploads"` + `.env.example`
  - `app/deps/storage.py`: `get_storage()` 의존성(백엔드 분기, lru_cache)

- [x] 단계 4 — Job 모델 + 마이그레이션
  - `app/models/job.py`: `Job`(job_id uuid·filename·image_path·status="pending"·result Text nullable + id/timestamps). __init__ glob auto-import로 자동 등록
  - 초기 마이그레이션 `c52c04b5b7e1` 생성 → `upgrade head` 적용 (베이스라인이 없어 users/roles까지 포함)
  - `greenlet` 의존성 추가(SQLAlchemy async 필수), `poetry.lock` 커밋
  - `.gitignore` 신규(.env·__pycache__·uploads/ 등), 기존 `.DS_Store` 추적 해제

- [x] 단계 5 — 업로드 API
  - `app/apis/v1/upload.py`: `POST /api/v1/upload` (멀티 업로드 `list[UploadFile]`)
  - 처리 순서: 전체 이미지 검증 → storage.save → job(pending) insert → **DB commit** → Kafka `{job_id, image_path}` produce
  - `SuccessJsonRes`로 job 목록(job_id, filename, status) 반환
  - `app/apis/v1/__init__.py`에 라우터 등록, `python-multipart` 의존성 명시

- [x] 단계 6 — Job 조회 API
  - `app/apis/v1/jobs.py`: `GET /api/v1/jobs/{job_id}` → job_id·filename·status·result 반환, 없으면 404
  - `GET /api/v1/jobs/{job_id}/image`: storage.load로 원본 이미지 StreamingResponse(미디어타입 추론), 파일 없으면 404
  - `app/apis/v1/__init__.py`에 jobs 라우터 등록
  - 검증: 존재 job→200, 없는 job→404 (ASGI 클라이언트로 확인)

- [x] 단계 7 — Jinja 업로드 + 폴링 화면
  - `app/templates/upload.html`: 다중 파일 선택 + 업로드, 카드 그리드(썸네일+파일명+상태뱃지), 인라인 CSS/JS
  - 바닐라 JS: `POST /api/v1/upload`(FormData, 필드명 `files`) → 응답 jobs로 카드 생성, 카드별 `GET /api/v1/jobs/{id}` 2.5초 폴링
  - status "done"→결과 표시+폴링 중단, "error/failed"→에러뱃지+중단, "pending"→스피너 유지하고 재폴링
  - 썸네일은 `GET /api/v1/jobs/{id}/image` 사용
  - `main.py`에 `Jinja2Templates`(파일 기준 절대경로) + `GET /upload-ui` 연결(기존 `GET /` JSON은 유지)
  - 검증: `/upload-ui` → 200 HTML 렌더 확인

## 진행 예정

- [ ] 단계 8 — 로컬 검증
  - .env 로컬 맞춤 → docker compose up -d → alembic upgrade head → uvicorn --reload
  - 업로드 → 카드 pending 표시 확인
  - ./uploads 파일 저장 / DB jobs pending row / Kafka UI(kafka-ui.doongle.local) 토픽 메시지 확인
  - (워커 없으므로 pending에서 멈춤이 정상)