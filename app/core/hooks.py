"""
FastAPI 전역 훅(Hook)
- startup / shutdown lifespan 관리
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.exception_handler import init_exception_handlers
from app.exceptions.handler import register_exception_handlers as register_domain_service_handlers


logger = logging.getLogger("app.hooks")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan 컨텍스트"""
    logger.info("Dongle Application startup")
    try:
        yield
    finally:
        logger.info("Dongle Application shutdown")


def register_all_exception_handlers(app):
    """전역 + 도메인 예외 통합 등록"""
    init_exception_handlers(app)            # 시스템 레벨
    register_domain_service_handlers(app)   # 비즈니스 레벨