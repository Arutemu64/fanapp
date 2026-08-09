import logging
import sys

import structlog

# Path of the container/Dockerfile HEALTHCHECK probe; its access logs are noise.
_HEALTH_CHECK_PATH = "/debug/health"


class _HealthCheckFilter(logging.Filter):
    """Drop uvicorn access logs for the health check endpoint."""

    def filter(self, record: logging.LogRecord) -> bool:
        return _HEALTH_CHECK_PATH not in record.getMessage()


def setup_logging(level: int, *, json_logs: bool):
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
        # for integration with default logging
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
    # Drop any handlers from a previous setup_logging() call so repeated
    # initialization (e.g. running a service entrypoint that also builds the
    # app factory) does not stack handlers and emit every log line twice.
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    structlog.configure(
        processors=default_processors + structlog_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
    # The outbox relay ticks every couple of seconds, and APScheduler's executor
    # logs "Running job"/"executed successfully" at INFO on every tick — tens of
    # thousands of lines a day for a job that usually finds nothing to publish.
    # WARNING keeps the ones that matter (missed runs, max-instances, failures).
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
