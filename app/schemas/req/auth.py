from app.schemas.__base__ import VaModelReq


class RefreshRequest(VaModelReq):
    """Refresh 토큰을 본문으로 받는 경우용 스키마 (현재 라우터는 쿠키로 받음)"""
    refresh_token: str
