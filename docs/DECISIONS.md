# DECISIONS

doongle-api 설계 결정 로그. 결정이 생기거나 바뀔 때마다 **아래에 시간순으로 추가**한다.
(언제 바뀌었나는 git 히스토리가, 왜 바뀌었나는 이 파일이 기록한다.)

---

## 2026-06-13 — dongle 스타터에서 복제, 풀스택 골격 유지
- 결정: 기존 FastAPI 스타터(dongle)를 doongle-api로 복제하고, 인증·어드민·마이그레이션 등 기존 스택을 걷어내지 않고 그대로 둔다.
- 이유: 포트폴리오에서 "프로덕션급 백엔드 골격을 이미 갖추고 있고 거기에 기능을 얹는다"를 보여주기 위함. 오버스펙이지만 "여력의 증명"으로 프레이밍. 슬림화하다 멀쩡한 코드를 깨뜨릴 리스크도 회피.

## 2026-06-13 — Kafka 메시지 최소화
- 결정: 메시지 페이로드는 `{job_id, image_path}`만. 파일명·업로드시각 등은 싣지 않는다.
- 이유: 메시지 큐는 가벼워야 한다. 파일명·시각은 DB(jobs)에 있으므로, 워커는 job_id로 DB를 조회해 필요한 정보를 얻으면 된다. 이미지 자체를 base64로 싣는 방식은 Kafka 메시지 크기 제한(기본 1MB) 문제가 있어 배제.

## 2026-06-13 — 이미지 전달은 경로(image_path) 방식
- 결정: 메시지에 이미지 실물이 아니라 저장 위치(image_path)를 싣는다. 워커가 그 경로로 이미지를 읽는다.
- 이유: 메시지 경량화 + 저장소 분리. image_path의 실체(파일경로/오브젝트키)는 저장소 구현에 따라 달라지지만 인터페이스는 동일하게 유지.

## 2026-06-13 — 이미지 저장소 추상화 (Local 우선, MinIO 대비)
- 결정: `StorageBackend` 인터페이스(save/load)를 정의하고 현재는 `LocalStorage`만 구현. `MinioStorage`는 인터페이스만 맞춰두고 추후 구현.
- 이유: 현재 멀티노드 환경(api는 일반 노드, 워커는 GPU 노드)에서 단순 local-path PVC는 노드 간 공유가 안 된다. 장기적으로 MinIO(S3 호환, 노드 무관 네트워크 접근)로 가는 것이 정석. 단, 지금은 로컬 개발로 검증 흐름을 막지 않기 위해 LocalStorage로 시작하고, 저장소 교체가 코드 변경 없이 가능하도록 추상화. 실제 저장소(PVC vs MinIO) 확정은 배포 단계로 미룸.
- save는 api가 사용(구현), load는 워커(doongle-ai)가 사용 예정이라 시그니처를 미리 정의해 양쪽 일관성 확보.

## 2026-06-13 — 결과 추적은 폴링
- 결정: 화면이 job_id별 조회 API를 2~3초 간격으로 폴링한다. WebSocket/SSE는 쓰지 않는다.
- 이유: 데모/포트폴리오 규모에는 폴링이 구현이 단순하고 충분. 멀티 업로드 시 각 카드가 자기 job_id를 독립적으로 폴링하면 된다. 실시간 push(SSE/WebSocket)는 워커→API 통신 등 복잡도가 커서 현 단계엔 과함.

## 2026-06-13 — 결과 저장은 PostgreSQL (jobs 테이블)
- 결정: 업로드 job과 추론 결과를 PostgreSQL `jobs` 테이블에 저장한다. (Redis 아님)
- 이유: 스타터에 이미 PostgreSQL/SQLAlchemy/alembic이 갖춰져 있어 추가 인프라가 0. 영속 보관 가능하고, 추후 user 모델과 엮어 "누가 무엇을 업로드했는가"로 확장 가능. 풀스택 골격을 유지한다는 방향과도 일치.

## 2026-06-13 — Kafka 연결 실패해도 앱은 부팅
- 결정: producer 시작 실패 시 예외를 삼키고 warning만 남긴다(앱은 정상 부팅). 이 경우 업로드 API는 503을 반환.
- 이유: 기존 clickhouse 연동의 "외부 의존성 없어도 앱은 뜬다" 철학과 일관. 분산 시스템에서 의존성 하나가 죽었다고 전체가 안 뜨는 것은 안티패턴. k8s에서는 readiness/liveness probe로 별도 관리하는 편이 디버깅에 유리.

## 2026-06-14 — jobs.result 컬럼은 Text
- 결정: 추론 결과(result)는 PostgreSQL JSON/JSONB가 아니라 Text(nullable)로 저장한다.
- 이유: 워커(doongle-ai)가 어떤 결과 스키마를 낼지 아직 확정되지 않았다. Text면 JSON 문자열·라벨·점수 등 무엇이든 수용 가능하고, 스키마가 굳으면 그때 JSONB로 마이그레이션하면 된다. 현 단계에서 컬럼 타입을 미리 박지 않는다.

## 2026-06-14 — 초기 마이그레이션은 전체 스키마 (jobs + 기존 users/roles)
- 결정: 복제 시점에 마이그레이션 파일이 0개였으므로, 첫 autogenerate(c52c04b5b7e1)에 jobs뿐 아니라 users/roles/roles_users까지 전부 포함됐다. 이를 베이스라인으로 채택한다.
- 이유: 빈 DB에서 시작하는 첫 마이그레이션이라 전체 스키마가 한 파일에 들어가는 게 자연스럽다. 기존 스타터를 복제하며 마이그레이션 히스토리는 가져오지 않았기 때문. 이후 변경분만 증분 마이그레이션으로 쌓는다.

## 2026-06-14 — greenlet 명시적 의존성 추가
- 결정: `greenlet`을 pyproject 의존성에 명시한다.
- 이유: SQLAlchemy 2.0 async(asyncpg)가 greenlet을 런타임에 요구하는데 플랫폼에 따라 자동 설치되지 않아 alembic 실행이 깨졌다. 환경 재현성을 위해 명시.

## 2026-06-14 — 업로드 처리 순서: 검증 → 저장 → job 커밋 → produce
- 결정: 업로드 API 는 (1) 모든 파일을 먼저 이미지인지 검증, (2) 저장 + job(pending) 적재, (3) **DB commit 먼저**, (4) 그 다음 Kafka produce 순서로 처리한다.
- 이유:
  - 검증을 선행해 일부 파일만 저장되는 부분 실패를 줄인다.
  - produce 보다 commit 을 먼저 해 워커가 메시지를 받아 DB 를 조회할 때 job row 가 이미 존재하도록 보장(반대 순서면 "메시지는 왔는데 job 없음" race 발생).
  - 트레이드오프: commit 후 produce 가 실패하면 해당 job 은 pending 으로 남는다(메시지 미발행). 데모 규모에선 수용하고, 추후 outbox 패턴 등으로 보강 여지.

## 2026-06-14 — 데모 화면은 `/upload-ui` 로 분리 (기존 `/` 유지)
- 결정: 업로드 데모 페이지를 `GET /upload-ui` 에 두고, 기존 `GET /`(JSON "Hello, Dongle!")는 건드리지 않는다. 템플릿 디렉토리는 CWD 의존을 피해 `Path(__file__).parent / "templates"` 절대경로로 지정.
- 이유: 루트(`/`)는 헬스/식별용 JSON 으로 이미 쓰이고 있어 깨지 않는 편이 안전. UI 는 별도 경로로 분리. 화면 JS 는 별도 빌드 없이 인라인 바닐라로 구성(데모 규모엔 충분, 의존성 0).

## 2026-06-14 — 비즈니스 로직은 서비스 계층(JobService)으로 (라우터는 얇게)
- 결정: 단계 5·6 에서 라우터에 직접 넣었던 업로드/조회 로직을 `app/services/job.py` 의 `JobService(db)` 로 옮긴다. 라우터는 `JobService` 를 호출하고 `SuccessJsonRes` 로 감싸기만 한다.
- 이유: 기존 스타터가 `UserService`/`RoleService` 처럼 "라우터=얇게, 로직=서비스" 컨벤션을 따르는데, jobs/upload 만 라우터에 로직을 박아 일관성이 깨졌다. 서비스로 통일.
- 부수 효과(개선): 에러를 `HTTPException` 대신 도메인/서비스 예외(`ObjectNotFoundError`·`UnprocessableEntityError`·`FileIOError`·`DatabaseCommitError`)로 던지게 되어, 응답이 FastAPI 기본 `{detail}` 대신 프로젝트 표준 `ErrorRes`(message 코드 + error_type + meta)로 통일됐다. 비-이미지는 422, 없는 job 은 404.

## 2026-06-14 — 이미지 미리보기는 클라이언트 로컬 렌더, 서버 image 엔드포인트 제거
- 결정: `GET /api/v1/jobs/{job_id}/image`(및 `JobService.load_image`)를 제거한다. 화면 썸네일은 업로드 시 브라우저가 가진 File 을 `URL.createObjectURL(file)` 로 그대로 렌더한다.
- 이유:
  - 이 화면은 1회성이고 로그인/세션이 없다. 새로고침하면 카드가 사라지는 휘발성 UI라, "다시 조회"할 영속 화면이 아니다.
  - 업로드 순간 브라우저가 이미 원본 File 을 들고 있으므로, 서버가 방금 받은 이미지를 되돌려주는 건 불필요한 왕복(앱 부하·메모리)일 뿐이다.
  - 업로드 응답 jobs 배열은 보낸 파일 순서와 동일 → 프론트가 인덱스로 로컬 File 과 job 을 짝지어 미리보기 가능.
- 유지: `StorageBackend.load()` 시그니처와 `LocalStorage.load()` 구현은 남긴다. 이건 api 가 아니라 워커(doongle-ai)가 `image_path` 로 원본을 읽는 계약이라 그대로 둔다(이 레포 내에선 미사용).
- 트레이드오프: 폴링으로 받은 다른 사용자/세션의 job 을 화면에서 이미지로 볼 수단은 없어진다. 하지만 현재 UI 는 "내가 방금 올린 것"만 보여주는 1회성이라 무관.

## 2026-06-14 — MinIO 백엔드 추가 (StorageBackend 구현)
- 결정: `StorageBackend` 에 `MinioStorage` 구현을 추가한다. `StorageBackend` 인터페이스(save/load 시그니처)와 `LocalStorage` 는 건드리지 않는다. `deps/storage.py` 에 `STORAGE_BACKEND=minio` 분기를 추가하고, 인터페이스로만 의존하는 `services/job.py`·`apis/v1/upload.py` 는 변경하지 않는다.
- 결정: `save()` 는 **오브젝트 키만** 반환한다(예: `abc123.jpg`). 버킷명은 키/메시지/`image_path` 에 넣지 않고 env(`MINIO_BUCKET`)로만 관리한다.
  - 이유: 단일 버킷이고, 미래의 소유자별 조회는 DB `user_id` + presigned URL 로 해결되므로 `image_path` 에 버킷을 넣을 이득이 없다. 키를 짧게 유지하고 버킷 교체(운영) 시 데이터 변경이 없다.
- 결정: 클라이언트는 minio 공식 SDK 를 쓴다(boto3 아님).
  - 이유: 자체 호스팅 MinIO 가 목적이고 boto3 보다 가볍다(불필요한 AWS 전반 의존성 회피).
- 결정: 클라이언트는 `__init__` 에서 1회 생성해 재사용하고, 버킷은 존재한다고 가정한다(앱이 생성하지 않음 — 콘솔에서 미리 생성).
  - 이유: 부팅 시 버킷 자동 생성은 권한·운영 경계를 흐린다. 버킷은 인프라가 소유.
- 트레이드오프: minio SDK 는 동기 라이브러리라 `async save()` 안에서 블로킹 호출(put_object/get_object)이 일어난다. 작은 이미지 + 데모 규모라 현재는 허용. 부하가 커지면 `anyio.to_thread`/`run_in_executor` 로 오프로딩할 여지.

## 2026-06-14 — api Dockerfile / .dockerignore (워커와 원칙 일치)
- 결정: api 컨테이너 이미지를 추가한다. 워커(doongle-ai) Dockerfile 과 동일한 원칙을 따르되 api 에 맞춘다.
- 결정: 베이스는 `python:3.13-slim`.
  - 이유: 워커는 추론을 위해 pytorch 베이스가 필요하지만 api 는 GPU 추론을 하지 않는 업로드 게이트웨이다. 무거운 ML 베이스를 쓸 이유가 없어 경량 슬림 파이썬으로 이미지 크기·빌드시간·공격 표면을 줄인다.
- 결정: `FROM --platform=linux/amd64` 로 아키텍처를 고정한다.
  - 이유: 빌드는 Mac(arm64)에서 하지만 실제 구동은 amd64 노드(윈2)다. 플랫폼을 고정하지 않으면 arm64 이미지가 빌드돼 amd64 노드에서 안 뜬다. 워커와 동일한 이유.
- 결정: 설정값(KAFKA/MINIO/DB 등)은 Dockerfile 에 `ENV` 로 박지 않고 전부 런타임 환경변수(k8s ConfigMap/Secret)로 주입한다. `.env` 는 `.dockerignore` 로 이미지에서 제외.
  - 이유: 12factor. 환경별(로컬/스테이징/운영) 설정 분리 + 비밀정보를 이미지에 굽지 않는다. 같은 이미지를 환경만 바꿔 재사용.
- 결정: 의존성은 poetry 가 아니라 `requirements.txt` + pip 흐름으로 설치한다. 빌드 전 로컬에서 `poetry export` 로 `requirements.txt` 를 뽑아 COPY 한다. `requirements.txt` 를 먼저 COPY/설치해 레이어 캐시를 활용(소스만 바뀌면 의존성 레이어 재사용).
  - 이유: 런타임 이미지에 poetry 자체를 넣지 않아 가볍고, lock 된 버전을 그대로 재현. (트레이드오프: 의존성 변경 시 `poetry export` 재실행이 수동 단계로 남는다.)
- 결정: 시작 시 `alembic upgrade head` 후 uvicorn 을 띄운다(셸 형태 CMD). 마이그레이션을 컨테이너 시작 시 자동 적용.
  - 이유: 현재 api 는 1 레플리카라 시작 시 마이그레이션이 단순하고 충분하다.
  - 트레이드오프: 다중 레플리카로 가면 여러 파드가 동시에 마이그레이션을 시도할 수 있다(경쟁). 그 단계에선 마이그레이션을 별도 k8s Job(또는 initContainer)으로 분리하고 앱 컨테이너는 uvicorn 만 실행하도록 바꾼다. 지금은 과한 복잡도라 미룸.

## 2026-06-14 — aiokafka 0.14 업그레이드 + amd64 이미지 빌드/푸시 성공
- 결정: `aiokafka` 를 0.11 → 0.14.0 으로 올린다. 부수적으로 `requires-python` 을 `>=3.9` → `>=3.10` 으로 올렸다(aiokafka 0.14 가 3.9 를 드롭).
  - 이유: `python:3.13-slim` 기반 이미지 빌드 시 aiokafka 0.11 은 cp313 휠이 없어 소스 컴파일이 필요했고, 빌드 도구를 builder 스테이지에 둬도 컴파일이 불안정했다. 0.14.0 은 cp313 manylinux 휠을 제공하므로 컴파일 없이 설치된다. → 빌드가 단순/안정해지고 런타임 이미지도 가볍게 유지.
- 결과: Mac(arm64)에서 `docker buildx build --platform linux/amd64 ... --load` 로 amd64 이미지 빌드 성공. 빌드 로그상 `aiokafka-0.14.0` 이 cp313 휠로 설치됨(컴파일 0). `ghcr.io/lucid9512/doongle-api:latest` 로 GHCR 푸시 완료(digest sha256:686855de...).
  - 트레이드오프: `requirements.txt` 는 의존성 변경 시 `poetry export` 재실행이 필요한 수동 단계로 남는다(이미 DECISIONS 기록됨).