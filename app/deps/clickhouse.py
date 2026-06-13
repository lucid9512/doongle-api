from typing import Generator
from app.core.clickhouse import create_ch_client

def get_ch_db() -> Generator:
    """
    FastAPI Depends에서 사용할 ClickHouse 의존성
    """
    client = create_ch_client()
    try:
        yield client
    finally:
        # 사용이 끝나면 세션을 닫아줍니다.
        client.close()