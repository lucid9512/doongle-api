import logging
from logging.config import dictConfig
from app.core.config import settings
import sys
from pathlib import Path
import platform


# ============================================================
# 로그 파일 경로
# ============================================================
LOG_DIR = Path(settings.LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)
APP_LOG = LOG_DIR / "app.log"
ERR_LOG = LOG_DIR / "error.log"

# ============================================================
# Formatter
# ============================================================
base_format = (
    "[%(asctime)s] [%(levelname)-8s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
)
date_format = "%Y-%m-%d %H:%M:%S"

# ============================================================
# LOGGING CONFIG
# ============================================================
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": base_format, "datefmt": date_format},
        "access": {
            "format": "%(asctime)s [ACCESS] %(client_addr)s \"%(request_line)s\" %(status_code)s",
            "datefmt": date_format,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "default",
            "level": settings.LOG_LEVEL,
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(APP_LOG),
            "maxBytes": 10_485_760,
            "backupCount": 5,
            "encoding": "utf-8",
            "level": settings.LOG_LEVEL,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(ERR_LOG),
            "maxBytes": 10_485_760,
            "backupCount": 5,
            "encoding": "utf-8",
            "level": "ERROR",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console", "app_file"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console", "app_file", "error_file"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["console", "app_file"], "level": "INFO", "propagate": False},
        "fastapi": {"handlers": ["console", "app_file"], "level": "INFO", "propagate": False},
        "app": {"handlers": ["console", "app_file", "error_file"], "level": settings.LOG_LEVEL, "propagate": False},
        "sqlalchemy.engine": {"handlers": ["app_file"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console", "app_file"], "level": settings.LOG_LEVEL},
}


# ============================================================
# Setup Function
# ============================================================
def setup_logging():
    """dictConfig 기반 로깅 초기화"""
    dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(True)

    system_name = platform.system()
    logging.getLogger("app").info(
        f"Logging initialized ({system_name}) → {APP_LOG} / errors → {ERR_LOG}"
    )
