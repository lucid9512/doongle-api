from typing import Annotated, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    # ===== App =====
    PROJECT_NAME: str
    SECRET_KEY: str
    ENV: str
    ADMIN_SECRET_KEY: str
    DEBUG: bool
    TESTING: bool

    # ===== DB =====
    DATABASE_URL: str

    # ===== JWT =====
    JWT_SECRET: str
    JWT_TOKEN_URL: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # ===== Logging =====
    LOG_DIR: str
    LOG_LEVEL: str

    # ===== CORS =====
    # 콤마(,) 구분 또는 JSON 배열로 .env 에 작성
    # 예) CORS_ORIGINS=http://localhost:3031,http://127.0.0.1:3031
    # NoDecode 로 pydantic-settings 의 자동 JSON 파싱을 끄고, 아래 validator 에서 직접 처리
    CORS_ORIGINS: Annotated[List[str], NoDecode] = []

    # ===== Kafka =====
    # 클러스터 내부: kafka-0.kafka.kafka.svc.cluster.local:9092
    # 로컬 개발: localhost:9092 등으로 .env 에서 교체
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_UPLOAD_TOPIC: str = "image-upload"

    # ===== Storage =====
    # 저장소 백엔드 선택 (local | minio)
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./uploads"
    # MinIO(S3 호환) 백엔드용. STORAGE_BACKEND=minio 일 때 사용.
    # 버킷은 콘솔에서 미리 생성해 둔다고 가정한다(앱이 생성하지 않음).
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "images"
    MINIO_SECURE: bool = False

    # ===== ClickHouse (옵셔널) =====
    CH_HOST: str = "localhost"
    CH_PORT: int = 8123
    CH_USER: str = "default"
    CH_PASSWORD: str = ""
    CH_DB: str = "default"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                import json
                return json.loads(v)
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
