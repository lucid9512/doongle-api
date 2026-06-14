from pydantic import field_validator

from app.exceptions import UnprocessableEntityError
from app.schemas.__base__ import VaModelReq

# DB jobs.filename 컬럼이 String(255) 이므로 동일하게 255 로 제한
MAX_FILENAME_LEN = 255


class UploadImageMeta(VaModelReq):
    """
    업로드 파일의 메타 검증 스키마.

    멀티파트 업로드라 파일 바이트 자체는 Pydantic 으로 담지 못하지만,
    파생 메타(filename, content_type)는 스키마에서 선언적으로 검증한다.
    (기존 req/user.py 의 valid_email 과 동일하게, 검증 실패는 UnprocessableEntityError 로 던진다.)
    """
    filename: str
    content_type: str

    @field_validator("filename")
    @classmethod
    def valid_filename(cls, val: str) -> str:
        if val is None or not val.strip():
            raise UnprocessableEntityError(message="MSG_EMPTY_FILENAME")
        if len(val) > MAX_FILENAME_LEN:
            raise UnprocessableEntityError(message="MSG_FILENAME_TOO_LONG")
        return val

    @field_validator("content_type")
    @classmethod
    def must_be_image(cls, val: str) -> str:
        if not (val or "").startswith("image/"):
            raise UnprocessableEntityError(message="MSG_NOT_AN_IMAGE")
        return val
