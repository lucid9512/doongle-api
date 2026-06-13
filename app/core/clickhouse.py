"""
ClickHouse 클라이언트 헬퍼

- clickhouse-connect 패키지가 설치되어 있지 않거나 서버에 접속할 수 없는
  환경에서도 FastAPI 앱은 정상 부팅되어야 한다.
- 따라서 import 는 lazy 하게 처리하고, 호출 시점에만 의존성을 평가한다.
- 접속 정보는 .env 의 CH_HOST / CH_PORT / CH_USER / CH_PASSWORD / CH_DB 로 설정한다.
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_ch_client():
    """
    ClickHouse HTTP 클라이언트 생성 (lazy import)

    Raises:
        RuntimeError: clickhouse-connect 미설치 시
    """
    try:
        import clickhouse_connect
    except ImportError as e:
        logger.warning(
            "clickhouse-connect 패키지가 설치되어 있지 않습니다. "
            "ClickHouse 의존 기능을 사용하려면 `poetry add clickhouse-connect` 로 설치하세요."
        )
        raise RuntimeError("clickhouse-connect not installed") from e

    return clickhouse_connect.get_client(
        host=settings.CH_HOST,
        port=settings.CH_PORT,
        username=settings.CH_USER,
        password=settings.CH_PASSWORD,
        database=settings.CH_DB,
    )
