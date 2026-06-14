# FIXES

doongle-api 수정/정합성 검토 로그. 코드 수정·오류 대응이 생길 때마다 **아래에 번호순으로 추가**한다.
각 항목은 **원인 → 수정내역 → 수정으로 얻은 것** 구조로 기록한다.
(무엇을/언제 바꿨나는 git 히스토리가, 설계 결정의 이유는 `DECISIONS.md`가, 단계 진행은 `TASKS.md`가 담당. 이 파일은 "어떤 문제를 왜 고쳤나"를 모아 본다.)

---

## #1 — 2026-06-14 — 업로드/조회 로직이 서비스 계층을 벗어나 라우터에 박혀 있던 문제
- 분류: 정합성(아키텍처 컨벤션)
- 관련 커밋: `refactor: move upload/job logic into JobService`
- 관련 파일: `app/services/job.py`, `app/apis/v1/upload.py`, `app/apis/v1/jobs.py`

### 원인
- 이 프로젝트는 "라우터는 얇게, 비즈니스 로직은 `app/services/`"를 따른다. (예: `UserService`/`RoleService`를 라우터가 호출)
- 그런데 단계 5·6에서 업로드 저장/produce, job 조회/이미지 로딩 로직을 `upload.py`·`jobs.py` 라우터 안에 직접 작성해, jobs/upload 영역만 컨벤션을 벗어났다.
- 에러도 도메인 예외가 아니라 `HTTPException`을 직접 던져, 응답 포맷이 다른 API와 달랐다.

### 수정내역
- `app/services/job.py`에 `JobService(db)` 신설:
  - `create_from_uploads(files, storage, producer)` — 검증 → 저장 → job(pending) insert → commit → produce
  - `get_by_job_id(job_id)` — 단일 조회
  - `load_image(job_id, storage)` — 원본 이미지 바이트 + media_type
- 라우터(`upload.py`/`jobs.py`)는 `JobService`를 호출하고 `SuccessJsonRes`로 감싸기만 하도록 축소.
- 라우터에서 던지던 `HTTPException`을 도메인/서비스 예외로 교체:
  - 비-이미지 → `UnprocessableEntityError`(422)
  - 없는 job / 이미지 파일 없음 → `ObjectNotFoundError`(404)
  - 저장 실패 → `FileIOError`(500), 커밋 실패 → `DatabaseCommitError`(500)

### 수정으로 얻은 것
- 코드베이스 전체가 동일한 "라우터=얇게, 로직=서비스" 구조로 통일 → 가독성/테스트성 향상.
- 에러 응답이 프로젝트 표준 `ErrorRes`(message 코드 + error_type + meta)로 통일 (기존 FastAPI 기본 `{detail}` 탈피).
- 재검증 결과: 업로드 201 / 조회 200 / 없는 job 404 / 썸네일 200 / 비-이미지 422 전부 정상.

---

## #2 — 2026-06-14 — Job 스키마(req/res) 부재 + 파일명 길이 검증 누락
- 분류: 정합성(스키마 컨벤션) + 입력 검증
- 관련 파일: `app/schemas/req/upload.py`, `app/schemas/model/job.py`, `app/services/job.py`

### 원인
- 프로젝트 컨벤션은 응답 data 를 `app/schemas/model/`의 스키마로 만들고 서비스가 `Schema.model_validate().model_dump()`로 반환하는데(예: `UserSchema`), `JobService`는 스키마 없이 **생짜 dict**를 반환해 `app/schemas/`에 job 파일이 하나도 없었다.
- 입력 검증도 FastAPI/Pydantic 방식(스키마에서 선언적 검증)을 따르지 않고 서비스에 content-type 체크만 흩어져 있었다. 특히 **filename 길이 검증이 전혀 없어**, DB `jobs.filename`(String(255)) 한도를 넘는 파일명이 오면 저장 단계에서 깨질 수 있었다.

### 수정내역
- `app/schemas/req/upload.py`에 `UploadImageMeta`(VaModelReq) 추가:
  - `filename` — 공백/빈 값(`MSG_EMPTY_FILENAME`), 255 초과(`MSG_FILENAME_TOO_LONG`) 검증
  - `content_type` — `image/` 접두사 아니면 `MSG_NOT_AN_IMAGE`
  - 검증 실패는 기존 `valid_email` 패턴대로 `UnprocessableEntityError`(422)로 던짐
- `app/schemas/model/job.py`에 `JobSchema`(조회 응답), `JobAcceptedSchema`(접수 응답) 추가 (`VaModelRes` 상속, ORM→Pydantic)
- `JobService`:
  - 업로드 시 파일별로 `UploadImageMeta`로 메타 검증(루프 전 일괄) → 부분 저장 방지
  - 조회는 `JobSchema.model_validate(job).model_dump()`, 접수는 `JobAcceptedSchema(...).model_dump()` 반환

### 수정으로 얻은 것
- 검증이 서비스 로직에서 스키마로 이동 → "정합성은 Pydantic 스키마에서" 라는 FastAPI 컨벤션 정합.
- DB 컬럼 한도(255)와 입력 검증이 한 곳에서 일치 → 잘못된 파일명이 DB 까지 도달하기 전에 422 로 차단.
- 응답이 타입 안전한 스키마 기반으로 통일(OpenAPI 문서화에도 유리).
- 재검증: 파일명 256자→422(MSG_FILENAME_TOO_LONG), 비-이미지→422(MSG_NOT_AN_IMAGE), 정상→201, 조회→200(JobSchema) 정상.
