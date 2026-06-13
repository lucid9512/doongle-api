"""
Kafka producer 의존성

FastAPI Depends 로 주입해 라우터에서 사용한다.
producer 가 시작되지 않은 경우(브로커 미가용 등) 503 으로 응답한다.
"""
from aiokafka import AIOKafkaProducer
from fastapi import HTTPException, status

from app.core.kafka import get_producer_instance


def get_producer() -> AIOKafkaProducer:
    """현재 실행 중인 Kafka producer 를 반환. 없으면 503."""
    producer = get_producer_instance()
    if producer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kafka producer is not available.",
        )
    return producer
