# doongle-api 이미지 업로드 게이트웨이
# 워커(doongle-ai) Dockerfile 과 동일 원칙: amd64 고정, 로그 언버퍼, 설정은 런타임 주입.
# api 는 추론을 하지 않으므로(GPU 없음) 슬림 파이썬 베이스를 쓴다.
#
# 멀티스테이지: 일부 의존성(aiokafka 등)은 cp313 휠이 없어 소스 빌드가 필요하다.
# builder 에서만 컴파일러를 두고 빌드한 뒤, runtime 이미지는 슬림하게(빌드도구 없이) 유지한다.

# ===== builder =====
FROM --platform=linux/amd64 python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1

# C 확장(aiokafka 등) 빌드용 컴파일러. 이 레이어는 builder 에만 남고 runtime 으로 안 넘어간다.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# 격리된 venv 에 설치 → runtime 으로 통째 복사
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 의존성 먼저 설치해 레이어 캐시 활용 (소스만 바뀌면 이 레이어 재사용)
# requirements.txt 는 빌드 전 로컬에서 `poetry export` 로 뽑아 둔다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== runtime =====
FROM --platform=linux/amd64 python:3.13-slim

# k8s 로그 가시성: stdout/stderr 즉시 flush
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# builder 에서 빌드한 의존성(venv)만 복사 — 컴파일러는 가져오지 않는다.
COPY --from=builder /opt/venv /opt/venv

# 앱 소스 + alembic 설정/마이그레이션 COPY
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/

# uvicorn
EXPOSE 8000

# 설정값(KAFKA/MINIO/DB 등)은 Dockerfile 에 ENV 로 박지 않는다.
# 전부 런타임 환경변수(k8s ConfigMap/Secret)로 주입한다.
#
# 시작 시 alembic 마이그레이션을 먼저 적용한 뒤 uvicorn 을 띄운다.
# (현재 api 1 레플리카 기준. 다중 레플리카로 가면 마이그레이션은 별도 Job 으로 분리 — DECISIONS 참고)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
