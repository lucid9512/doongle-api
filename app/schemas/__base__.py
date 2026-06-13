import re
from typing import Any, Dict, List, Union
from pydantic import BaseModel, ConfigDict


# -------------------
# util functions
# -------------------
def to_camel(string: str) -> str:
    """snake_case → camelCase"""
    if string == "root":
        return string
    string_split = string.split("_")
    return string_split[0] + "".join(word.capitalize() for word in string_split[1:])

def to_snake(string: str) -> str:
    """camelCase → snake_case"""
    if string == "root":
        return string
    first_underscore = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", string)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_underscore).lower()

def keys_to_snake_case(data: Dict[str, Any]) -> Dict[str, Any]:
    return {to_snake(k): v for k, v in data.items()}

def keys_to_camel_case(data: Dict[str, Any]) -> Dict[str, Any]:
    return {to_camel(k): v for k, v in data.items()}

# -------------------
# Base Request Model
# -------------------
class VaModelReq(BaseModel):
    """
    camelCase → snake_case 변환해서 내부에서 사용
    """
    class Config:
        alias_generator = to_camel   # snake → camel alias 자동 생성
        populate_by_name = True      # snake_case 입력도 허용
        from_attributes = True
        arbitrary_types_allowed = True


def parse_keys(data: Union[Dict, List], types: str = "camel") -> Union[Dict, List]:
    """
    dict/list 전체를 camelCase or snake_case로 변환 (재귀 지원)
    """
    def snake_case(val: str) -> str:
        import re
        first = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", val)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first).lower()

    def keys_to_case(d: Dict[str, Any]) -> Dict[str, Any]:
        if types == "camel":
            return {to_camel(k): v for k, v in d.items()}
        elif types == "snake":
            return {snake_case(k): v for k, v in d.items()}
        return d

    if isinstance(data, list):
        return [parse_keys(item, types) if isinstance(item, (dict, list)) else item for item in data]
    elif isinstance(data, dict):
        return {k: parse_keys(v, types) if isinstance(v, (dict, list)) else v
                for k, v in keys_to_case(data).items()}
    else:
        return data

# --- 베이스 스키마 ---
class VaModelRes(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

