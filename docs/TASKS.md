# TASKS

doongle-api 구현 단계. 에이전트는 현재 단계만 수행하고 멈춰서 확인받는다.
완료 시 체크박스를 갱신하고 코드와 함께 커밋한다.

## 완료
- [x] 단계 1 — Kafka 설정 (config + pyproject `aiokafka` + .env.example)
- [x] 단계 2 — Kafka Producer 모듈 (core/kafka.py, hooks lifespan 연결, deps/kafka.py)
- [x] 단계 3 — 스토리지 추상화 (core/storage.py, config + .env.example, deps/storage.py)
- [x] 단계 4 — Job 모델 + 마이그레이션 (models/job.py, 초기 마이그레이션 c52c04b5b7e1, upgrade head 적용)

## 진행 예정

- [ ] 단계 5 — 업로드 API
  - `app/apis/v1/upload.py`: `POST /api/v1/upload` (멀티 업로드 list[UploadFile])
  - content-type 이미지 검증 → storage.save → image_path
  - job_id(uuid) 생성, DB Job(pending) insert
  - producer로 `{job_id, image_path}` produce
  - SuccessJsonRes로 job 목록(job_id, filename, status) 반환
  - `python-multipart` 없으면 추가, 라우터 등록

- [ ] 단계 6 — Job 조회 API
  - `app/apis/v1/jobs.py`: `GET /api/v1/jobs/{job_id}` → status/result 반환, 없으면 404
  - (선택) `GET /api/v1/jobs/{job_id}/image` → storage.load로 썸네일 StreamingResponse
  - 라우터 등록

- [ ] 단계 7 — Jinja 업로드 + 폴링 화면
  - `app/templates/upload.html`: 다중 선택 + 업로드, 카드 그리드(썸네일+파일명+상태뱃지)
  - 바닐라 JS: 업로드는 POST /api/v1/upload(FormData), 카드별 GET /api/v1/jobs/{id} 2~3초 폴링
  - status "done"이면 결과 표시+폴링 중단, "pending"이면 스피너 유지
  - `GET /` 또는 `GET /upload-ui`에 Jinja2Templates 연결

- [ ] 단계 8 — 로컬 검증
  - .env 로컬 맞춤 → docker compose up -d → alembic upgrade head → uvicorn --reload
  - 업로드 → 카드 pending 표시 확인
  - ./uploads 파일 저장 / DB jobs pending row / Kafka UI(kafka-ui.doongle.local) 토픽 메시지 확인
  - (워커 없으므로 pending에서 멈춤이 정상)