from contextvars import ContextVar

# 요청 단위 Request ID를 ContextVar로 보관
REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="-")

def set_request_id(rid: str):
    """요청 시작 시 ContextVar에 request_id 저장"""
    REQUEST_ID_CTX.set(rid)

def get_request_id() -> str:
    """현재 ContextVar에 저장된 request_id 반환"""
    return REQUEST_ID_CTX.get("-")
