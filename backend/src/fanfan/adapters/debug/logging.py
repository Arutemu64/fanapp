import logging
import sys
from typing import override

import structlog

from fanfan.adapters.debug.redaction import redact_secret_paths

HEALTH_CHECK_PATH = "/debug/health"


class _HealthCheckFilter(logging.Filter):
    """Drop uvicorn access logs for the health check endpoint."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return HEALTH_CHECK_PATH not in record.getMessage()


class SecretPathFilter(logging.Filter):
    """Redact secret path segments from uvicorn access log lines."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_secret_paths(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def setup_logging(level: int, *, json_logs: bool) -> None:
    default_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.ExtraAdder(),
        structlog.dev.set_exc_info,
        structlog.processors.ExceptionPrettyPrinter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=True),
        structlog.processors.dict_tracebacks,
    ]

    if json_logs:
        default_processors.insert(0, structlog.processors.format_exc_info)

    structlog_processors = [
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer()
    )

    logging_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        renderer,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=default_processors,
        processors=logging_processors,
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.set_name("default")
    handler.setLevel(level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    structlog.configure(
        processors=default_processors + structlog_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(_HealthCheckFilter())
    access_logger.addFilter(SecretPathFilter())
