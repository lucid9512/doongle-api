from datetime import datetime
from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, declarative_mixin, declared_attr
from app.models import Base
from sqlalchemy.sql import func

@declarative_mixin
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,      # 1. ORM으로 객체 생성 시 Python이 시간 채워줌
        server_default=func.now(),    # 2. Bulk Insert나 Raw SQL 시 DB가 시간 채워줌 (에러 해결!)
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,      # 1. ORM Insert 시 Python이 시간 채워줌
        onupdate=datetime.utcnow,     # 2. ORM Update 시 Python이 시간 갱신함
        server_default=func.now(),    # 3. Bulk Insert 시 DB가 초기값 채워줌
        nullable=False
    )

@declarative_mixin
class BaseMixin:
    """
    단일 PK + autoincrement id 모델용 Mixin.

    `__tablename__` 자동 생성은 `ClassName.lower() + "s"` 단순 규칙이라
    영어 복수형 예외(Category → categorys)에 약합니다. 모델 정의 시 가급적
    `__tablename__ = "..."` 를 명시하고, 본 fallback 은 단순 케이스용으로만 사용하세요.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"  # 예: User → users (fallback)


class BaseModel(Base, BaseMixin, TimestampMixin):
    """
    표준 단일 PK 모델 베이스. 대부분의 도메인 모델은 이걸 상속.
    """
    __abstract__ = True


class CompositePKBaseModel(Base, TimestampMixin):
    """
    복합 PK 모델 베이스 (id 컬럼 없음).

    예: 통계 테이블에서 [year, month, day, +@] 로 구성된 복합 기본키를 직접 정의할 때 사용.
    `id` 가 자동으로 들어가지 않으니 모델에서 PK 컬럼을 직접 선언해야 합니다.
    """
    __abstract__ = True