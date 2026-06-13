"""
Kafka Producer 헬퍼

- AIOKafkaProducer 인스턴스를 앱 생명주기(lifespan)에 맞춰 1개만 유지한다.
- start_producer() 는 lifespan startup 에서, stop_producer() 는 shutdown 에서 호출한다.
- Kafka 브로커에 접속할 수 없는 환경에서도 FastAPI 앱은 부팅되어야 하므로
  start 실패 시 예외를 삼키고 producer 를 None 으로 둔다. (ClickHouse 헬퍼와 동일 철학)
- 접속 정보는 .env 의 KAFKA_BOOTSTRAP_SERVERS / KAFKA_UPLOAD_TOPIC 로 설정한다.
"""
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger("app.core.kafka")

# 앱 전역에서 공유하는 단일 producer 인스턴스
_producer: Optional[AIOKafkaProducer] = None


async def start_producer() -> None:
    """lifespan startup 에서 호출 — producer 생성 및 연결 시작"""
    global _producer
    if _producer is not None:
        logger.warning("Kafka producer 가 이미 시작되어 있습니다.")
        return

    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    try:
        await producer.start()
    except Exception as e:  # 브로커 미가용 등 — 앱 부팅은 막지 않는다
        logger.warning(
            "Kafka producer 시작 실패 (bootstrap=%s): %s. "
            "업로드 기능은 비활성 상태로 동작합니다.",
            settings.KAFKA_BOOTSTRAP_SERVERS,
            e,
        )
        return

    _producer = producer
    logger.info("Kafka producer 시작 (bootstrap=%s)", settings.KAFKA_BOOTSTRAP_SERVERS)


async def stop_producer() -> None:
    """lifespan shutdown 에서 호출 — producer 연결 정리"""
    global _producer
    if _producer is None:
        return
    try:
        await _producer.stop()
        logger.info("Kafka producer 종료")
    finally:
        _producer = None


def get_producer_instance() -> Optional[AIOKafkaProducer]:
    """현재 실행 중인 producer 인스턴스 반환 (없으면 None)"""
    return _producer
