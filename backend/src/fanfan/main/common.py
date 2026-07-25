from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.debug.logging import setup_logging
from fanfan.adapters.debug.telemetry import setup_telemetry


def init(service_name: str) -> None:
    config = get_config()

    setup_logging(
        level=config.debug.logging_level,
        json_logs=config.debug.json_logs,
    )

    setup_telemetry(
        service_name=service_name,
        environment=config.env,
        sentry_dsn=config.debug.sentry_dsn,
        release=config.build,
        traces_sample_rate=config.debug.sentry_traces_sample_rate,
        profiles_sample_rate=config.debug.sentry_profiles_sample_rate,
    )
