# CLAUDE.md

이 파일은 doongle-api 레포에서 작업하는 에이전트(Claude Code)가 항상 따르는 상시 컨텍스트다.

## 작업 절차 (매 작업 시작 시)
1. `docs/TASKS.md`를 읽어 현재 진행할 단계를 확인한다.
2. **그 단계만** 수행한다. 다음 단계로 임의로 넘어가지 않는다.
3. 단계가 끝나면 변경 파일을 요약하고 **멈춰서 사용자 확인을 받는다.**
4. 설계상 의미 있는 결정을 내렸거나 기존 결정을 바꿨다면 `docs/DECISIONS.md`에 시간순으로 추가한다.
5. 단계 완료 시 `docs/TASKS.md`의 체크박스를 갱신하고, 코드와 함께 커밋한다.
6. 코드 수정·오류 대응(버그/정합성/리팩터 등)이 생기면 `docs/FIXES.md`에 번호순으로 **원인 → 수정내역 → 수정으로 얻은 것** 구조로 추가한다.

## 프로젝트 정체성
- doongle-api는 **이미지 업로드 게이트웨이**다. (dongle FastAPI 스타터에서 복제)
- 역할: 이미지 업로드를 받아 (1) 저장소에 저장, (2) job을 DB에 pending 기록, (3) Kafka에 produce, (4) job_id 반환. 그리고 job 조회 API 제공.
- GPU 추론은 별도 워커(doongle-ai)의 몫이다. **이 레포 범위가 아니다.**
- k8s 매니페스트는 doongle-k8s 레포에서 관리한다. 이 레포 범위가 아니다.

## 핵심 설계 결정 (상세 이유는 docs/DECISIONS.md)
- Kafka 메시지는 `{"job_id": "...", "image_path": "..."}`만. 시각·파일명 등은 DB에 둔다.
- 이미지 저장은 `StorageBackend` 인터페이스로 추상화. 현재는 `LocalStorage`만 구현, 추후 `MinioStorage`로 교체 가능하도록 설계.
- 결과 추적은 **폴링** 방식 (화면이 job 조회 API를 주기 호출). WebSocket/SSE 미사용.
- 기존 인증·어드민·마이그레이션 스택은 그대로 둔다 (의도된 풀스택 골격).

## 코드 컨벤션
- 라우터: `APIRouter(prefix="/...", tags=["..."])`. `app/apis/v1/`에 추가 후 `app/apis/v1/__init__.py`에 `include_router` 등록.
- 응답: `app/schemas/res/common.py`의 `SuccessJsonRes` 사용.
- 설정: `app/core/config.py`의 `Settings`에 필드 추가 + `.env.example`에 항목 추가.
- 의존성 주입: `app/deps/`에 정의하고 `Depends`로 주입.
- 로깅: `logging.getLogger("app.xxx")` 패턴.
- DB: SQLAlchemy 2.0 async + alembic. 모델은 `app/models/`, 기존 `base.py` 상속.

## 작업 원칙
- 한 단계씩. 한 번에 전체를 구현하지 않는다.
- 커밋은 단계별 의미 단위, **커밋 메시지는 영어 + (step N) 표기.** 예: `feat: add storage abstraction (step 3)`
- 기존 인증/어드민/예외처리 코드는 건드리지 않는다.
- 민감정보(비밀번호·토큰)는 코드에 하드코딩하지 않고 `.env`로만 관리한다.