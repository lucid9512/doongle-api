from sqlalchemy.orm import declarative_base
import pathlib, importlib

Base = declarative_base()

# 현재 디렉토리 안의 모든 .py 파일을 순회
for file in pathlib.Path(__file__).parent.glob("*.py"):
    if file.name not in {"__init__.py", "base.py"}:
        module_name = f"{__package__}.{file.stem}"
        importlib.import_module(module_name)