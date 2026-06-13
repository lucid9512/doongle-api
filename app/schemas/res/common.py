from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Any, Optional, Dict
from datetime import datetime
from app.core.request_context import get_request_id
from app.schemas.__base__ import to_camel, parse_keys

class MetaData(BaseModel):
    request_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    elapsed_ms: int | None = None
    version: str = "v1.0.0"
    
    # metadata 필드의 키를 camelCase로 변환
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def __init__(self, **data):
        # 자동으로 request_id 주입
        if not data.get("request_id"):
            data["request_id"] = get_request_id()
        super().__init__(**data)

class SuccessJsonRes(BaseModel):
    """통일된 성공 응답 스키마"""
    result: bool = True
    message: str = Field(default="MSG_SUCCESS", description="결과 메시지 코드 (FE i18n key)")
    data: Dict[str, Any] = Field(default_factory=dict, description="응답 데이터 (object 형태 강제)")
    meta: MetaData = Field(default_factory=MetaData, description="추가 메타데이터")

    # data 필드의 키를 재귀적으로 camelCase로 변환
    @field_serializer('data')
    def recursive_to_camel(self, data: Dict[str, Any], _info) -> Dict[str, Any]:
        return parse_keys(data)


class ErrorRes(BaseModel):
    """통일된 오류 응답 스키마"""
    result: bool = False
    message: str = Field(default="MSG_ERROR", description="에러 메시지 코드 (FE i18n key)")
    error_type: Optional[str] = Field(default=None, description="오류 유형 식별자 (ex. DuplicateError)")
    meta: MetaData = Field(default_factory=MetaData, description="추가 메타데이터")
