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
